from decimal import Decimal
from types import SimpleNamespace

from app.services.eligibility import assess_application


def make_product(**overrides):
    values = {
        "min_amount": Decimal("50000"),
        "max_amount": Decimal("1000000"),
        "max_term_months": 12,
        "interest_rate": Decimal("12.00"),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_application(**overrides):
    values = {
        "requested_amount": Decimal("500000"),
        "requested_term_months": 12,
        "monthly_income": Decimal("200000"),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_amount_below_minimum():
    result = assess_application(
        make_application(requested_amount=Decimal("20000")),
        make_product(),
    )

    assert result.eligible is False
    assert result.reason == "Requested amount is below the product minimum"


def test_amount_above_maximum():
    result = assess_application(
        make_application(requested_amount=Decimal("1200000")),
        make_product(),
    )

    assert result.eligible is False
    assert result.reason == "Requested amount exceeds the product maximum"


def test_term_above_maximum():
    result = assess_application(
        make_application(requested_term_months=18),
        make_product(),
    )

    assert result.eligible is False
    assert result.reason == "Requested term exceeds the product maximum"


def test_income_too_low():
    result = assess_application(
        make_application(monthly_income=Decimal("10000")),
        make_product(),
    )

    assert result.eligible is False
    assert result.reason == (
        "Monthly repayment exceeds the affordability limit"
    )


def test_valid_application():
    result = assess_application(
        make_application(),
        make_product(),
    )

    assert result.eligible is True
    assert result.reason is None


def test_minimum_amount_boundary():
    result = assess_application(
        make_application(requested_amount=Decimal("50000")),
        make_product(),
    )

    assert result.eligible is True
    assert result.reason is None


def test_maximum_amount_boundary():
    result = assess_application(
        make_application(requested_amount=Decimal("1000000")),
        make_product(),
    )

    assert result.eligible is False
    assert result.reason == (
        "Monthly repayment exceeds the affordability limit"
    )