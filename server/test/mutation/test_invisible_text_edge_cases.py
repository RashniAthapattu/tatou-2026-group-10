import pymupdf
import pytest

from invisible_text_watermark import InvisibleTextWatermark
from watermarking_method import InvalidKeyError, SecretNotFoundError

MARK = "TATOUWM1:"


def _real_pdf(pages=2):
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"page {i + 1} body")
    out = doc.tobytes()
    doc.close()
    return out


def _page_text(pdf, index):
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    try:
        return doc[index].get_text("text")
    finally:
        doc.close()


def _payload(pdf):
    text = _page_text(pdf, 0)
    return text[text.index(MARK):].split()[0]


@pytest.fixture
def wm():
    return InvisibleTextWatermark()


def test_roundtrip(wm):
    out = wm.add_watermark(_real_pdf(), secret="hello", key="k")
    assert wm.read_secret(out, key="k") == "hello"


def test_wrong_key_raises_invalid_key(wm):
    out = wm.add_watermark(_real_pdf(), secret="hello", key="k")
    with pytest.raises(InvalidKeyError):
        wm.read_secret(out, key="other")


def test_unwatermarked_pdf_raises_not_found(wm):
    with pytest.raises(SecretNotFoundError) as exc:
        wm.read_secret(_real_pdf(), key="k")
    assert str(exc.value) == "No invisible-text watermark marker found in this PDF"


def test_get_usage_text_is_exact():
    assert InvisibleTextWatermark.get_usage() == (
        "position: optional zero-based page index as a string (e.g. \"0\"). "
        "Defaults to page 0 if omitted or empty. The secret is placed as "
        "invisible text (render mode 3) near the top-left of that page."
    )


def test_is_applicable_true_for_real_pdf(wm):
    assert wm.is_watermark_applicable(_real_pdf()) is True


def test_is_applicable_false_for_out_of_range_position(wm):
    assert wm.is_watermark_applicable(_real_pdf(pages=2), position="2") is False


def test_is_applicable_false_for_non_integer_position(wm):
    assert wm.is_watermark_applicable(_real_pdf(), position="abc") is False


def test_is_applicable_false_for_garbage_bytes(wm):
    assert wm.is_watermark_applicable(b"not a pdf") is False


def test_empty_secret_exact_message(wm):
    with pytest.raises(ValueError) as exc:
        wm.add_watermark(_real_pdf(), secret="", key="k")
    assert str(exc.value) == "secret must not be empty"


def test_empty_key_on_add_exact_message(wm):
    with pytest.raises(ValueError) as exc:
        wm.add_watermark(_real_pdf(), secret="s", key="")
    assert str(exc.value) == "key must not be empty"


def test_empty_key_on_read_exact_message(wm):
    out = wm.add_watermark(_real_pdf(), secret="s", key="k")
    with pytest.raises(ValueError) as exc:
        wm.read_secret(out, key="")
    assert str(exc.value) == "key must not be empty"


def test_position_places_watermark_on_that_page(wm):
    out = wm.add_watermark(_real_pdf(pages=2), secret="s", key="k", position="1")
    assert MARK not in _page_text(out, 0)
    assert MARK in _page_text(out, 1)


def test_out_of_range_position_exact_message(wm):
    with pytest.raises(ValueError) as exc:
        wm.add_watermark(_real_pdf(pages=2), secret="s", key="k", position="5")
    assert str(exc.value) == "Invalid position 5: document has 2 page(s)"


def test_non_integer_position_exact_message(wm):
    with pytest.raises(ValueError) as exc:
        wm.add_watermark(_real_pdf(), secret="s", key="k", position="abc")
    assert str(exc.value) == "Invalid position 'abc': expected a page index"


def test_payload_is_deterministic(wm):
    a = _payload(wm.add_watermark(_real_pdf(), secret="s", key="k"))
    b = _payload(wm.add_watermark(_real_pdf(), secret="s", key="k"))
    assert a == b


def test_payload_depends_on_secret_and_key(wm):
    base = _payload(wm.add_watermark(_real_pdf(), secret="s", key="k"))
    assert base != _payload(wm.add_watermark(_real_pdf(), secret="t", key="k"))
    assert base != _payload(wm.add_watermark(_real_pdf(), secret="s", key="j"))