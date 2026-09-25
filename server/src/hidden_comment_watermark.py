from watermarking_method import (
    WatermarkingMethod,
    SecretNotFoundError,
    load_pdf_bytes,
)


class HiddenCommentWatermark(WatermarkingMethod):

    name = "hidden-comment"

    @staticmethod
    def get_usage() -> str:
        return "Hides the secret inside a PDF comment. Position and key are ignored."

    def is_watermark_applicable(self, pdf, position=None) -> bool:
        load_pdf_bytes(pdf)
        return True

    def add_watermark(self, pdf, secret, key, position=None) -> bytes:
        data = load_pdf_bytes(pdf)

        if not secret:
            raise ValueError("Secret must not be empty")

        marker = b"\n%TATOU-HIDDEN:" + secret.encode("utf-8") + b"\n"

        return data + marker

    def read_secret(self, pdf, key) -> str:
        data = load_pdf_bytes(pdf)

        marker = b"%TATOU-HIDDEN:"
        start = data.rfind(marker)

        if start == -1:
            raise SecretNotFoundError("Hidden watermark not found")

        start = start + len(marker)
        end = data.find(b"\n", start)

        if end == -1:
            end = len(data)

        return data[start:end].decode("utf-8")
