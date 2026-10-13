"""Covers the serialization-failure branch of InvisibleTextWatermark.add_watermark.

Mutant 89 replaced the error message with None. It is only reachable when
PyMuPDF fails to serialize the document, so the test forces that failure.
"""
from __future__ import annotations

import pymupdf
import pytest

from invisible_text_watermark import InvisibleTextWatermark
from watermarking_method import WatermarkingError


def _real_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "hello")
    data = doc.tobytes()
    doc.close()
    return data


def test_serialization_failure_is_reported_with_message(tmp_path, monkeypatch):
    pdf = tmp_path / "in.pdf"
    pdf.write_bytes(_real_pdf())

    def failing_tobytes(self, *args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(pymupdf.Document, "tobytes", failing_tobytes)

    with pytest.raises(WatermarkingError) as info:
        InvisibleTextWatermark().add_watermark(pdf, secret="s", key="k")

    assert str(info.value) == "Failed to serialize watermarked PDF: boom"