import secrets

from rmap.crypto import encrypt_json
from server import app


def test_rmap_rejects_unregistered_identity():
    client = app.test_client()

    # Create a correctly encrypted Message 1, but use an identity that is not registered with the RMAP server.
    nonce_client = secrets.randbits(64)

    msg1 = encrypt_json(
        {
            "identity": "Definitely_Not_A_Registered_Identity",
            "nonceClient": nonce_client,
        },
        app.config["RMAP_SERVER"].serverPublicKey,
    )

    response = client.post(
        "/api/rmap-initiate",
        json=msg1,
    )

    print("\n=== FIA_UID.2: Unregistered Identity ===")
    print("REQUEST:")
    print("POST /api/rmap-initiate")
    print("nonceClient:", nonce_client)
    print("Encrypted JSON:", msg1)
    print("RESPONSE:")
    print("HTTP", response.status_code)
    print("JSON:", response.get_json())

    assert response.status_code == 400
    assert response.is_json

    data = response.get_json()

    assert "Unknown identity" in data["error"]