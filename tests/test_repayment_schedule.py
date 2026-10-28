
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.services.repayment_schedule import (
    add_months,
    generate_schedule,
)



def make_loan(
    principal=Decimal("100000"),
    interest_rate=Decimal("12.00"),
    term_months=12,
):
    return SimpleNamespace(
        id=1,
        principal_amount=principal,
        interest_rate=interest_rate,
        term_months=term_months,
    )



def test_schedule_has_correct_number_of_installments():
    schedule = generate_schedule(
        make_loan(),
        start_date=date(2026, 1, 15),
    )

    assert len(schedule) == 12


def test_installment_numbers_are_sequential():
    schedule = generate_schedule(
        make_loan(),
        start_date=date(2026, 1, 15),
    )

    assert [item.installment_number for item in schedule] == list(
        range(1, 13)
    )


def test_due_dates_are_monthly():
    schedule = generate_schedule(
        make_loan(term_months=3),
        start_date=date(2026, 1, 15),
    )

    assert [item.due_date for item in schedule] == [
        date(2026, 2, 15),
        date(2026, 3, 15),
        date(2026, 4, 15),
    ]


def test_month_end_dates_are_valid():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2028, 1, 31), 1) == date(2028, 2, 29)


def test_installments_start_unpaid_and_pending():
    schedule = generate_schedule(
        make_loan(term_months=3),
        start_date=date(2026, 1, 15),
    )

    assert all(item.amount_paid == Decimal("0.00") for item in schedule)
    assert all(item.status == "PENDING" for item in schedule)


def test_final_installment_corrects_rounding():
    loan = make_loan(
        principal=Decimal("100000"),
        interest_rate=Decimal("12.00"),
        term_months=7,
    )

    schedule = generate_schedule(
        loan,
        start_date=date(2026, 1, 15),
    )

    assert len(schedule) == 7
    assert schedule[-1].amount_due > 0

    regular_amounts = [item.amount_due for item in schedule[:-1]]
    assert all(amount == regular_amounts[0] for amount in regular_amounts)


def test_zero_interest_schedule():
    schedule = generate_schedule(
        make_loan(
            principal=Decimal("1200"),
            interest_rate=Decimal("0"),
            term_months=12,
        ),
        start_date=date(2026, 1, 15),
    )

    assert sum(
        (item.amount_due for item in schedule),
        Decimal("0.00"),
    ) == Decimal("1200.00")
