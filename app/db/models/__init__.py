# Import order matters here — models with no FKs first, dependents after.
# Alembic's autogenerate scans Base.metadata, which only contains models
# that have been imported. Importing them all here guarantees a complete
# schema is reflected in every migration run.

from app.db.models.company import Company, CompanyPlan  # noqa: F401
from app.db.models.user import User, UserRole  # noqa: F401
from app.db.models.conversation import Conversation, Message  # noqa: F401
from app.db.models.workflow_log import WorkflowLog  # noqa: F401
from app.db.models.action import Action, ActionType, ActionStatus  # noqa: F401
from app.db.models.feedback import Feedback  # noqa: F401
from app.db.models.audit_log import AuditLog, AuditEventType  # noqa: F401
from app.db.models.notification import Notification, NotificationKind  # noqa: F401
from app.db.models.action_comment import ActionComment  # noqa: F401

__all__ = [
    "Company",
    "CompanyPlan",
    "User",
    "UserRole",
    "Conversation",
    "Message",
    "WorkflowLog",
    "Action",
    "ActionType",
    "ActionStatus",
    "Feedback",
    "AuditLog",
    "AuditEventType",
    "Notification",
    "NotificationKind",
    "ActionComment",
]
