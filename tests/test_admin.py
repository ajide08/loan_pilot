
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.models import (
    AuditLog,
    Installment,
    Loan,
    LoanApplication,
    LoanProduct,
    Repayment,
    User,
)
from app.security import create_access_token


def make_user(db_session, name, role):
    user = User(
        full_name=name,
        email=f"{name.lower().replace(' ', '.')}@example.com",
        password_hash="unused-test-hash",
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers(user):
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def make_product(db_session):
    product = LoanProduct(
        name="Test Product",
        interest_rate=Decimal("10.00"),
        min_amount=Decimal("100.00"),
        max_amount=Decimal("10000.00"),
        max_term_months=24,
        active=True,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


def make_application(db_session, borrower, product, status="PENDING"):
    application = LoanApplication(
        borrower_id=borrower.id,
        loan_product_id=product.id,
        requested_amount=Decimal("1000.00"),
        requested_term_months=12,
        monthly_income=Decimal("2000.00"),
        status=status,
    )
    db_session.add(application)
    db_session.commit()
    db_session.refresh(application)
    return application


def make_loan(
    db_session,
    borrower,
    product,
    application,
    status="ACTIVE",
    balance="1000.00",
):
    loan = Loan(
        application_id=application.id,
        borrower_id=borrower.id,
        loan_product_id=product.id,
        principal_amount=Decimal("1000.00"),
        interest_rate=Decimal("10.00"),
        term_months=12,
        outstanding_balance=Decimal(balance),
        status=status,
    )
    db_session.add(loan)
    db_session.commit()
    db_session.refresh(loan)
    return loan


def test_borrower_cannot_view_admin_reports(client, db_session):
    borrower = make_user(db_session, "Report Borrower", "BORROWER")

    for path in (
        "/admin/reports/loans",
        "/admin/reports/repayments",
        "/admin/reports/applications",
        "/admin/audit-logs",
    ):
        response = client.get(path, headers=auth_headers(borrower))
        assert response.status_code == 403, path


def test_loan_report_returns_totals_and_status_counts(client, db_session):
    admin = make_user(db_session, "Loan Report Admin", "SYSTEM_ADMIN")
    borrower = make_user(db_session, "Loan Report Borrower", "BORROWER")
    product = make_product(db_session)

    active_app = make_application(db_session, borrower, product, "APPROVED")
    overdue_app = make_application(
        db_session,
        borrower,
        product,
        "APPROVED",
    )
    paid_app = make_application(db_session, borrower, product, "APPROVED")

    make_loan(
        db_session, borrower, product, active_app,
        status="ACTIVE", balance="500.00",
    )
    make_loan(
        db_session, borrower, product, overdue_app,
        status="OVERDUE", balance="300.00",
    )
    make_loan(
        db_session, borrower, product, paid_app,
        status="PAID", balance="0.00",
    )

    response = client.get(
        "/admin/reports/loans",
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_loans"] == 3
    assert Decimal(data["total_outstanding_balance"]) == Decimal("800.00")
    assert data["loans_by_status"] == {
        "ACTIVE": 1,
        "OVERDUE": 1,
        "PAID": 1,
        "DEFAULTED": 0,
    }


def test_finance_admin_can_view_loan_report(client, db_session):
    finance_admin = make_user(
        db_session, "Finance Report Admin", "FINANCE_ADMIN"
    )

    response = client.get(
        "/admin/reports/loans",
        headers=auth_headers(finance_admin),
    )

    assert response.status_code == 200
    assert response.json()["total_loans"] == 0


def test_repayment_report_counts_statuses_and_collected_amount(
    client, db_session
):
    admin = make_user(db_session, "Repayment Report Admin", "SYSTEM_ADMIN")
    borrower = make_user(
        db_session, "Repayment Report Borrower", "BORROWER"
    )
    product = make_product(db_session)
    application = make_application(db_session, borrower, product, "APPROVED")
    loan = make_loan(db_session, borrower, product, application)

    db_session.add_all([
        Repayment(
            loan_id=loan.id,
            amount=Decimal("100.00"),
            status="SUCCESS",
            reference="report-success-1",
        ),
        Repayment(
            loan_id=loan.id,
            amount=Decimal("50.00"),
            status="SUCCESS",
            reference="report-success-2",
        ),
        Repayment(
            loan_id=loan.id,
            amount=Decimal("25.00"),
            status="PENDING",
            reference="report-pending-1",
        ),
        Repayment(
            loan_id=loan.id,
            amount=Decimal("10.00"),
            status="FAILED",
            reference="report-failed-1",
        ),
    ])
    db_session.commit()

    response = client.get(
        "/admin/reports/repayments",
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_payments"] == 4
    assert data["successful_payments"] == 2
    assert data["pending_payments"] == 1
    assert data["failed_payments"] == 1
    assert Decimal(data["total_collected"]) == Decimal("150.00")


def test_application_report_counts_statuses(client, db_session):
    officer = make_user(
        db_session, "Application Report Officer", "LENDING_OFFICER"
    )
    borrower = make_user(
        db_session, "Application Report Borrower", "BORROWER"
    )
    product = make_product(db_session)

    make_application(db_session, borrower, product, "PENDING")
    make_application(db_session, borrower, product, "APPROVED")
    make_application(db_session, borrower, product, "REJECTED")

    response = client.get(
        "/admin/reports/applications",
        headers=auth_headers(officer),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_applications"] == 3
    assert data["applications_by_status"] == {
        "PENDING": 1,
        "APPROVED": 1,
        "REJECTED": 1,
    }


def test_audit_log_filters_and_pagination(client, db_session):
    admin = make_user(db_session, "Audit Log Admin", "SYSTEM_ADMIN")

    db_session.add_all([
        AuditLog(
            actor_user_id=admin.id,
            action="PAYMENT_RECORDED",
            resource_type="REPAYMENT",
            resource_id=10,
            details={"amount": "100.00"},
        ),
        AuditLog(
            actor_user_id=admin.id,
            action="LOAN_APPROVED",
            resource_type="LOAN",
            resource_id=20,
            details={},
        ),
        AuditLog(
            actor_user_id=admin.id,
            action="PAYMENT_RECORDED",
            resource_type="REPAYMENT",
            resource_id=11,
            details={"amount": "50.00"},
        ),
    ])
    db_session.commit()

    response = client.get(
        "/admin/audit-logs",
        params={
            "action": "PAYMENT_RECORDED",
            "resource_type": "REPAYMENT",
            "limit": 1,
            "offset": 0,
        },
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["limit"] == 1
    assert data["offset"] == 0
    assert data["items"][0]["action"] == "PAYMENT_RECORDED"
    assert data["items"][0]["resource_type"] == "REPAYMENT"


def test_audit_log_rejects_invalid_pagination(client, db_session):
    admin = make_user(db_session, "Audit Pagination Admin", "SYSTEM_ADMIN")

    response = client.get(
        "/admin/audit-logs?limit=101",
        headers=auth_headers(admin),
    )

    assert response.status_code == 422


def test_borrower_cannot_process_overdue_installments(client, db_session):
    borrower = make_user(db_session, "Overdue Borrower", "BORROWER")

    response = client.post(
        "/admin/overdue/process",
        headers=auth_headers(borrower),
    )

    assert response.status_code == 403


def test_system_admin_can_process_overdue_installments(client, db_session):
    admin = make_user(db_session, "Overdue System Admin", "SYSTEM_ADMIN")

    response = client.post(
        "/admin/overdue/process",
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    assert response.json() == {
        "installments_marked_overdue": 0,
        "loans_marked_overdue": 0,
        "loans_reactivated": 0,
    }
    assert db_session.query(AuditLog).filter_by(
        action="OVERDUE_PROCESSING_COMPLETED"
    ).count() == 1
