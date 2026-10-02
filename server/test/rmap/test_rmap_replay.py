import json
import os
import secrets

from rmap import RMAPClient
from server import app


def test_rmap_replay_of_message_2_is_rejected():
    client = app.test_client()

    rmap_client = RMAPClient(
        identity="Group_10",
        client_private_key_path="keys/server_priv.asc",
        server_public_key_path="keys/server_pub.asc",
        passphrase=os.environ.get("RMAP_SERVER_PASSPHRASE"),
    )

    # Message 1: start a fresh legitimate handshake.
    msg1 = rmap_client.build_msg1()

    response1 = client.post(
        "/api/rmap-initiate",
        json=msg1,
    )

    assert response1.status_code == 200
    assert response1.is_json

    # Process the server response and build Message 2.
    rmap_client.process_resp1(response1.get_json())
    msg2 = rmap_client.build_msg2()

    # First use of Message 2 must succeed.
    response2 = client.post(
        "/api/rmap-get-link",
        json=msg2,
    )

    assert response2.status_code == 200
    assert response2.is_json

    link = rmap_client.process_resp2(response2.get_json())

    assert isinstance(link, str)
    assert len(link) == 32

    # Replay the exact same Message 2.
    replay_response = client.post(
        "/api/rmap-get-link",
        json=msg2,
    )

    assert replay_response.status_code == 409
    assert replay_response.is_json

    replay_data = replay_response.get_json()

    assert replay_data["error"] == "RMAP Message 2 has already been used"
