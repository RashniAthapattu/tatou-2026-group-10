import base64
import json

import pytest

from add_after_eof import AddAfterEOF
from watermarking_method import InvalidKeyError, SecretNotFoundError, WatermarkingError

SAMPLE = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
MARKER = b"\n%%WM-ADD-AFTER-EOF:v1\n"


@pytest.fixture
def wm():
    return AddAfterEOF()


def _with_payload(payload: bytes) -> bytes:
    return SAMPLE + MARKER + base64.urlsafe_b64encode(payload) + b"\n"


def _watermarked(secret="s", key="k"):
    return AddAfterEOF().add_watermark(SAMPLE, secret=secret, key=key)


def test_roundtrip(wm):
    out = wm.add_watermark(SAMPLE, secret="hello", key="k")
    assert wm.read_secret(out, key="k") == "hello"


def test_is_watermark_applicable_returns_true(wm):
    assert wm.is_watermark_applicable(SAMPLE) is True


def test_get_usage_text_is_exact():
    assert AddAfterEOF.get_usage() == (
        "Toy method that appends a watermark record after the PDF EOF. Position is ignored."
    )


def test_wrong_key_raises_invalid_key(wm):
    out = _watermarked(key="k")
    with pytest.raises(InvalidKeyError):
        wm.read_secret(out, key="other")


def test_exact_invalid_key_message(wm):
    out = _watermarked(key="k")
    with pytest.raises(InvalidKeyError) as exc:
        wm.read_secret(out, key="other")
    assert str(exc.value) == "Provided key failed to authenticate the watermark"


def test_unwatermarked_pdf_raises_not_found(wm):
    with pytest.raises(SecretNotFoundError) as exc:
        wm.read_secret(SAMPLE, key="k")
    assert str(exc.value) == "No AddAfterEOF watermark found"


def test_tampered_secret_is_rejected(wm):
    payload = {
        "v": 1,
        "alg": "HMAC-SHA256",
        "mac": wm._mac_hex(b"s", "k"),
        "secret": base64.b64encode(b"forged").decode("ascii"),
    }
    pdf = _with_payload(json.dumps(payload, separators=(",", ":")).encode())
    with pytest.raises(InvalidKeyError):
        wm.read_secret(pdf, key="k")


@pytest.mark.parametrize("key", ["", None, 123])
def test_read_key_validation_exact_message(wm, key):
    with pytest.raises(ValueError) as exc:
        wm.read_secret(_watermarked(), key=key)
    assert str(exc.value) == "Key must be a non-empty string"


def test_empty_key_message_on_add(wm):
    with pytest.raises(ValueError) as exc:
        wm.add_watermark(SAMPLE, secret="s", key="")
    assert str(exc.value) == "Key must be a non-empty string"


def test_empty_secret_exact_message(wm):
    with pytest.raises(ValueError) as exc:
        wm.add_watermark(SAMPLE, secret="", key="k")
    assert str(exc.value) == "Secret must be a non-empty string"


@pytest.mark.parametrize(
    "pdf, exc_type, message",
    [
        (SAMPLE + MARKER + b"\n", SecretNotFoundError, "Found marker but empty payload"),
        (SAMPLE + MARKER + b"!!!\n", SecretNotFoundError, "Malformed watermark payload"),
        (_with_payload(b"[]"), SecretNotFoundError, "Unsupported watermark version or format"),
        (_with_payload(b'{"v":1,"alg":"HMAC-SHA256"}'), SecretNotFoundError, "Invalid payload fields"),
        (
            _with_payload(b'{"v":1,"alg":"MD5","mac":"00","secret":"AA=="}'),
            WatermarkingError,
            "Unsupported MAC algorithm: 'MD5'",
        ),
    ],
)
def test_malformed_payloads_raise_exact_errors(wm, pdf, exc_type, message):
    with pytest.raises(exc_type) as exc:
        wm.read_secret(pdf, key="k")
    assert str(exc.value) == message


def test_latest_watermark_wins(wm):
    out = wm.add_watermark(SAMPLE, secret="first", key="k")
    out = wm.add_watermark(out, secret="second", key="k")
    assert wm.read_secret(out, key="k") == "second"


def test_watermark_survives_bytes_appended_after_it(wm):
    out = _watermarked()
    assert wm.read_secret(out + b"%%EOF\nincremental update\n", key="k") == "s"


@pytest.mark.parametrize(
    "secret", ["a", "ab", "abc", "abcd", "abcde", "abcdef", "abcdefg", "abcdefgh", "abcdefghi"]
)
def test_trailing_text_after_payload_is_ignored(wm, secret):
    out = wm.add_watermark(SAMPLE, secret=secret, key="k")
    assert wm.read_secret(out + b"\n%%EOF\nincremental update\n", key="k") == secret


def test_watermark_at_end_of_file_without_newline(wm):
    out = _watermarked()
    assert wm.read_secret(out.rstrip(b"\n"), key="k") == "s"


def test_pdf_without_trailing_newline_is_handled(wm):
    out = wm.add_watermark(SAMPLE.rstrip(b"\n"), secret="s", key="k")
    assert wm.read_secret(out, key="k") == "s"


def test_payload_uses_compact_json(wm):
    out = _watermarked()
    raw = base64.urlsafe_b64decode(out.rsplit(MARKER, 1)[1].strip())
    assert raw == json.dumps(json.loads(raw), separators=(",", ":")).encode()

def test_pdf_ending_in_newline_gets_no_extra_newline(wm):
    out = wm.add_watermark(SAMPLE, secret="s", key="k")
    assert out.startswith(SAMPLE + MARKER)


def test_pdf_without_trailing_newline_gets_exactly_one(wm):
    no_nl = SAMPLE.rstrip(b"\n")
    out = wm.add_watermark(no_nl, secret="s", key="k")
    assert out.startswith(no_nl + b"\n" + MARKER)