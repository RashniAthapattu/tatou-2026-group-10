import base64
import re

import pymupdf
import pytest

from invisible_text_watermark import InvisibleTextWatermark
from watermarking_method import InvalidKeyError, WatermarkingError

MARK = "TATOUWM1:"
GOLDEN = "TATOUWM1:DbavrWF9XzseENHCRnnkrDvtguZawYefZIa7jsQ="


def _plain_pdf(pages=1):
    doc = pymupdf.open()
    for i in range(pages):
        doc.new_page().insert_text((72, 72), f"page {i + 1} body")
    out = doc.tobytes()
    doc.close()
    return out


def _pdf_with_pages(page_texts):
    doc = pymupdf.open()
    for texts in page_texts:
        page = doc.new_page()
        for y, text in zip((10, 20, 30), texts):
            page.insert_text((1, y), text, fontsize=1)
    out = doc.tobytes()
    doc.close()
    return out


def _page_text(pdf, index):
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    try:
        return doc[index].get_text("text")
    finally:
        doc.close()


def _marker_for(secret, key):
    out = InvisibleTextWatermark().add_watermark(_plain_pdf(), secret=secret, key=key)
    text = _page_text(out, 0)
    return text[text.index(MARK):].split()[0]


@pytest.fixture
def wm():
    return InvisibleTextWatermark()


def test_golden_payload_for_fixed_inputs(wm):
    out = wm.add_watermark(_plain_pdf(), secret="s", key="k")
    text = _page_text(out, 0)
    assert text[text.index(MARK):].split()[0] == GOLDEN


def test_watermark_is_invisible_render_mode_3(wm):
    out = wm.add_watermark(_plain_pdf(), secret="s", key="k")
    doc = pymupdf.open(stream=out, filetype="pdf")
    try:
        content = doc[0].read_contents()
    finally:
        doc.close()
    assert re.search(rb"\b3 Tr\b", content)


def test_watermark_span_is_one_point_at_top_left(wm):
    out = wm.add_watermark(_plain_pdf(), secret="s", key="k")
    doc = pymupdf.open(stream=out, filetype="pdf")
    try:
        spans = [
            span
            for block in doc[0].get_text("dict")["blocks"]
            for line in block.get("lines", [])
            for span in line["spans"]
            if MARK in span["text"]
        ]
    finally:
        doc.close()
    assert [span["size"] for span in spans] == [1]
    assert [tuple(span["origin"]) for span in spans] == [(1, 10)]


def test_wrong_key_message_is_not_none(wm):
    out = wm.add_watermark(_plain_pdf(), secret="s", key="k")
    with pytest.raises(InvalidKeyError) as exc:
        wm.read_secret(out, key="other")
    msg = str(exc.value)
    assert msg.startswith("Watermark marker found but decryption failed with the given key:")
    assert not msg.endswith("None")


def test_short_payload_reports_reason(wm):
    pdf = _pdf_with_pages([[MARK + "AAAA"]])
    with pytest.raises(InvalidKeyError) as exc:
        wm.read_secret(pdf, key="k")
    assert str(exc.value).endswith("payload too short")


def test_base64_error_is_reported_not_none(wm):
    pdf = _pdf_with_pages([[MARK + "A"]])
    with pytest.raises(InvalidKeyError) as exc:
        wm.read_secret(pdf, key="k")
    assert not str(exc.value).endswith("None")


def test_short_candidate_does_not_stop_the_search(wm):
    pdf = _pdf_with_pages([[MARK + "AAAA"], []])
    pdf = wm.add_watermark(pdf, secret="s", key="k", position="1")
    assert wm.read_secret(pdf, key="k") == "s"


def test_exactly_nonce_length_payload_is_not_reported_as_too_short(wm):
    token = base64.urlsafe_b64encode(b"x" * 12).decode("ascii")
    pdf = _pdf_with_pages([[MARK + token]])
    with pytest.raises(InvalidKeyError) as exc:
        wm.read_secret(pdf, key="k")
    assert "payload too short" not in str(exc.value)


def test_first_marker_on_a_page_is_used(wm):
    pdf = _pdf_with_pages([[_marker_for("s", "k"), _marker_for("t", "k")]])
    assert wm.read_secret(pdf, key="k") == "s"

def test_read_on_non_pdf_is_rejected(wm):
    with pytest.raises(ValueError) as exc:
        wm.read_secret(b"not a pdf", key="k")
    assert "missing %PDF header" in str(exc.value)


def test_add_on_non_pdf_is_rejected(wm):
    with pytest.raises(ValueError) as exc:
        wm.add_watermark(b"not a pdf", secret="s", key="k")
    assert "missing %PDF header" in str(exc.value)


def test_bad_candidate_on_one_page_does_not_stop_the_search(wm):
    pdf = _pdf_with_pages([[MARK + "A"], []])
    pdf = wm.add_watermark(pdf, secret="s", key="k", position="1")
    assert wm.read_secret(pdf, key="k") == "s"


def test_wrong_key_candidate_does_not_stop_the_search(wm):
    pdf = wm.add_watermark(_plain_pdf(pages=2), secret="s", key="j", position="0")
    pdf = wm.add_watermark(pdf, secret="s", key="k", position="1")
    assert wm.read_secret(pdf, key="k") == "s"

BROKEN_PDF = b"%PDF-1.4\n" + b"\x00" * 64


def test_read_on_broken_pdf_raises_watermarking_error(wm):
    with pytest.raises(WatermarkingError) as exc:
        wm.read_secret(BROKEN_PDF, key="k")
    assert str(exc.value).startswith("Failed to open PDF:")


def test_add_on_broken_pdf_raises_watermarking_error(wm):
    with pytest.raises(WatermarkingError) as exc:
        wm.add_watermark(BROKEN_PDF, secret="s", key="k")
    assert str(exc.value).startswith("Failed to open PDF:")

@pytest.mark.xfail(strict=True, reason="position is bound into the cipher but read uses the page index, so '01' cannot be read back")
def test_non_canonical_position_is_readable(wm):
    pdf = wm.add_watermark(_plain_pdf(pages=2), secret="s", key="k", position="01")
    assert wm.read_secret(pdf, key="k") == "s"