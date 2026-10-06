import time

import jwt
import pytest

import main
from auth import JWT_ALGO, JWT_SECRET, verify_password
from conftest import signup


class TestSignup:
    def test_returns_token_and_identity(self, client):
        data = signup(client, "alice")
        assert data["username"] == "alice" and data["user_id"] >= 1 and data["token"]

    def test_username_is_trimmed(self, client):
        assert signup(client, "  bob  ")["username"] == "bob"

    def test_short_password_rejected(self, client):
        r = client.post("/auth/signup", json={"username": "alice", "password": "12345"})
        assert r.status_code == 400

    def test_blank_username_rejected(self, client):
        r = client.post("/auth/signup", json={"username": "   ", "password": "secret123"})
        assert r.status_code == 400

    def test_duplicate_username_conflicts(self, client):
        signup(client, "alice")
        r = client.post("/auth/signup", json={"username": "alice", "password": "another123"})
        assert r.status_code == 409

    def test_password_is_stored_hashed_never_plaintext(self, client, fake_db):
        signup(client, "alice", "secret123")
        stored = fake_db.get_user_by_username("alice")["password_hash"]
        assert "secret123" not in stored
        assert verify_password("secret123", stored)
        assert not verify_password("wrong-password", stored)

    def test_same_password_gets_different_salt(self, client, fake_db):
        signup(client, "alice", "secret123")
        signup(client, "bob", "secret123")
        assert (fake_db.get_user_by_username("alice")["password_hash"]
                != fake_db.get_user_by_username("bob")["password_hash"])


class TestLogin:
    def test_correct_credentials(self, client):
        signup(client, "alice", "secret123")
        r = client.post("/auth/login", json={"username": "alice", "password": "secret123"})
        assert r.status_code == 200 and r.json()["username"] == "alice" and r.json()["token"]

    def test_wrong_password(self, client):
        signup(client, "alice", "secret123")
        r = client.post("/auth/login", json={"username": "alice", "password": "nope-nope"})
        assert r.status_code == 401

    def test_unknown_user_gets_same_error_as_wrong_password(self, client):
        signup(client, "alice", "secret123")
        wrong_pw = client.post("/auth/login", json={"username": "alice", "password": "nope-nope"})
        unknown = client.post("/auth/login", json={"username": "ghost", "password": "nope-nope"})
        assert unknown.status_code == 401
        assert unknown.json() == wrong_pw.json(), "error text must not reveal which usernames exist"

    def test_google_only_account_cannot_password_login(self, client, fake_db):
        fake_db.create_user("g@example.com", password_hash=None, google_id="g-1")
        r = client.post("/auth/login", json={"username": "g@example.com", "password": "anything1"})
        assert r.status_code == 401


class TestTokens:
    def test_me_with_valid_token(self, client):
        data = signup(client, "alice")
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {data['token']}"})
        assert r.status_code == 200 and r.json() == {"user_id": data["user_id"], "username": "alice"}

    @pytest.mark.parametrize("header", [None, "", "Token abc", "Bearer", "Bearer not.a.jwt"])
    def test_missing_or_malformed_token(self, client, header):
        h = {"Authorization": header} if header is not None else {}
        assert client.get("/auth/me", headers=h).status_code == 401

    def test_token_signed_with_wrong_secret_rejected(self, client):
        forged = jwt.encode({"sub": "1", "username": "alice", "exp": int(time.time()) + 600},
                            "some-other-secret", algorithm=JWT_ALGO)
        assert client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401

    def test_expired_token_rejected(self, client):
        data = signup(client, "alice")
        expired = jwt.encode({"sub": str(data["user_id"]), "username": "alice",
                              "exp": int(time.time()) - 5}, JWT_SECRET, algorithm=JWT_ALGO)
        assert client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401

    def test_unsigned_alg_none_token_rejected(self, client):
        none_tok = jwt.encode({"sub": "1", "username": "alice"}, key=None, algorithm="none")
        assert client.get("/auth/me", headers={"Authorization": f"Bearer {none_tok}"}).status_code == 401

    def test_token_for_deleted_user_is_404(self, client, headers):
        assert client.delete("/account", headers=headers).status_code == 200
        assert client.get("/auth/me", headers=headers).status_code == 404


PROTECTED = [("GET", "/auth/me"), ("POST", "/chat"), ("POST", "/translate"), ("POST", "/speak"),
             ("GET", "/conversations"), ("DELETE", "/conversations/1"),
             ("GET", "/conversations/1/messages"), ("GET", "/history"), ("GET", "/rating"),
             ("POST", "/soundtrack"), ("GET", "/soundtrack/weekly"), ("GET", "/reflection"),
             ("GET", "/export"), ("GET", "/export/doctor-report"), ("DELETE", "/account")]


@pytest.mark.parametrize("method,path", PROTECTED)
def test_every_private_endpoint_requires_login(client, method, path):
    r = client.request(method, path, json={} if method == "POST" else None)
    assert r.status_code == 401, f"{method} {path} answered {r.status_code} without a token"


class TestGoogleSignIn:
    def test_unconfigured_is_503(self, client, monkeypatch):
        monkeypatch.setattr(main, "GOOGLE_CLIENT_ID", None)
        assert client.post("/auth/google", json={"credential": "x"}).status_code == 503

    def test_invalid_credential_is_401(self, client, monkeypatch):
        monkeypatch.setattr(main, "GOOGLE_CLIENT_ID", "client-id")
        def boom(*a, **k): raise ValueError("bad token")
        monkeypatch.setattr(main.google_id_token, "verify_oauth2_token", boom)
        assert client.post("/auth/google", json={"credential": "x"}).status_code == 401

    def test_new_google_user_is_created(self, client, monkeypatch, fake_db):
        monkeypatch.setattr(main, "GOOGLE_CLIENT_ID", "client-id")
        monkeypatch.setattr(main.google_id_token, "verify_oauth2_token",
                            lambda *a, **k: {"sub": "g-42", "email": "new@example.com"})
        r = client.post("/auth/google", json={"credential": "x"})
        assert r.status_code == 200 and r.json()["username"] == "new@example.com"
        assert fake_db.get_user_by_google_id("g-42")["username"] == "new@example.com"

    def test_existing_email_account_gets_linked_not_duplicated(self, client, monkeypatch, fake_db):
        signup(client, "me@example.com", "secret123")
        monkeypatch.setattr(main, "GOOGLE_CLIENT_ID", "client-id")
        monkeypatch.setattr(main.google_id_token, "verify_oauth2_token",
                            lambda *a, **k: {"sub": "g-7", "email": "me@example.com"})
        assert client.post("/auth/google", json={"credential": "x"}).status_code == 200
        assert len(fake_db.users) == 1
        assert fake_db.get_user_by_username("me@example.com")["google_id"] == "g-7"
