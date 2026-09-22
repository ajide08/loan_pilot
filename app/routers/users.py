from fastapi import APIRouter, Depends

from ..dependencies import get_current_user
from ..models import User
from ..schemas import UserOutput


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get("/me", response_model=UserOutput)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user