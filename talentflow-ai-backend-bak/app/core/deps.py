from app import schemas, crud
from app.core import security
from app.core import database
from app.models import user,task

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from jose import JWTError, jwt

from sqlalchemy.orm import Session

from typing import List
# 创建一个路由
router = APIRouter()

oauth_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# 通过 depends 从请求头自动获取 token 并解析出当前用户
async def get_current_user(
    token: str = Depends(oauth_scheme),
    db: Session = Depends(database.get_db)
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
    except Exception as e:
        raise credentials_exception
    
    # 使用统一的 username 变量进行查询
    user = crud.get_user_by_username(db, username=username)
    
    if user is None:
        raise credentials_exception
    return user

def get_current_active_admin(current_user: user.User = Depends(get_current_user)):
    if current_user.role != 1:
        raise HTTPException(status_code=403, detail="权限不足：仅管理员可操作")
    return current_user


