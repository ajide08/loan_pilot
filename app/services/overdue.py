from datetime import date
from sqlalchemy.orm import Session
from app.models import Installment, Loan
from app.services.audit import log_action


def process_overdue_installments(
    db: Session,
    today: date | None = None,
    actor_user_id: int | None = None
    ) -> dict[str, int]:
    today = today or date.today()

    try:
        loans = db.query(Loan).filter(Loan.status.in_(['ACTIVE', 'OVERDUE'])).all()
        installments_marked_overdue = 0
        loans_marked_overdue = 0
        loans_reactivated = 0

        for loan in loans:
        # If the loan is fully paid, don't mark its installments overdue.
            if loan.outstanding_balance <= 0:
                loan.status = "PAID"
                continue

            installments = db.query(Installment).filter(
                Installment.loan_id == loan.id
            ).all()
            for installment in installments:
                if (
                    installment.due_date.date() < today
                    and installment.status in {"PENDING", "PARTIAL"}
                ):
                    installment.status = 'OVERDUE'
                    installments_marked_overdue += 1
            has_overdue_installment = any(installment.status == 'OVERDUE' for installment in installments)


            if has_overdue_installment and loan.status == 'ACTIVE':
                loan.status = 'OVERDUE'
                loans_marked_overdue += 1

            elif not has_overdue_installment and loan.status == 'OVERDUE':
                loan.status = 'ACTIVE'
                loans_reactivated += 1

        log_action(
            db, 
            actor_user_id=actor_user_id,
            action='OVERDUE_PROCESSING_COMPLETED',
            resource_type='OVERDUE_PROCESSING',
            resource_id=0,
            details={
                "processed_on": str(today),
                "installments_marked_overdue": installments_marked_overdue,
                "loans_marked_overdue": loans_marked_overdue,
                "loans_reactivated": loans_reactivated
            }
        )
        db.commit()

        return {
            'installments_marked_overdue': installments_marked_overdue,
            'loans_marked_overdue': loans_marked_overdue,
            'loans_reactivated': loans_reactivated
        }

    except Exception:
        db.rollback()
        raise