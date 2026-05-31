from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.core import security, database
from app.models import user

oauth_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(database.get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证或登录已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.settings.SECRET_KEY, algorithms=[security.settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    user_obj = await crud.get_user_by_username(db, username=username)
    if user_obj is None:
        raise credentials_exception
    return user_obj


async def get_current_active_admin(current_user: user.User = Depends(get_current_user)):
    if current_user.role != 1:
        raise HTTPException(status_code=403, detail="权限不足：仅管理员可操作")
    return current_user
