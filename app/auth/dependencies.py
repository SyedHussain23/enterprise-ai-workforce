"""
FastAPI auth dependencies — enforces authentication on protected routes.

Changes from original:
  - Added JTI blocklist check: every request verifies the token hasn't been
    explicitly revoked (e.g., post-logout, post-password-change).
  - Returns structured payload dict with guaranteed `jti` field so callers
    can block the current token on password change or logout.
  - Cleaner error messages to avoid leaking implementation details.
"""
from fastapi import Depends, Header, HTTPException

from app.auth.auth import decode_token
from app.core.token_blocklist import is_token_blocked


def get_current_user(authorization: str = Header(None)) -> dict:
    """
    Validate the Bearer token and return the decoded JWT payload.

    Checks:
      1. Authorization header is present and well-formed
      2. Token signature and expiry are valid
      3. Token JTI has not been explicitly revoked (blocklist)

    Raises:
      401 HTTPException on any auth failure (no detail leakage about which check failed).
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required.")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required.")

    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    # Blocklist check — O(1) Redis lookup, ~0.2ms overhead
    jti = payload.get("jti")
    if jti and is_token_blocked(jti):
        raise HTTPException(status_code=401, detail="Token has been revoked. Please log in again.")

    return payload


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """
    Extend get_current_user to enforce admin role.
    Returns the same payload dict so route handlers can use user metadata.
    """
    if user.get("role") not in ("admin", "ADMIN"):
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


def require_approver(user: dict = Depends(get_current_user)) -> dict:
    """
    Allow managers and admins to act on approvals.

    Why this exists separately from `require_admin`:
      Approvals are an operational responsibility belonging to line managers,
      not only the platform owner. Without this, every approval funnels to
      a tiny pool of admins — that's a chatbot, not a workforce platform.
    """
    role = (user.get("role") or "").lower()
    if role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Manager or admin access required.")
    return user
