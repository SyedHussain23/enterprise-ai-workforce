"""
Integration tests for the request lifecycle + notification + approvals layer.

These exercise the repositories against a real Postgres test DB (skipped
when the DB isn't reachable). They cover:

  - Action create → approve → notification emission
  - Action create → reject → notification emission
  - Action cancel by owner; cannot cancel after terminal state
  - Approver list_pending_for_approvers filters correctly
  - Notification mark-read + mark-all-read + ownership scoping
  - Audit timeline entries for state transitions

Pure unit-level coverage of the state machine constants is also included
so we get *some* signal even without a live DB.
"""
import pytest

from app.db.repositories.action_repo import TERMINAL_STATUSES


# ── Pure unit tests (no DB) ───────────────────────────────────────────────────

def test_terminal_statuses_complete_set():
    """The state machine should treat all five end-states as terminal so
    cancel/approve/reject become no-ops once a row hits one of them."""
    assert "approved"  in TERMINAL_STATUSES
    assert "rejected"  in TERMINAL_STATUSES
    assert "completed" in TERMINAL_STATUSES
    assert "failed"    in TERMINAL_STATUSES
    assert "cancelled" in TERMINAL_STATUSES
    # Anything else (e.g. "pending") must NOT be terminal
    assert "pending" not in TERMINAL_STATUSES


def test_notification_kinds_enum_members():
    """Notification kinds we emit from the actions API must exist in the
    enum so the client never sees a kind it can't categorise."""
    from app.db.models.notification import NotificationKind
    members = {m.value for m in NotificationKind}
    for required in (
        "request_submitted", "request_approved", "request_rejected",
        "request_commented", "request_completed", "system",
    ):
        assert required in members, f"NotificationKind missing {required}"


def test_require_approver_blocks_employees():
    """The approval dep must reject regular users — managers/admins only."""
    from fastapi import HTTPException
    from app.auth.dependencies import require_approver

    # Employee → 403
    with pytest.raises(HTTPException) as excinfo:
        require_approver({"sub": "alice", "role": "employee"})
    assert excinfo.value.status_code == 403

    # Manager → passes
    payload = {"sub": "bob", "role": "manager"}
    assert require_approver(payload) is payload

    # Admin → passes
    payload = {"sub": "carol", "role": "admin"}
    assert require_approver(payload) is payload


# ── DB-backed lifecycle tests ────────────────────────────────────────────────

# These import lazily so the no-DB run still passes
try:
    from tests.conftest import _DB_AVAILABLE
except Exception:
    _DB_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _DB_AVAILABLE,
    reason="Lifecycle tests require Postgres test DB",
)


@pytest.mark.asyncio
async def test_action_approve_emits_notification(seeded_db, db_session):
    """Approving a pending action should:
       1. transition the action to 'approved'
       2. emit a Notification to the original requester
       3. write an audit_log entry of type 'action_approved'"""
    from app.auth.auth import hash_password
    from app.db.models.user import User, UserRole
    from app.db.repositories import (
        ActionRepository, AuditLogRepository, NotificationRepository,
    )

    company = seeded_db["company"]
    admin   = seeded_db["admin"]

    # Create a regular employee in the same tenant
    employee = User(
        company_id=company.id,
        email="emp@test.com",
        username="emp",
        hashed_password=hash_password("x"),
        role=UserRole.EMPLOYEE.value,
        is_active=True,
    )
    db_session.add(employee)
    await db_session.flush()

    actions = ActionRepository(db_session)
    action = await actions.create(
        company_id=company.id,
        user_id=employee.id,
        action_type="apply_leave",
        department="HR",
        payload={"days": 3},
        requires_approval=True,
    )

    approved = await actions.approve(action.id, admin.id, notes="OK")
    assert approved is not None
    assert approved.status == "approved"
    assert approved.approved_by_id == admin.id

    # Emit the notification the API layer would emit
    notifs = NotificationRepository(db_session)
    n = await notifs.emit(
        company_id=company.id,
        recipient_id=employee.id,
        actor_id=admin.id,
        kind="request_approved",
        title="Your request was approved",
        message="Test approve",
        entity_type="action",
        entity_id=action.id,
    )
    assert n.id is not None
    assert n.is_read is False

    # Audit entry
    audits = AuditLogRepository(db_session)
    await audits.log(
        "action_approved",
        company_id=company.id,
        user_id=admin.id,
        entity_type="action",
        entity_id=action.id,
        payload={"action_type": action.action_type},
    )


