"""Keyed (v2) hidden-comment format: the key must be verified."""
from __future__ import annotations

import pytest

from hidden_comment_watermark import HiddenCommentWatermark
from watermarking_method import InvalidKeyError, SecretNotFoundError

SAMPLE = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
MARKER = b"%TATOU-HIDDEN:v2:"


def test_wrong_key_raises_exact_message():
    wm = HiddenCommentWatermark()
    pdf = wm.add_watermark(SAMPLE, secret="s", key="right")
    with pytest.raises(InvalidKeyError) as info:
        wm.read_secret(pdf, key="wrong")
    assert str(info.value) == "Key does not match the hidden watermark"


def test_tampered_secret_is_rejected():
    wm = HiddenCommentWatermark()
    pdf = wm.add_watermark(SAMPLE, secret="original", key="k")
    start = pdf.rfind(MARKER) + len(MARKER)
    tag = pdf[start:start + 64]
    # Keep the valid tag, replace the secret: the tag must bind the secret.
    forged = pdf[:start] + tag + b":forged\n"
    with pytest.raises(InvalidKeyError):
        wm.read_secret(forged, key="k")


def test_secret_containing_colons_round_trips():
    wm = HiddenCommentWatermark()
    pdf = wm.add_watermark(SAMPLE, secret="a:b:c", key="k")
    assert wm.read_secret(pdf, key="k") == "a:b:c"


@pytest.mark.parametrize("body", [b"abc\n", b"x:\n", b":\n"])
def test_malformed_marker_raises_exact_not_found_message(body):
    wm = HiddenCommentWatermark()
    pdf = SAMPLE + MARKER + body
    with pytest.raises(SecretNotFoundError) as info:
        wm.read_secret(pdf, key="k")
    assert str(info.value) == "Hidden watermark not found"

def test_marker_is_appended_on_its_own_line():
    wm = HiddenCommentWatermark()
    out = wm.add_watermark(SAMPLE, secret="s", key="k")
    assert out.startswith(SAMPLE + b"\n" + MARKER)


def test_no_marker_with_colon_after_offset_is_not_found():
    wm = HiddenCommentWatermark()
    pdf = b"%PDF-1.4\n" + b"x" * 20 + b":y\n%%EOF\n"
    with pytest.raises(SecretNotFoundError) as info:
        wm.read_secret(pdf, key="k")
    assert str(info.value) == "Hidden watermark not found"


def test_non_ascii_tag_is_rejected_as_wrong_key():
    wm = HiddenCommentWatermark()
    pdf = SAMPLE + b"\n" + MARKER + b"\xff\xfe:s\n"
    with pytest.raises(InvalidKeyError):
        wm.read_secret(pdf, key="k")