"""
Authentication and user-profile endpoints.

POST /login
POST /logout
GET  /me
PUT  /me
PUT  /me/password
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.auth.auth import create_access_token, hash_password, verify_password
from app.auth.dependencies import get_current_user
from app.core.config import settings
from app.core.logger import get_logger
from app.core.rate_limiter import login_rate_limiter
from app.db.repositories import AuditLogRepository, UserRepository
from app.schemas.api import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    UpdateProfileRequest,
    UserProfileResponse,
)

router = APIRouter(tags=["auth"])
logger = get_logger(__name__)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else "unknown"
    )


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse, dependencies=[Depends(login_rate_limiter)])
async def login(data: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    repo       = UserRepository(db)
    audit      = AuditLogRepository(db)
    ip         = _client_ip(request)
    user_agent = request.headers.get("User-Agent", "")

    user = await repo.get_by_username(data.username)
    if not user or not verify_password(data.password, user.hashed_password):
        await audit.log(
            "login_failed",
            ip_address=ip, user_agent=user_agent,
            payload={"username": data.username},
        )
        await db.commit()
        logger.warning("auth.login_failed", username=data.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    await audit.log(
        "login",
        company_id=user.company_id, user_id=user.id,
        ip_address=ip, user_agent=user_agent,
    )
    await db.commit()

    token = create_access_token({
        "sub": data.username,
        "role": user.role,
        "company_id": str(user.company_id),
    })
    logger.info("auth.login_success", username=data.username, role=user.role)
    return LoginResponse(access_token=token, role=user.role)


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """
    Invalidate the caller's JWT by adding its JTI to the Redis blocklist.
    The entry TTL matches the token's remaining lifetime (self-expiring).
    """
    from app.core.token_blocklist import block_token

    jti = user.get("jti")
    exp = user.get("exp")

    if jti and exp:
        remaining = int(exp - datetime.now(timezone.utc).timestamp())
        block_token(jti, max(remaining, 0))

    logger.info("auth.logout", user=user.get("sub", "unknown")[:20])
    return {"status": "logged_out"}


# ── My Profile ────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated user's profile."""
    repo    = UserRepository(db)
    db_user = await repo.get_by_username(user.get("sub", ""))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfileResponse(
        id=str(db_user.id),
        username=db_user.username,
        email=db_user.email,
        role=db_user.role,
        department=db_user.department,
        is_active=db_user.is_active,
        company_id=str(db_user.company_id),
        created_at=db_user.created_at.isoformat(),
    )


@router.put("/me")
async def update_my_profile(
    body: UpdateProfileRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the authenticated user's email or department."""
    repo    = UserRepository(db)
    db_user = await repo.get_by_username(user.get("sub", ""))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.email is not None:
        db_user.email = body.email
    if body.department is not None:
        db_user.department = body.department

    audit = AuditLogRepository(db)
    await audit.log(
        "profile_updated",
        company_id=db_user.company_id,
        user_id=db_user.id,
        payload={
            "email_changed": body.email is not None,
            "dept_changed": body.department is not None,
        },
    )
    await db.commit()
    logger.info("profile.updated", username=db_user.username)
    return {"status": "updated", "username": db_user.username}


@router.put("/me/password")
async def change_my_password(
    body: ChangePasswordRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the authenticated user's password after verifying the current one."""
    repo    = UserRepository(db)
    db_user = await repo.get_by_username(user.get("sub", ""))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(body.current_password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    db_user.hashed_password = hash_password(body.new_password)

    audit = AuditLogRepository(db)
    await audit.log(
        "password_changed",
        company_id=db_user.company_id,
        user_id=db_user.id,
        payload={},
    )
    await db.commit()
    logger.info("password.changed", username=db_user.username)
    return {"status": "password_changed"}
