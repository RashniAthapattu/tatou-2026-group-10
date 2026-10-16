# Mutation testing configuration (Specialization B)

[tool.mutmut]
source_paths = [
    "src/add_after_eof.py",
    "src/hidden_comment_watermark.py",
    "src/metadata_watermark.py",
    "src/invisible_text_watermark.py",
]
also_copy = [
	"src/watermarking_utils.py",
	"src/watermarking_method.py",
	"src/unsafe_bash_bridge_append_eof.py",
]
pytest_add_cli_args_test_selection = ["test/mutation/"]
on_dependency_change = "rerun"
[tool.mutmut]
source_paths = [
    "src/add_after_eof.py",
    "src/hidden_comment_watermark.py",
    "src/metadata_watermark.py",
    "src/invisible_text_watermark.py",
]
also_copy = [
	"src/watermarking_utils.py",
	"src/watermarking_method.py",
	"src/unsafe_bash_bridge_append_eof.py",
]
pytest_add_cli_args_test_selection = ["test/mutation/"]
on_dependency_change = "rerun"

# Workflow file

name: Mutation testing

on:
  pull_request:
    paths:
      - "server/**"
  push:
    branches: [main]
    paths:
      - "server/**"
  workflow_dispatch:

jobs:
  mutmut:
    name: mutmut on watermarking modules
    runs-on: ubuntu-latest
    timeout-minutes: 90
    defaults:
      run:
        working-directory: server
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install \
            "PyMuPDF>=1.21.1" "Flask==3.0.3" "PyMySQL==1.1.2" \
            "SQLAlchemy==2.0.43" "dill==0.4.0" "cryptography>=41.0.0" \
            "rmap @ https://github.com/nharrand/RMAP/releases/download/v2.0.0/rmap-2.0.0-py3-none-any.whl" \
            "pytest>=7.0.0" "mutmut==3.8.0"

      - name: Run mutation-selection tests
        run: python -m pytest test/mutation -o addopts="" -q

      - name: Run mutmut
        run: |
          rm -rf mutants .mutmut-cache
          mutmut run
          mutmut results > mutmut-results.txt

      - name: Summarise survivors
        run: |
          {
            echo "### mutmut survivors"
            echo ""
            echo "Survived: $(grep -c ': survived' mutmut-results.txt || true)"
            echo ""
            echo '```'
            grep ': survived' mutmut-results.txt || echo "none"
            echo '```'
          } >> "$GITHUB_STEP_SUMMARY"

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: mutmut-results
          path: server/mutmut-results.txt

# Interesting mutants

These survivors exposed a real gap in the tests and were fixed by adding a test:
Metadata zero-page branch. Removing the zero-page handling survived because no test used a PDF with zero pages. Killed by test_metadata_zero_page.py, which builds a zero-page PDF by hand.
Invisible-text serialization error. The error path in add_watermark survived because nothing made tobytes fail. Killed by test_invisible_text_serialize_error.py, which makes pymupdf.Document.tobytes raise.
Hidden-comment read_secret, start == -1 changed. Survived because no test had a PDF without the marker but with a colon after the offset. The mutant then parsed garbage instead of raising not-found. Killed by test_no_marker_with_colon_after_offset_is_not_found. Confirmed by hand on a copy of the code.
Hidden-comment marker placement. Changing the newline before the marker to XX plus newline survived. Killed by a test that checks the marker starts on its own line.

## Bugs found

# In the test suite

The bash-bridge-eof exclusion compared the class name, not the registry key, so it never applied.
The sample PDF for the watermarking tests was not a valid PDF, so the invisible-text method was silently skipped.
The all-methods test skipped instead of failing when a method was not applicable.
test_wrong_key_is_rejected was marked xfail, which hid a real defect in the metadata module.

# In the project
The metadata watermark ignored the key. Anyone could read the secret without it.
The hidden-comment watermark ignored the key for the same reason.
A secret or tag containing non-ASCII characters raised TypeError from hmac.compare_digest, which accepts only ASCII str arguments.
The metadata zero-page branch had no test.
The invisible-text serialization error branch had no test.
The return annotation of is_watermark_applicable in watermarking_utils.py disagrees with what it returns (bytes vs bool). Fixed in the Fixes section.

# Fixes

Exclusion filter: compares against the registry key bash-bridge-eof.
Sample PDF: built with PyMuPDF (pymupdf.open(), new_page(), insert_text). The test asserts applicability instead of skipping.
xfail: removed once the key check was fixed. The test now passes.
Keyed format (v2) for the metadata and hidden-comment watermarks. The tag is HMAC-SHA256 of the secret under the key, in hex. A wrong key raises InvalidKeyError. This is a breaking change: v1 watermarks are no longer read.
Non-ASCII input: the tag is compared as bytes, so a non-ASCII value is rejected as a wrong key instead of raising TypeError.
New tests in test/mutation/: zero-page metadata, invisible-text serialization error, metadata v2 format (colons, tampering, malformed values, wrong key, non-ASCII), and hidden-comment keyed format (marker placement, no marker, non-ASCII, malformed markers).
Annotation: is_watermarking_applicable now returns bool instead of bytes, and its docstring is corrected. A regression test is in test/mutation/test_is_watermarking_applicable.py.
