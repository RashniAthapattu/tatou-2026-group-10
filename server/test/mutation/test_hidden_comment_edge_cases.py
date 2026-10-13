import pytest

from hidden_comment_watermark import HiddenCommentWatermark
from watermarking_method import SecretNotFoundError

SAMPLE = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"


@pytest.fixture
def wm():
    return HiddenCommentWatermark()


def test_get_usage_text_is_exact():
    assert HiddenCommentWatermark.get_usage() == (
        "Hides the secret inside a PDF comment. Position is ignored."
    )


def test_is_watermark_applicable_returns_true(wm):
    assert wm.is_watermark_applicable(SAMPLE) is True


def test_empty_secret_exact_message(wm):
    with pytest.raises(ValueError) as exc:
        wm.add_watermark(SAMPLE, secret="", key="k")
    assert str(exc.value) == "Secret must not be empty"


def test_roundtrip(wm):
    out = wm.add_watermark(SAMPLE, secret="hello", key="k")
    assert wm.read_secret(out, key="k") == "hello"


def test_latest_marker_wins(wm):
    out = wm.add_watermark(SAMPLE, secret="first", key="k")
    out = wm.add_watermark(out, secret="second", key="k")
    assert wm.read_secret(out, key="k") == "second"


def test_not_found_exact_message(wm):
    with pytest.raises(SecretNotFoundError) as exc:
        wm.read_secret(SAMPLE, key="k")
    assert str(exc.value) == "Hidden watermark not found"


def test_text_after_marker_is_not_read(wm):
    out = wm.add_watermark(SAMPLE, secret="s", key="k") + b"junk\n"
    assert wm.read_secret(out, key="k") == "s"


def test_marker_at_eof_without_newline(wm):
    pdf = wm.add_watermark(SAMPLE, secret="s", key="k").rstrip(b"\n")
    assert wm.read_secret(pdf, key="k") == "s"