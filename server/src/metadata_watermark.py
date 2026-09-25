from __future__ import annotations

from typing import Final

import pymupdf

from watermarking_method import (
    SecretNotFoundError,
    WatermarkingMethod,
    load_pdf_bytes,
)


class MetadataWatermark(WatermarkingMethod):
    """Store a watermark secret in PDF metadata."""

    name: Final[str] = "metadata-watermark"
    _FIELD: Final[str] = "keywords"
    _PREFIX: Final[str] = "tatou-watermark:"

    @staticmethod
    def get_usage() -> str:
        return "Stores the watermark secret in PDF metadata."

    def add_watermark(
        self,
        pdf,
        secret: str,
        key: str,
        position: str | None = None,
    ) -> bytes:
        if not secret:
            raise ValueError("Secret must be a non-empty string")
        if not key:
            raise ValueError("Key must be a non-empty string")

        data = load_pdf_bytes(pdf)
        doc = pymupdf.open(stream=data, filetype="pdf")

        if doc.page_count == 0:
            doc.close()
            doc = pymupdf.open()
            doc.new_page()

        metadata = doc.metadata or {}
        metadata[self._FIELD] = self._PREFIX + secret

        doc.set_metadata(metadata)
        output = doc.tobytes()
        doc.close()

        return output
    
    def is_watermark_applicable(
        self,
        pdf,
        position: str | None = None,
    ) -> bool:
        return True

    def read_secret(self, pdf, key: str) -> str:
        if not key:
            raise ValueError("Key must be a non-empty string")

        data = load_pdf_bytes(pdf)
        doc = pymupdf.open(stream=data, filetype="pdf")

        metadata = doc.metadata or {}
        value = metadata.get(self._FIELD, "")
        doc.close()

        if not isinstance(value, str) or not value.startswith(self._PREFIX):
            raise SecretNotFoundError("No metadata watermark found")

        return value[len(self._PREFIX):]


__all__ = ["MetadataWatermark"]
