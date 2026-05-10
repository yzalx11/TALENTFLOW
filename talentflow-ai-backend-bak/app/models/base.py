from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from typing import List, Optional
from app.models.user import User
from app.core.database import get_db
from app.core.security import get_password_hash
from app.core.deps import get_current_active_admin 

from app.schemas.user_profile_schema import UserRead

router = APIRouter(prefix="/api/v1/admin", tags=["Admin-User-Manager"])




@router.get("/users", response_model=List[User])
def read_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = Query(None, description="搜索用户名或姓名")
):

def reset_user_password():
    
    
def delete_user(
    user_id:int,
    db:Session = Depends(get_db)
    current_user:User = Depends(get_current_active_admin)
):
    