from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core import database, security, config
from app.schemas import user_schema
from app.crud import crud

router = APIRouter(prefix="/api/v1/auth",tags=["授权认证"])


@router.post("/register", response_model=user_schema.UserOut, status_code=status.HTTP_201_CREATED)
def register(
    user_in: user_schema.UserCreate,
    db: Session = Depends(database.get_db)
):
    '''用户的注册接口'''
    #用户名是否已存在
    existing_user = crud.get_user_by_username(db, username=user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该用户名已被注册。"
        )
    
    #  CRUD 创建用户
    user = crud.create_user(db, user_in=user_in)
    return user

#登录接口
@router.post("/login", response_model=user_schema.LoginResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db)
):
    """
    OAuth2 兼容登录接口
    使用 Argon2 验证密码并返回 JWT Token
    """
    # 用户是否存在
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证
    if not security.verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # JWT Token
    access_token_expires = timedelta(minutes=config.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": str(user.username)}, 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }