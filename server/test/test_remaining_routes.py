import io
import uuid

import pytest
from server import app


def minimal_pdf() -> bytes:
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R"
        b" /Resources << /Font << /F1 5 0 R >> >> >>",
        None,
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream = b"BT /F1 24 Tf 72 700 Td (Route test) Tj ET"
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


def new_user(client):
    tag = uuid.uuid4().hex[:10]
    login = f"routes_{tag}"
    email = f"{login}@example.com"
    password = "Routes-Test-Passw0rd!"
    r = client.post(
        "/api/create-user",
        json={"login": login, "password": password, "email": email},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    r = client.post("/api/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.get_data(as_text=True)
    return {"Authorization": f"Bearer {r.get_json()['token']}"}


@pytest.fixture()
def doc():
    """A throwaway user with one uploaded document and one watermark."""
    client = app.test_client()
    headers = new_user(client)
    r = client.post(
        "/api/upload-document",
        data={
            "file": (io.BytesIO(minimal_pdf()), "r.pdf", "application/pdf"),
            "name": f"routes_{uuid.uuid4().hex[:8]}",
        },
        headers=headers,
        content_type="multipart/form-data",
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    doc_id = int(r.get_json()["id"])

    r = client.post(
        f"/api/create-watermark/{doc_id}",
        json={
            "method": "hidden-comment",
            "position": None,
            "key": "route-key",
            "secret": "route-secret",
            "intended_for": "route-recipient",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.get_data(as_text=True)

    yield client, headers, doc_id

    client.delete(f"/api/delete-document/{doc_id}", headers=headers)


def test_list_versions_by_path(doc):
    client, headers, doc_id = doc
    r = client.get(f"/api/list-versions/{doc_id}", headers=headers)
    assert r.status_code == 200
    intended = [v["intended_for"] for v in r.get_json()["versions"]]
    assert "route-recipient" in intended


def test_list_versions_by_query(doc):
    client, headers, doc_id = doc
    r = client.get(f"/api/list-versions?documentid={doc_id}", headers=headers)
    assert r.status_code == 200
    intended = [v["intended_for"] for v in r.get_json()["versions"]]
    assert "route-recipient" in intended


def test_list_all_versions_includes_new_version(doc):
    client, headers, doc_id = doc
    r = client.get("/api/list-all-versions", headers=headers)
    assert r.status_code == 200
    doc_ids = [int(v["documentid"]) for v in r.get_json()["versions"]]
    assert doc_id in doc_ids


def test_get_document_by_path_returns_pdf(doc):
    client, headers, doc_id = doc
    r = client.get(f"/api/get-document/{doc_id}", headers=headers)
    assert r.status_code == 200
    assert r.data.startswith(b"%PDF")


def test_get_document_by_query_returns_pdf(doc):
    client, headers, doc_id = doc
    r = client.get(f"/api/get-document?id={doc_id}", headers=headers)
    assert r.status_code == 200
    assert r.data.startswith(b"%PDF")


def test_get_document_hidden_from_other_user(doc):
    client, _, doc_id = doc
    other_headers = new_user(client)
    r = client.get(f"/api/get-document/{doc_id}", headers=other_headers)
    assert r.status_code == 404

def test_read_watermark_by_path_reports_no_watermark_on_original(doc):
    client, headers, doc_id = doc
    r = client.post(
        f"/api/read-watermark/{doc_id}",
        json={"method": "hidden-comment", "key": "route-key"},
        headers=headers,
    )
    assert r.status_code == 400
    assert "Hidden watermark not found" in r.get_json()["error"]


def test_read_watermark_by_body_id_reports_no_watermark_on_original(doc):
    client, headers, doc_id = doc
    r = client.post(
        "/api/read-watermark",
        json={"id": doc_id, "method": "hidden-comment", "key": "route-key"},
        headers=headers,
    )
    assert r.status_code == 400
    assert "Hidden watermark not found" in r.get_json()["error"]

def test_load_plugin_requires_filename(doc):
    client, headers, _ = doc
    r = client.post("/api/load-plugin", json={}, headers=headers)
    assert r.status_code == 400


@pytest.mark.xfail(
    strict=True,
    reason="load-plugin 404 branch uses undefined name 'safe' (NameError -> 500)",
)
def test_load_plugin_missing_file_returns_404(doc):
    client, headers, _ = doc
    r = client.post(
        "/api/load-plugin",
        json={"filename": f"missing_{uuid.uuid4().hex}.pkl"},
        headers=headers,
    )
    assert r.status_code == 404