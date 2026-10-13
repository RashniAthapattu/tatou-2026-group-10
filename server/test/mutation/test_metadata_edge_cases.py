import pymupdf
import pytest

from metadata_watermark import MetadataWatermark
from watermarking_method import InvalidKeyError, SecretNotFoundError


def _real_pdf(pages=2, title="Original title"):
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"page {i + 1} text")
    doc.set_metadata({"title": title})
    out = doc.tobytes()
    doc.close()
    return out


def _pdf_with_keywords(value):
    doc = pymupdf.open()
    doc.new_page()
    doc.set_metadata({"keywords": value})
    out = doc.tobytes()
    doc.close()
    return out


@pytest.fixture
def wm():
    return MetadataWatermark()


def test_roundtrip_on_real_pdf(wm):
    out = wm.add_watermark(_real_pdf(), secret="hello", key="k")
    assert wm.read_secret(out, key="k") == "hello"


def test_output_keeps_pages_and_content(wm):
    out = wm.add_watermark(_real_pdf(pages=2), secret="s", key="k")
    doc = pymupdf.open(stream=out, filetype="pdf")
    try:
        assert doc.page_count == 2
        assert "page 2 text" in doc[1].get_text()
    finally:
        doc.close()


def test_output_keeps_existing_metadata(wm):
    out = wm.add_watermark(_real_pdf(title="Original title"), secret="s", key="k")
    doc = pymupdf.open(stream=out, filetype="pdf")
    try:
        assert doc.metadata["title"] == "Original title"
    finally:
        doc.close()


def test_is_watermark_applicable_returns_true(wm):
    assert wm.is_watermark_applicable(_real_pdf()) is True


def test_get_usage_text_is_exact():
    assert MetadataWatermark.get_usage() == "Stores the watermark secret in PDF metadata."


def test_empty_secret_exact_message(wm):
    with pytest.raises(ValueError) as exc:
        wm.add_watermark(_real_pdf(), secret="", key="k")
    assert str(exc.value) == "Secret must be a non-empty string"


def test_empty_key_on_add_exact_message(wm):
    with pytest.raises(ValueError) as exc:
        wm.add_watermark(_real_pdf(), secret="s", key="")
    assert str(exc.value) == "Key must be a non-empty string"


def test_empty_key_on_read_exact_message(wm):
    out = wm.add_watermark(_real_pdf(), secret="s", key="k")
    with pytest.raises(ValueError) as exc:
        wm.read_secret(out, key="")
    assert str(exc.value) == "Key must be a non-empty string"


def test_unwatermarked_pdf_raises_exact_message(wm):
    with pytest.raises(SecretNotFoundError) as exc:
        wm.read_secret(_real_pdf(), key="k")
    assert str(exc.value) == "No metadata watermark found"


@pytest.mark.parametrize("value", ["other", ""])
def test_non_watermark_keyword_is_not_a_secret(wm, value):
    with pytest.raises(SecretNotFoundError):
        wm.read_secret(_pdf_with_keywords(value), key="k")


def test_wrong_key_is_rejected(wm):
    out = wm.add_watermark(_real_pdf(), secret="s", key="k")
    with pytest.raises(InvalidKeyError):
        wm.read_secret(out, key="other")