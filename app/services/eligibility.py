from dataclasses import dataclass
from decimal import Decimal
from math import pow
from decimal import Decimal, ROUND_HALF_UP, localcontext


@dataclass
class EligibilityResult:
    eligible: bool
    reason: str | None = None

CENT = Decimal("0.01")

def money(value: Decimal) -> Decimal:
    """Round a monetary value to two decimal places."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_exact_monthly_payment(
    amount: Decimal,
    annual_interest_rate: Decimal,
    term_months: int,
) -> Decimal:
    if amount <= 0 or term_months <= 0:
        raise ValueError("Amount and term must be greater than zero")
    if annual_interest_rate < 0:
        raise ValueError("Interest rate cannot be negative")

    with localcontext() as context:
        context.prec = 28

        principal = Decimal(amount)
        monthly_rate = (
            Decimal(annual_interest_rate)
            / Decimal("100")
            / Decimal("12")
        )

        if monthly_rate == 0:
            return principal / Decimal(term_months)

        return (
            principal
            * monthly_rate
            / (
                Decimal("1")
                - (Decimal("1") + monthly_rate) ** (-term_months)
            )
        )


def calculate_monthly_payment(
    amount: Decimal,
    annual_interest_rate: Decimal,
    term_months: int,
) -> Decimal:
    return money(
        calculate_exact_monthly_payment(
            amount,
            annual_interest_rate,
            term_months,
        )
    )


def assess_application(application, product) -> EligibilityResult:
    if application.requested_amount < product.min_amount: 
        return EligibilityResult(
            eligible=False,
            reason="Requested amount is below the product minimum"
        )

    if application.requested_amount > product.max_amount:
        return EligibilityResult(
            eligible=False,
            reason="Requested amount exceeds the product maximum"
        )

    if application.requested_term_months > product.max_term_months:
        return EligibilityResult(
            eligible=False,
            reason="Requested term exceeds the product maximum"
        )

    monthly_payment = calculate_monthly_payment(
        amount=application.requested_amount, 
        annual_interest_rate=product.interest_rate,
        term_months=application.requested_term_months,
    )

    maximum_affordable_payment = application.monthly_income * Decimal('0.30')

    if monthly_payment > maximum_affordable_payment:
        return EligibilityResult(
            eligible=False,
            reason='Monthly repayment exceeds the affordability limit'
        )

    return EligibilityResult(eligible=True)