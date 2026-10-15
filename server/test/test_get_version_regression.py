"""Regression tests for the get-version / create-watermark fuzzing findings.

Written before the fixes. On the unfixed code, tests 2-5 are expected to FAIL.
Each test creates its own uniquely named throwaway user and document and
deletes the document at the end.
"""
import hashlib
import io
import re
import uuid
from urllib.parse import quote

import pytest
from server import app

LEAK_MARKERS = ("pymysql", "sqlalche", "insert into", "/app/storage", "traceback")


def minimal_pdf() -> bytes:
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R"
        b" /Resources << /Font << /F1 5 0 R >> >> >>",
        None,
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream = b"BT /F1 24 Tf 72 700 Td (Regression test) Tj ET"
    objs[3] = b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
    out = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    xref_pos = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objs) + 1,
        xref_pos,
    )
    return out


@pytest.fixture()
def owner():
    """A throwaway user with one uploaded document."""
    client = app.test_client()
    tag = uuid.uuid4().hex[:10]
    login = f"fuzztest_{tag}"
    email = f"{login}@example.com"
    password = "Fuzz-Test-Passw0rd!"

    r = client.post(
        "/api/create-user",
        json={"login": login, "password": password, "email": email},
    )
    assert r.status_code == 201, r.get_data(as_text=True)

    r = client.post("/api/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.get_data(as_text=True)
    headers = {"Authorization": f"Bearer {r.get_json()['token']}"}

    name = f"doc{tag}"
    r = client.post(
        "/api/upload-document",
        data={
            "file": (io.BytesIO(minimal_pdf()), "t.pdf", "application/pdf"),
            "name": name,
        },
        headers=headers,
        content_type="multipart/form-data",
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    doc_id = int(r.get_json()["id"])

    yield client, headers, doc_id, name

    client.delete(f"/api/delete-document/{doc_id}", headers=headers)


def make_version(client, headers, doc_id, recipient="recipient"):
    return client.post(
        f"/api/create-watermark/{doc_id}",
        json={
            "method": "toy-eof",
            "position": "0",
            "key": "testkey",
            "secret": "regression-secret",
            "intended_for": recipient,
        },
        headers=headers,
    )


MALFORMED_LINKS = [
    "abc123",
    "g" * 32,
    "a" * 31,
    "a" * 33,
    "_" * 40,
    "%25",
    quote("' OR '1'='1", safe=""),
    quote("\u00e9" * 32, safe=""),
    "..%2f..%2fetc%2fpasswd",
]


@pytest.mark.parametrize("segment", MALFORMED_LINKS)
def test_malformed_links_are_rejected_cleanly(segment):
    """Fuzzing result: malformed links give 400/404 and leak nothing."""
    client = app.test_client()
    resp = client.get("/api/get-version/" + segment)
    body = resp.get_data(as_text=True).lower()
    assert resp.status_code in (400, 404)
    assert not any(marker in body for marker in LEAK_MARKERS)


def test_repeat_watermark_keeps_first_version(owner):
    """A repeated create-watermark request must not destroy the first file."""
    client, headers, doc_id, _ = owner
    first = make_version(client, headers, doc_id)
    assert first.status_code == 201, first.get_data(as_text=True)
    link1 = first.get_json()["link"]

    make_version(client, headers, doc_id)

    resp = client.get(f"/api/get-version/{link1}")
    assert resp.status_code == 200


def test_create_watermark_errors_do_not_leak_internals(owner):
    """Error bodies must not contain SQL, driver names or storage paths."""
    client, headers, doc_id, _ = owner
    make_version(client, headers, doc_id)
    second = make_version(client, headers, doc_id)
    body = second.get_data(as_text=True).lower()
    assert not any(marker in body for marker in LEAK_MARKERS)


def test_link_is_not_derived_from_names(owner):
    """The link must be unguessable, not sha1(<name>__<recipient>.pdf)."""
    client, headers, doc_id, name = owner
    resp = make_version(client, headers, doc_id)
    assert resp.status_code == 201, resp.get_data(as_text=True)
    link = resp.get_json()["link"]

    guessable = hashlib.sha1(f"{name}__recipient.pdf".encode()).hexdigest()
    assert link != guessable
    assert re.fullmatch(r"[0-9a-f]{40}", link)


def test_link_matching_is_exact(owner):
    """Only the exact link works: no uppercase or trailing-space variants."""
    client, headers, doc_id, _ = owner
    resp = make_version(client, headers, doc_id)
    assert resp.status_code == 201, resp.get_data(as_text=True)
    link = resp.get_json()["link"]

    assert client.get(f"/api/get-version/{link}").status_code == 200
    for variant in (link.upper(), link + "%20"):
        assert client.get(f"/api/get-version/{variant}").status_code == 404, variant
