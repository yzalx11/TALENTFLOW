from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.models import database
from app.schemas import user_schema
from app.crud import crud
from jose import JWTError, jwt
from app.core import security

# 创建一个路由
router = APIRouter()
oauth_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(
    user_in: schemas.UserCreate,
    db: Session = Depends(database.get_db)
):
    '''用户的注册接口'''
    
    user = crud.create_user(db, user_in=user_in, tenant_id=user_in.tenant_id)
    return user


@router.post("/login", response_model=user_schema.LoginResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db)
):
    """
    OAuth2 兼容登录接口
    返回: access_token, token_type, 以及用户完整信息
    """
    # 1. 查找用户 (支持用户名或邮箱登录)
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user: