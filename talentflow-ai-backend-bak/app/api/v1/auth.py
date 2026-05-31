from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from app.core import security, config, database
from app.schemas import user_schema
from app.crud import crud

router = APIRouter(prefix="/api/v1/auth", tags=["授权认证"])


# ---- 用户注册 ----
@router.post("/register", response_model=user_schema.UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: user_schema.UserCreate,
    db: AsyncSession = Depends(database.get_db),
):
    existing_user = await crud.get_user_by_username(db, username=user_in.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="该用户名已被注册。")
    user = await crud.create_user(db, user_in=user_in)
    return user


# ---- 登录获取 Token ----
@router.post("/login", response_model=user_schema.LoginResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(database.get_db),
):
    user = await crud.get_user_by_username(db, username=form_data.username)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误",
                            headers={"WWW-Authenticate": "Bearer"})

    if not security.verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误",
                            headers={"WWW-Authenticate": "Bearer"})

    access_token_expires = timedelta(minutes=config.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": str(user.username)},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user": user}
