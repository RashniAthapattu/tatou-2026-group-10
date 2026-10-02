import secrets

from rmap.crypto import encrypt_json
from server import app


def test_rmap_rejects_unmatched_server_nonce():
    client = app.test_client()

    # Create a correctly encrypted Message 2, but use a server nonce that was never issued by this server.
    fake_nonce_server = secrets.randbits(64)

    msg2 = encrypt_json(
        {"nonceServer": fake_nonce_server},
        app.config["RMAP_SERVER"].serverPublicKey,
    )

    response = client.post(
        "/api/rmap-get-link",
        json=msg2,
    )

    assert response.status_code == 400
    assert response.is_json

    data = response.get_json()

    assert "No pending session matches the given nonceServer" in data["error"]