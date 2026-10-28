from app.database import Base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey
from datetime import datetime
from sqlalchemy import JSON

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(225), unique=True, nullable=False)
    password_hash = Column(String(225), nullable=False)
    full_name = Column(String(225), unique=True,  nullable=False)
    role = Column(String(50), nullable=False, default='BORROWER')
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class LoanProduct(Base):
    __tablename__ = 'loan_products'
    id = Column(Integer, primary_key=True)
    name = Column(String(225), unique=True, nullable=False)
    interest_rate = Column(Numeric(5, 2), nullable=False)
    min_amount = Column(Numeric(12, 2), nullable=False)
    max_amount = Column(Numeric(12, 2), nullable=False)
    max_term_months = Column(Integer, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class LoanApplication(Base):
    __tablename__ = 'loan_applications'
    id = Column(Integer, primary_key=True)
    borrower_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    loan_product_id = Column(Integer, ForeignKey('loan_products.id'), nullable=False)
    requested_amount = Column(Numeric(12, 2), nullable=False)
    requested_term_months = Column(Integer, nullable=False)
    monthly_income = Column(Numeric(12, 2), nullable=False)
    status = Column(String(50), default='PENDING', nullable=False)
    rejection_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Loan(Base):
    __tablename__ = 'loans'
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey('loan_applications.id'), nullable=False, unique=True)
    borrower_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    loan_product_id = Column(Integer, ForeignKey('loan_products.id'), nullable=False)
    principal_amount = Column(Numeric(12, 2), nullable=False)
    interest_rate = Column(Numeric(5, 2), nullable=False)
    term_months = Column(Integer, nullable=False)
    outstanding_balance = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), nullable=False, default='ACTIVE')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Installment(Base):
    __tablename__ = 'installments'
    id = Column(Integer, primary_key=True)
    loan_id = Column(Integer, ForeignKey('loans.id'), nullable=False)
    installment_number = Column(Integer, nullable=False)
    due_date = Column(DateTime, nullable=False)
    amount_due = Column(Numeric(12, 2), nullable=False)
    amount_paid = Column(Numeric(12, 2), nullable=False, default=0)
    status = Column(String(20), nullable=False, default='PENDING')


class Repayment(Base):
    __tablename__ = 'repayments'
    id = Column(Integer, primary_key=True)
    loan_id = Column(Integer, ForeignKey('loans.id'), nullable=False)
    amount = Column(Numeric(12,2), nullable=False)
    status = Column(String(20), nullable=False, default='PENDING')
    reference = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    idempotency_key = Column(String(100), unique=True, nullable=True)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    actor_user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(Integer, nullable=False, index=True)

    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

