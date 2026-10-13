from __future__ import annotations

import hashlib
import hmac
from typing import Final

import pymupdf

from watermarking_method import (
    InvalidKeyError,
    SecretNotFoundError,
    WatermarkingMethod,
    load_pdf_bytes,
)


class MetadataWatermark(WatermarkingMethod):
    """Store a keyed watermark secret in PDF metadata.

    The keywords field holds ``tatou-watermark:v2:<tag>:<secret>`` where
    ``tag`` is HMAC-SHA256(key, secret) in hex. Reading with a wrong key
    raises InvalidKeyError. The secret itself is stored in plaintext, so
    anyone who inspects the PDF metadata can read it.
    """

    name: Final[str] = "metadata-watermark"
    _FIELD: Final[str] = "keywords"
    _PREFIX: Final[str] = "tatou-watermark:v2:"

    @staticmethod
    def get_usage() -> str:
        return "Stores the watermark secret in PDF metadata."

    @staticmethod
    def _tag(key: str, secret: str) -> str:
        return hmac.new(key.encode("utf-8"), secret.encode("utf-8"), hashlib.sha256).hexdigest()

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
        metadata[self._FIELD] = self._PREFIX + self._tag(key, secret) + ":" + secret

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

        tag, sep, secret = value[len(self._PREFIX):].partition(":")
        if not sep or not secret:
            raise SecretNotFoundError("No metadata watermark found")

        if not hmac.compare_digest(tag.encode("utf-8"), self._tag(key, secret).encode("ascii")):
            raise InvalidKeyError("Key does not match the metadata watermark")

        return secret


__all__ = ["MetadataWatermark"]
