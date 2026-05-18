"""
Authentication utilities — password hashing and JWT creation/decoding.

JTI (JWT ID) CLAIM:
  Every token now contains a `jti` (UUID4) claim. This enables server-side
  token invalidation via the Redis blocklist in app.core.token_blocklist.
  The jti is checked by the auth dependency on every protected request.
"""
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: dict, expires_minutes: int | None = None) -> str:
    """
    Create a signed JWT with an embedded `jti` (JWT ID) for blocklist support.

    The jti is a UUID4 that uniquely identifies this token issuance. It allows
    the token to be explicitly revoked (e.g., on logout or password change)
    without waiting for the `exp` claim to pass.
    """
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload["exp"] = expire
    payload["iat"] = datetime.now(timezone.utc)   # issued-at (for TTL calculation)
    payload["jti"] = str(uuid.uuid4())            # unique token ID for blocklist
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict | None:
    """
    Decode and verify a JWT. Returns the payload dict or None on any error.

    Note: this does NOT check the blocklist — that is done in the dependency
    layer (auth/dependencies.py) so it runs only on actual protected requests,
    not on every decode call (e.g., the frontend expiry check).
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
