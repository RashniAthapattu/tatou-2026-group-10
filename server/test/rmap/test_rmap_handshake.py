import os

from rmap import RMAPClient
from server import app


def test_rmap_handshake_succeeds():
    client = app.test_client()

    rmap_client = RMAPClient(
        identity="Group_10",
        client_private_key_path="keys/server_priv.asc",
        server_public_key_path="keys/server_pub.asc",
        passphrase=os.environ.get("RMAP_SERVER_PASSPHRASE"),
    )

    # Message 1: start a legitimate handshake.
    msg1 = rmap_client.build_msg1()

    response1 = client.post(
        "/api/rmap-initiate",
        json=msg1,
    )

    assert response1.status_code == 200
    assert response1.is_json

    # Process Message 1 response and build Message 2.
    nonce_client, nonce_server = rmap_client.process_resp1(
        response1.get_json()
    )

    assert nonce_client is not None
    assert nonce_server is not None

    msg2 = rmap_client.build_msg2()

    # Message 2: complete the legitimate handshake.
    response2 = client.post(
        "/api/rmap-get-link",
        json=msg2,
    )

    assert response2.status_code == 200
    assert response2.is_json

    # The server should return a valid session link.
    link = rmap_client.process_resp2(response2.get_json())

    assert isinstance(link, str)
    assert len(link) == 32
    assert link