from app.models import AuditLog
from sqlalchemy.orm import Session

def log_action(
    db: Session,
    actor_user_id: int | None,
    action: str,
    resource_type: str,
    resource_id: int,
    details: dict | None = None
) -> AuditLog:
    """Add audit event to database."""
    audit_log = AuditLog(
        actor_user_id = actor_user_id,
        action = action,
        resource_type = resource_type,
        resource_id = resource_id,
        details = details or {}
    )
    db.add(audit_log)
    return audit_log