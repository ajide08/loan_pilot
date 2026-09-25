from fastapi import FastAPI

from app.database import init_db
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router

app = FastAPI()


@app.on_event("startup")
def startup_event() -> None:
    init_db()


app.include_router(auth_router, prefix='/auth', tags=['auth'])
app.include_router(users_router)
app.include_router(admin_router)