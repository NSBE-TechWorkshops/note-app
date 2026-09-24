import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

security = HTTPBearer()

_jwks_cache: dict | None = None


def _get_jwks() -> dict:
    """Fetch and cache Cognito JWKS."""
    global _jwks_cache
    if _jwks_cache is None:
        resp = httpx.get(settings.cognito_jwks_url, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    return _jwks_cache


def _decode_token(token: str) -> dict:
    """Verify and decode a Cognito JWT access token."""
    jwks = _get_jwks()
    try:
        header = jwt.get_unverified_header(token)
    except jwt.DecodeError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Find matching key
    key = next((k for k in jwks["keys"] if k["kid"] == header.get("kid")), None)
    if key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token key not found")

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=settings.cognito_issuer,
            options={"verify_aud": False},  # Cognito access tokens use client_id claim, not aud
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Verify it's an access token
    if payload.get("token_use") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not an access token")

    return payload


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: verify JWT and return or create the User."""
    payload = _decode_token(credentials.credentials)
    cognito_sub = payload["sub"]
    email = payload.get("email", "")

    user = db.query(User).filter(User.cognito_sub == cognito_sub).first()
    if user is None:
        user = User(cognito_sub=cognito_sub, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)

    return user
