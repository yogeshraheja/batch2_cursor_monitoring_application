"""Integration tests for server inventory routes."""

from servers import AUTH_KEY, AUTH_LOCALHOST, AUTH_PASSWORD

TEST_PASSWORD = "test-pass-not-for-prod"
TEST_USERNAME = "admin"


def _login(client):
    client.post(
        "/login",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )


def test_add_password_server_and_redirect(client):
    _login(client)
    response = client.post(
        "/servers/add",
        data={
            "name": "lab",
            "host": "10.1.2.3",
            "port": "22",
            "ssh_user": "monitor",
            "auth_type": AUTH_PASSWORD,
            "password": "demo-pass",
            "private_key": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/overview" in response.headers["Location"]

    overview = client.get("/overview")
    assert b"lab" in overview.data
    assert b"demo-pass" not in overview.data


def test_add_validation_missing_password(client):
    _login(client)
    response = client.post(
        "/servers/add",
        data={
            "name": "bad",
            "host": "10.1.2.3",
            "port": "22",
            "ssh_user": "monitor",
            "auth_type": AUTH_PASSWORD,
            "password": "",
            "private_key": "",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Password is required" in response.data


def test_add_localhost_and_key_modes(client):
    _login(client)
    r1 = client.post(
        "/servers/add",
        data={
            "name": "local",
            "host": "",
            "port": "22",
            "ssh_user": "",
            "auth_type": AUTH_LOCALHOST,
            "password": "",
            "private_key": "",
        },
        follow_redirects=False,
    )
    assert r1.status_code == 302

    r2 = client.post(
        "/servers/add",
        data={
            "name": "keyhost",
            "host": "lab.example",
            "port": "22",
            "ssh_user": "ops",
            "auth_type": AUTH_KEY,
            "password": "",
            "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\ndemo\n-----END OPENSSH PRIVATE KEY-----",
        },
        follow_redirects=False,
    )
    assert r2.status_code == 302

    overview = client.get("/overview")
    assert b"local" in overview.data
    assert b"keyhost" in overview.data
    assert b"BEGIN OPENSSH" not in overview.data


def test_edit_delete_and_404(client, app):
    _login(client)
    client.post(
        "/servers/add",
        data={
            "name": "editme",
            "host": "10.9.9.9",
            "port": "22",
            "ssh_user": "u",
            "auth_type": AUTH_PASSWORD,
            "password": "first",
            "private_key": "",
        },
    )
    server_id = app.server_store.list()[0].id

    response = client.post(
        f"/servers/{server_id}/edit",
        data={
            "name": "edited",
            "host": "10.9.9.8",
            "port": "2222",
            "ssh_user": "u2",
            "auth_type": AUTH_PASSWORD,
            "password": "",
            "private_key": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    updated = app.server_store.get(server_id)
    assert updated.name == "edited"
    assert updated.password == "first"

    detail = client.get(f"/servers/{server_id}")
    assert detail.status_code == 200
    assert b"edited" in detail.data
    assert b"first" not in detail.data

    missing = client.get("/servers/does-not-exist")
    assert missing.status_code == 404

    delete = client.post(f"/servers/{server_id}/delete", follow_redirects=False)
    assert delete.status_code == 302
    assert app.server_store.get(server_id) is None

    delete_missing = client.post("/servers/gone/delete")
    assert delete_missing.status_code == 404


def test_mutations_require_login(client):
    response = client.post(
        "/servers/add",
        data={
            "name": "x",
            "host": "1.2.3.4",
            "port": "22",
            "ssh_user": "u",
            "auth_type": AUTH_PASSWORD,
            "password": "p",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_get_does_not_delete(client, app):
    _login(client)
    client.post(
        "/servers/add",
        data={
            "name": "keep",
            "host": "1.2.3.4",
            "port": "22",
            "ssh_user": "u",
            "auth_type": AUTH_PASSWORD,
            "password": "p",
        },
    )
    server_id = app.server_store.list()[0].id
    response = client.get(f"/servers/{server_id}/delete")
    assert response.status_code in (405, 404)
    assert app.server_store.get(server_id) is not None
