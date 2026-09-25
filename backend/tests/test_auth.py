"""JWT verification, exercised with a throwaway RSA key so nothing calls Cognito."""

import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.middleware import auth as auth_middleware
from app.models import User

KID = "test-key"


@pytest.fixture(scope="module")
def private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(autouse=True)
def fake_jwks(monkeypatch, private_key):
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk["kid"] = KID
    monkeypatch.setattr(auth_middleware, "_get_jwks", lambda: {"keys": [jwk]})


@pytest.fixture
def make_token(private_key):
    def _make(kid: str = KID, **overrides) -> str:
        claims = {
            "iss": settings.cognito_issuer,
            "token_use": "access",
            "sub": "cognito-sub-123",
            "email": "student@example.com",
            "exp": int(time.time()) + 300,
        }
        claims.update(overrides)
        return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": kid})

    return _make


def get_me(client, token: str | None = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.get("/me", headers=headers)


def test_missing_token_is_rejected(anon_client):
    assert get_me(anon_client).status_code in (401, 403)


def test_garbage_token_is_rejected(anon_client):
    assert get_me(anon_client, "not-a-jwt").status_code == 401


def test_expired_token_is_rejected(anon_client, make_token):
    response = get_me(anon_client, make_token(exp=int(time.time()) - 10))

    assert response.status_code == 401
    assert response.json()["detail"] == "Token expired"


def test_token_from_wrong_issuer_is_rejected(anon_client, make_token):
    assert get_me(anon_client, make_token(iss="https://evil.example.com/pool")).status_code == 401


def test_id_token_is_rejected(anon_client, make_token):
    response = get_me(anon_client, make_token(token_use="id"))

    assert response.status_code == 401
    assert response.json()["detail"] == "Not an access token"


def test_unknown_signing_key_is_rejected(anon_client, make_token):
    assert get_me(anon_client, make_token(kid="some-other-key")).status_code == 401


@pytest.mark.integration
def test_valid_token_returns_profile_and_creates_user_once(anon_client, db, make_token):
    app.dependency_overrides[get_db] = lambda: db
    token = make_token()

    first = get_me(anon_client, token)
    second = get_me(anon_client, token)
    app.dependency_overrides.clear()

    assert first.status_code == 200
    assert first.json()["email"] == "student@example.com"
    assert second.json()["id"] == first.json()["id"]
    assert db.query(User).filter(User.cognito_sub == "cognito-sub-123").count() == 1


@pytest.mark.integration
def test_patch_me_updates_display_name(client, db, user):
    response = client.patch("/me", json={"display_name": "  Kyle  "})

    assert response.status_code == 200
    assert response.json()["display_name"] == "Kyle"
    db.refresh(user)
    assert user.display_name == "Kyle"


def test_patch_me_rejects_empty_display_name(unit_client):
    assert unit_client.patch("/me", json={"display_name": ""}).status_code == 422
