from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.services.overdue import process_overdue_installments
from app.models import AuditLog
from app.dependencies import require_role
from app.models import User, Loan, Repayment, LoanApplication

from decimal import Decimal

router = APIRouter(prefix='/admin', tags=['Admin'])

@router.get('/test')
def admin_test(current_user: User = Depends(require_role('SYSTEM_ADMIN'))):
    return {"msg":"Admin access granted", "user":current_user.full_name}


@router.post('/overdue/process')
def process_overdue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    role = current_user.role.strip().upper().replace(" ", "_")

    if role != 'SYSTEM_ADMIN':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only system administrators can process overdue loans'
        )
    return process_overdue_installments(
        db,
        actor_user_id=current_user.id
    )

@router.get('/audit-logs')
def get_audit_logs(
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    role = current_user.role.strip().upper().replace(" ", "_")

    if role != 'SYSTEM_ADMIN':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admin can view audit logs"

        )

    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)

    if resource_type:
        query = query.filter(
            AuditLog.resource_type == resource_type
        )

    if resource_id:
        query = query.filter(
            AuditLog.resource_id == resource_id
        )

    logs = (
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset(offset).limit(limit).all()
    )

    return {
        "count": len(logs),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": log.id,
                "actor_user_id": log.actor_user_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "created_at": log.created_at
            }
            for log in logs
        ]
    }


@router.get('/reports/loans')
def get_loan_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    role = current_user.role.strip().upper().replace(" ", "_")

    if role not in {"SYSTEM_ADMIN", "FINANCE_ADMIN"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You are not authorized to view loan reports'
        )

    total_loans = db.query(func.count(Loan.id)).scalar() or 0

    total_outstanding = (db.query(
        func.sum(Loan.outstanding_balance))
        .filter(Loan.status.in_(['ACTIVE', 'OVERDUE'])).scalar() or Decimal('0.00')
    )

    loan_by_status = (
        db.query(Loan.status, func.count(Loan.id))
        .group_by(Loan.status)
        .all()
    )

    status_counts = {
        loan_status: count for loan_status, count in loan_by_status
    }

    return {
        "total_loans": total_loans,
        "total_outstanding_balance": str(total_outstanding),
        "loans_by_status": {
            "ACTIVE": status_counts.get('ACTIVE', 0),
            "OVERDUE": status_counts.get('OVERDUE', 0),
            "PAID": status_counts.get('PAID', 0),
            "DEFAULTED": status_counts.get('DEFAULTED', 0)
        }
    }


@router.get('/reports/repayments')
def get_repayment_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    role = current_user.role.strip().upper().replace(" ", "_")

    if role not in {"SYSTEM_ADMIN", "FINANCE_ADMIN"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You are not authorized to view repayment reports'
        )

    total_payments = (
        db.query(func.count(Repayment.id)).scalar() or 0
    )

    successful_payments = (
        db.query(func.count(Repayment.id))
        .filter(Repayment.status == "SUCCESS")
        .scalar() or 0
    )

    pending_payments = (
        db.query(func.count(Repayment.id))
        .filter(Repayment.status == "PENDING")
        .scalar() or 0
    )

    failed_payments = (
        db.query(func.count(Repayment.id))
        .filter(Repayment.status == "FAILED")
        .scalar() or 0
    )

    total_collected = (
        db.query(func.sum(Repayment.amount))
        .filter(Repayment.status == "SUCCESS")
        .scalar() or Decimal("0.00")
    )

    return {
        "total_payments": total_payments,
        "successful_payments": successful_payments,
        "pending_payments": pending_payments,
        "failed_payments": failed_payments,
        "total_collected": str(total_collected)
    }

@router.get('/reports/applications')
def get_application_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    role = current_user.role.strip().upper().replace(" ", "_")
    if  role not in {"SYSTEM_ADMIN", "FINANCE_ADMIN", "LENDING_OFFICER"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view application reports"
        )

    total_applications = (db.query(func.count(LoanApplication.id)).scalar() or 0)
    applications_by_status = (db.query(LoanApplication.status, func.count(LoanApplication.id),)
    .group_by(LoanApplication.status).all())

    status_counts = {
        application_status: count for application_status, count in applications_by_status
    }

    return {
        "total_applications": total_applications,
        "applications_by_status": {
            "PENDING": status_counts.get("PENDING", 0),
            "APPROVED": status_counts.get("APPROVED", 0),
            "REJECTED": status_counts.get("REJECTED", 0)
        }
    }