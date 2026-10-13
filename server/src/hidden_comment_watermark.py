from __future__ import annotations

import hashlib
import hmac

from watermarking_method import (
    InvalidKeyError,
    SecretNotFoundError,
    WatermarkingMethod,
    load_pdf_bytes,
)


class HiddenCommentWatermark(WatermarkingMethod):
    """Hide a keyed secret inside a PDF comment.

    The comment holds ``%TATOU-HIDDEN:v2:<tag>:<secret>`` where ``tag`` is
    HMAC-SHA256(key, secret) in hex. Reading with a wrong key raises
    InvalidKeyError. The secret itself is stored in plaintext.
    """

    name = "hidden-comment"

    _MARKER = b"%TATOU-HIDDEN:v2:"

    @staticmethod
    def get_usage() -> str:
        return "Hides the secret inside a PDF comment. Position is ignored."

    @staticmethod
    def _tag(key: str, secret: str) -> str:
        return hmac.new(key.encode("utf-8"), secret.encode("utf-8"), hashlib.sha256).hexdigest()

    def is_watermark_applicable(self, pdf, position=None) -> bool:
        load_pdf_bytes(pdf)
        return True

    def add_watermark(self, pdf, secret, key, position=None) -> bytes:
        data = load_pdf_bytes(pdf)

        if not secret:
            raise ValueError("Secret must not be empty")

        tag = self._tag(key, secret).encode("ascii")
        marker = b"\n" + self._MARKER + tag + b":" + secret.encode("utf-8") + b"\n"

        return data + marker

    def read_secret(self, pdf, key) -> str:
        data = load_pdf_bytes(pdf)

        start = data.rfind(self._MARKER)

        if start == -1:
            raise SecretNotFoundError("Hidden watermark not found")

        start = start + len(self._MARKER)
        end = data.find(b"\n", start)

        if end == -1:
            end = len(data)

        tag, sep, secret_bytes = data[start:end].partition(b":")
        if not sep or not secret_bytes:
            raise SecretNotFoundError("Hidden watermark not found")

        secret = secret_bytes.decode("utf-8")
        if not hmac.compare_digest(tag, self._tag(key, secret).encode("ascii")):
            raise InvalidKeyError("Key does not match the hidden watermark")

        return secret