"""Tests for the keyed (v2) metadata watermark format.

Format: keywords = "tatou-watermark:v2:<tag>:<secret>", tag = HMAC-SHA256(key, secret).
"""
from __future__ import annotations

import pymupdf
import pytest

from metadata_watermark import MetadataWatermark
from watermarking_method import InvalidKeyError, SecretNotFoundError

PREFIX = "tatou-watermark:v2:"
NOT_FOUND = "No metadata watermark found"


def _real_pdf() -> bytes:
    doc = pymupdf.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    return data


def _write(tmp_path, data: bytes, name: str = "doc.pdf"):
    path = tmp_path / name
    path.write_bytes(data)
    return path


def _watermarked(tmp_path, secret: str, key: str):
    src = _write(tmp_path, _real_pdf(), "src.pdf")
    return _write(tmp_path, MetadataWatermark().add_watermark(src, secret=secret, key=key), "wm.pdf")


def _with_keywords(tmp_path, pdf_bytes: bytes, keywords: str):
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    meta = doc.metadata or {}
    meta["keywords"] = keywords
    doc.set_metadata(meta)
    out = doc.tobytes()
    doc.close()
    return _write(tmp_path, out, "tampered.pdf")


def test_secret_containing_colons_round_trips(tmp_path):
    secret = "a:b:c"
    pdf = _watermarked(tmp_path, secret, "k")
    assert MetadataWatermark().read_secret(pdf, key="k") == secret


def test_tampered_secret_is_rejected(tmp_path):
    wm = MetadataWatermark()
    pdf = _watermarked(tmp_path, "original", "k")
    assert wm.read_secret(pdf, key="k") == "original"

    doc = pymupdf.open(pdf)
    keywords = doc.metadata["keywords"]
    doc.close()
    tag = keywords[len(PREFIX):].split(":", 1)[0]

    # Same valid tag, different secret: the tag must bind the secret.
    tampered = _with_keywords(tmp_path, pdf.read_bytes(), PREFIX + tag + ":forged")
    with pytest.raises(InvalidKeyError):
        wm.read_secret(tampered, key="k")


@pytest.mark.parametrize(
    "keywords",
    [
        PREFIX,            # no tag, no separator
        PREFIX + "abc",    # tag without separator
        PREFIX + ":",      # empty tag and empty secret
        PREFIX + "x:",     # tag with empty secret
        "other:colon",     # colon but no watermark prefix
        "an unrelated keyword value that is longer than the prefix: with a colon",
    ],
)
def test_malformed_values_raise_exact_not_found_message(tmp_path, keywords):
    pdf = _with_keywords(tmp_path, _real_pdf(), keywords)
    with pytest.raises(SecretNotFoundError) as info:
        MetadataWatermark().read_secret(pdf, key="k")
    assert str(info.value) == NOT_FOUND


def test_wrong_key_raises_exact_message(tmp_path):
    pdf = _watermarked(tmp_path, "s", "right")
    with pytest.raises(InvalidKeyError) as info:
        MetadataWatermark().read_secret(pdf, key="wrong")
    assert str(info.value) == "Key does not match the metadata watermark"

def test_non_ascii_tag_is_rejected_as_wrong_key(tmp_path):
    pdf = _with_keywords(tmp_path, _real_pdf(), PREFIX + "é" + ":s")
    with pytest.raises(InvalidKeyError):
        MetadataWatermark().read_secret(pdf, key="k")