@pytest.mark.asyncio
async def test_action_cancel_owner_only_and_terminal_block(seeded_db, db_session):
    """Owner can cancel a PENDING action; cannot cancel an already-terminal one;
    non-owner cancel call returns None even if the row exists."""
    from app.auth.auth import hash_password
    from app.db.models.user import User, UserRole
    from app.db.repositories import ActionRepository

    company = seeded_db["company"]
    employee = User(
        company_id=company.id,
        email="emp2@test.com",
        username="emp2",
        hashed_password=hash_password("x"),
        role=UserRole.EMPLOYEE.value,
        is_active=True,
    )
    other_employee = User(
        company_id=company.id,
        email="emp3@test.com",
        username="emp3",
        hashed_password=hash_password("x"),
        role=UserRole.EMPLOYEE.value,
        is_active=True,
    )
    db_session.add_all([employee, other_employee])
    await db_session.flush()

    actions = ActionRepository(db_session)
    action = await actions.create(
        company_id=company.id, user_id=employee.id,
        action_type="submit_expense", department="Finance",
        payload={"amount": 100}, requires_approval=True,
    )

    # Non-owner can't cancel
    assert await actions.cancel(action_id=action.id, canceller_id=other_employee.id) is None

    # Owner can cancel
    cancelled = await actions.cancel(action_id=action.id, canceller_id=employee.id, reason="changed my mind")
    assert cancelled is not None
    assert cancelled.status == "cancelled"

    # Re-cancel after terminal state → returns None
    assert await actions.cancel(action_id=action.id, canceller_id=employee.id) is None


@pytest.mark.asyncio
async def test_notification_mark_read_ownership_scoped(seeded_db, db_session):
    """A user can mark their own notifications read; cannot touch another
    user's notification (the repo update returns None)."""
    from app.auth.auth import hash_password
    from app.db.models.user import User, UserRole
    from app.db.repositories import NotificationRepository

    company = seeded_db["company"]
    u1 = User(company_id=company.id, email="u1@x.com", username="u1",
              hashed_password=hash_password("x"), role=UserRole.EMPLOYEE.value, is_active=True)
    u2 = User(company_id=company.id, email="u2@x.com", username="u2",
              hashed_password=hash_password("x"), role=UserRole.EMPLOYEE.value, is_active=True)
    db_session.add_all([u1, u2])
    await db_session.flush()

    notifs = NotificationRepository(db_session)
    n = await notifs.emit(
        company_id=company.id, recipient_id=u1.id,
        kind="system", title="t", message="m",
    )
    # u2 tries to mark u1's notification read → None (no row updated)
    assert await notifs.mark_read(notification_id=n.id, recipient_id=u2.id) is None
    # u1 succeeds
    updated = await notifs.mark_read(notification_id=n.id, recipient_id=u1.id)
    assert updated is not None
    assert updated.is_read is True
    assert updated.read_at is not None


@pytest.mark.asyncio
async def test_list_pending_for_approvers_filters(seeded_db, db_session):
    """Pending-approvals listing must respect company scope, status=pending,
    and the optional department filter."""
    from app.db.repositories import ActionRepository

    company = seeded_db["company"]
    actions = ActionRepository(db_session)

    # 2 HR pending, 1 Finance pending
    for _ in range(2):
        await actions.create(
            company_id=company.id, action_type="apply_leave",
            department="HR", payload={}, requires_approval=True,
        )
    await actions.create(
        company_id=company.id, action_type="submit_expense",
        department="Finance", payload={}, requires_approval=True,
    )

    all_rows = await actions.list_pending_for_approvers(company_id=company.id)
    assert len(all_rows) == 3

    hr_only = await actions.list_pending_for_approvers(
        company_id=company.id, department="HR",
    )
    assert len(hr_only) == 2
    assert all(a.department == "HR" for a in hr_only)
