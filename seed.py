from decimal import Decimal
from sqlalchemy import select
from app.database import sessionLocal
from app.models import User, LoanProduct
from app.security import hash_password


DEMO_USERS = [
    {
        "email": "borrower@loanpilot.demo",
        "full_name": "Demo Borrower",
        "password": "BorrowerDemo123!",
        "role": "BORROWER",
    },
    {
        "email": "officer@loanpilot.demo",
        "full_name": "Demo Lending Officer",
        "password": "OfficerDemo123!",
        "role": "LENDING_OFFICER",
    },
    {
        "email": "admin@loanpilot.demo",
        "full_name": "Demo Administrator",
        "password": "AdminDemo123!",
        "role": "SYSTEM_ADMIN",
    },
]

DEMO_PRODUCTS = [
    {
        "name": "Personal Starter Loan",
        "interest_rate": Decimal("12.00"),
        "min_amount": Decimal("50000.00"),
        "max_amount": Decimal("500000.00"),
        "max_term_months": 12,
    },
    {
        "name": "Business Growth Loan",
        "interest_rate": Decimal("15.00"),
        "min_amount": Decimal("200000.00"),
        "max_amount": Decimal("5000000.00"),
        "max_term_months": 24,
    },
]


def seed_data() -> None:
    db = sessionLocal()

    try:
        for user_data in DEMO_USERS:
            existing_user = db.scalar(
                select(User).where(User.email == user_data["email"])
            )

            if existing_user:
                print(f"User already exists: {user_data['email']}")
                continue

            user = User(
                email=user_data["email"],
                full_name=user_data["full_name"],
                password_hash=hash_password(user_data["password"]),
                role=user_data["role"],
                is_active=True,
            )
            db.add(user)
            print(f"Added user: {user_data['email']}")

        for product_data in DEMO_PRODUCTS:
            existing_product = db.scalar(
                select(LoanProduct).where(
                    LoanProduct.name == product_data["name"]
                )
            )

            if existing_product:
                print(f"Product already exists: {product_data['name']}")
                continue

            product = LoanProduct(**product_data, active=True)
            db.add(product)
            print(f"Added product: {product_data['name']}")

        db.commit()
        print("LoanPilot seed data completed successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
