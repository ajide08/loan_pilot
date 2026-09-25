from fastapi import APIRouter, Depends

from app.dependencies import require_role
from app.models import User

router = APIRouter(prefix='/admin', tags=['Admin'])

@router.get('/test')
def admin_test(current_user: User = Depends(require_role('SYSTEM_ADMIN'))):
    return {"msg":"Admin access granted", "user":current_user.full_name}