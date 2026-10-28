from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging

from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.loan_application import router as loan_application_router
from app.routers.loan_products import router as loan_products_router
from app.routers.payments import router as payments_router

logger = logging.getLogger(__name__)

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validate_error_handler(
    request: Request,
    exc: RequestValidationError
):
    errors = [
        {
            "field": ".".join(str(part) for part in error['loc']),
            "message": error['msg'],
            "type": error['type'],
        }
        for error in exc.errors()
    ]

    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": errors
        },
    )

@app.exception_handler(Exception)
async def unexpected_error_handler(
    request: Request,
    exc: Exception
):
    logger.exception(
        "Unhandled error while processing %s %s",
        request.method,
        request.url.path
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred"
        }
    )

app.include_router(auth_router, prefix='/auth', tags=['auth'])
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(loan_application_router)
app.include_router(loan_products_router)
app.include_router(payments_router)