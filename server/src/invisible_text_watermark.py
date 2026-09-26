from __future__ import annotations

import base64
import hashlib
import hmac
import re

import pymupdf as fitz

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from watermarking_method import (
    WatermarkingMethod,
    WatermarkingError,
    SecretNotFoundError,
    InvalidKeyError,
    PdfSource,
    load_pdf_bytes,
)

_MARKER = "TATOUWM1:" 
_NONCE_LEN = 12 


def _derive_aes_key(key: str) -> bytes:
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"tatou-invisible-text-watermark",
        info=b"aes-gcm-key",
    )
    return hkdf.derive(key.encode("utf-8"))


def _derive_nonce(key: str, secret: str, position: str) -> bytes:
    digest = hashlib.sha256(
        key.encode("utf-8") + b"|" + secret.encode("utf-8") + b"|" + position.encode("utf-8")
    ).digest()
    return digest[:_NONCE_LEN]


class InvisibleTextWatermark(WatermarkingMethod):

    name = "invisible-text"

    @staticmethod
    def get_usage() -> str:
        return (
            "position: optional zero-based page index as a string (e.g. \"0\"). "
            "Defaults to page 0 if omitted or empty. The secret is placed as "
            "invisible text (render mode 3) near the top-left of that page."
        )

    def _resolve_page_index(self, doc: "fitz.Document", position: str | None) -> int:
        if not position:
            page_index = 0
        else:
            try:
                page_index = int(position)
            except ValueError as exc:
                raise ValueError(f"Invalid position {position!r}: expected a page index") from exc
        if page_index < 0 or page_index >= doc.page_count:
            raise ValueError(
                f"Invalid position {page_index}: document has {doc.page_count} page(s)"
            )
        return page_index

    def is_watermark_applicable(
        self,
        pdf: PdfSource,
        position: str | None = None,
    ) -> bool:
        try:
            data = load_pdf_bytes(pdf)
            doc = fitz.open(stream=data, filetype="pdf")
        except Exception:
            return False
        try:
            self._resolve_page_index(doc, position)
        except ValueError:
            return False
        finally:
            doc.close()
        return True

    def add_watermark(
        self,
        pdf: PdfSource,
        secret: str,
        key: str,
        position: str | None = None,
    ) -> bytes:
        if not secret:
            raise ValueError("secret must not be empty")
        if not key:
            raise ValueError("key must not be empty")

        data = load_pdf_bytes(pdf)
        pos_str = position or "0"

        try:
            doc = fitz.open(stream=data, filetype="pdf")
        except Exception as exc:
            raise WatermarkingError(f"Failed to open PDF: {exc}") from exc

        try:
            page_index = self._resolve_page_index(doc, position)
            page = doc[page_index]

            aes_key = _derive_aes_key(key)
            nonce = _derive_nonce(key, secret, pos_str)
            aesgcm = AESGCM(aes_key)
            ciphertext = aesgcm.encrypt(nonce, secret.encode("utf-8"), pos_str.encode("utf-8"))

            payload = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
            invisible_text = _MARKER + payload

            page.insert_text(
                fitz.Point(1, 10),
                invisible_text,
                fontsize=1,
                fontname="helv",
                render_mode=3,
            )

            try:
                return doc.tobytes(deflate=True, garbage=4, no_new_id=True)
            except Exception as exc:
                raise WatermarkingError(f"Failed to serialize watermarked PDF: {exc}") from exc
        finally:
            doc.close()

    def read_secret(self, pdf: PdfSource, key: str) -> str:
        if not key:
            raise ValueError("key must not be empty")

        data = load_pdf_bytes(pdf)

        try:
            doc = fitz.open(stream=data, filetype="pdf")
        except Exception as exc:
            raise WatermarkingError(f"Failed to open PDF: {exc}") from exc

        try:
            candidate_payloads: list[tuple[str, str]] = []  

            for page_index in range(doc.page_count):
                page = doc[page_index]
                spans = [page.get_text("text")]

                for text in spans:
                    idx = text.find(_MARKER)
                    if idx != -1:
                        rest = text[idx + len(_MARKER):]
                        m = re.match(r"[A-Za-z0-9_\-]+=*", rest)
                        if m:
                            candidate_payloads.append((m.group(0), str(page_index)))

            if not candidate_payloads:
                raise SecretNotFoundError("No invisible-text watermark marker found in this PDF")

            aes_key = _derive_aes_key(key)
            last_error: Exception | None = None

            for payload, pos_str in candidate_payloads:
                try:
                    raw = base64.urlsafe_b64decode(payload.encode("ascii"))
                except Exception as exc:
                    last_error = exc
                    continue
                if len(raw) < _NONCE_LEN:
                    last_error = ValueError("payload too short")
                    continue
                nonce, ciphertext = raw[:_NONCE_LEN], raw[_NONCE_LEN:]
                aesgcm = AESGCM(aes_key)
                try:
                    plaintext = aesgcm.decrypt(nonce, ciphertext, pos_str.encode("utf-8"))
                    return plaintext.decode("utf-8")
                except Exception as exc:  
                    last_error = exc
                    continue

            raise InvalidKeyError(
                f"Watermark marker found but decryption failed with the given key: {last_error}"
            )
        finally:
            doc.close()