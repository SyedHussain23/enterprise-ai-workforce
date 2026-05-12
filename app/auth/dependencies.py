from fastapi import Depends, Header, HTTPException

from app.auth.auth import decode_token


def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="No token provided")

    token = authorization.removeprefix("Bearer ")
    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    return payload


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") not in ("admin", "ADMIN"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user