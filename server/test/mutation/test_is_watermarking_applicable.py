from __future__ import annotations

import typing

import pymupdf

from watermarking_utils import is_watermarking_applicable


def _real_pdf() -> bytes:
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Sample page")
    data = doc.tobytes()
    doc.close()
    return data


def test_return_annotation_is_bool():
    # Regression: the annotation said bytes while the function returns a bool.
    hints = typing.get_type_hints(is_watermarking_applicable)
    assert hints["return"] is bool


def test_returns_true_for_applicable_pdf():
    assert is_watermarking_applicable("hidden-comment", _real_pdf()) is True


def test_returns_false_for_non_pdf_input():
    assert is_watermarking_applicable("invisible-text", b"not a pdf") is False