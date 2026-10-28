import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext

from app.models import Installment, Loan
from app.services.eligibility import calculate_monthly_payment, calculate_exact_monthly_payment

CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def add_months(start_date: date, months: int) -> date:
    month_index = start_date.month - 1 + months

    year = start_date.year + month_index // 12
    month = month_index % 12 + 1

    day = min(
        start_date.day,
        calendar.monthrange(year, month)[1],
    )

    return date(year, month, day)


def generate_schedule(
    loan: Loan,
    start_date: date | None = None,
) -> list[Installment]:
    if loan.id is None:
        raise ValueError("Loan must be saved before generating its schedule")

    if loan.term_months <= 0:
        raise ValueError("Loan term must be greater than zero")

    if loan.principal_amount <= 0:
        raise ValueError("Loan principal must be greater than zero")

    if loan.interest_rate < 0:
        raise ValueError("Interest rate cannot be negative")

    start_date = start_date or date.today()

    monthly_payment = calculate_monthly_payment(
        amount=Decimal(loan.principal_amount),
        annual_interest_rate=Decimal(loan.interest_rate),
        term_months=loan.term_months,
    )

    # The rounded regular payment multiplied by the term is our
    # target total for this schedule.
    
    exact_payment = calculate_exact_monthly_payment(
        amount=Decimal(loan.principal_amount),
        annual_interest_rate=Decimal(loan.interest_rate),
        term_months=loan.term_months,
    )

    target_total = money(
        exact_payment * Decimal(loan.term_months)
    )



    installments = []
    amount_scheduled = Decimal("0.00")

    for number in range(1, loan.term_months + 1):
        if number == loan.term_months:
            # Correct any accumulated rounding difference.
            amount_due = money(target_total - amount_scheduled)
        else:
            amount_due = monthly_payment
            amount_scheduled += amount_due

        installments.append(
            Installment(
                loan_id=loan.id,
                installment_number=number,
                due_date=add_months(start_date, number),
                amount_due=amount_due,
                amount_paid=Decimal("0.00"),
                status="PENDING",
            )
        )

    return installments