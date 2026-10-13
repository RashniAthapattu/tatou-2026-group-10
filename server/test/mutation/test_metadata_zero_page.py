"""Covers the zero-page branch of MetadataWatermark.add_watermark (mutant 22)."""
from __future__ import annotations

import pymupdf

from metadata_watermark import MetadataWatermark

ZERO_PAGE_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
    b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"
)


def test_zero_page_pdf_gets_watermark_and_roundtrips(tmp_path):
    pdf = tmp_path / "empty.pdf"
    pdf.write_bytes(ZERO_PAGE_PDF)
    wm = MetadataWatermark()

    out_bytes = wm.add_watermark(pdf, secret="s", key="k")
    out = tmp_path / "out.pdf"
    out.write_bytes(out_bytes)

    assert wm.read_secret(out, key="k") == "s"
    with pymupdf.open(out) as doc:
        assert doc.page_count == 1