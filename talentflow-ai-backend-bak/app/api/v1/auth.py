from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.models import database
from app import schemas, crud
from jose import JWTError, jwt
from app.core import security

# 创建一个路由
router = APIRouter()
oauth_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.get("/tenants", response_model=List[schemas.TenantOut])
def read_tenants(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db)
):
    '''获取公司(租户)列表接口'''
    tenants = crud.get_tenants(db, skip=skip, limit=limit)
    return tenants


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(
    user_in: schemas.UserCreate,
    db: Session = Depends(database.get_db)
):
    '''用户的注册接口'''
    user = crud.get_user_by_username(db, username=user_in.username)
    if user:
        raise HTTPException(status_code=400, detail="用户名已经存在")
        
    if not user_in.tenant_id:
        raise HTTPException(status_code=400, detail="必须选择归属的公司")
    
    user = crud.create_user(db, user_in=user_in, tenant_id=user_in.tenant_id)
    return user

@router.post("/login",response_model=schemas.LoginResponse, status_code=status.HTTP_201_CREATED)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db)
):
    """用户登录接口：验证账号密码，验证成功后颁发 JWT 访问令牌"""
    user = crud.get_user_by_username(db, username=form_data.username)
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="用户名或密码错误",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not user:
        raise credentials_exception
        
    if not security.verify_password(form_data.password, user.password):
        raise credentials_exception
        
    access_token = security.create_access_token(
        data={"sub": user.username}
    )
    
    # 这里默认传 0 给前端
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "role": getattr(user, 'role', 0), 
            "tenant_id": user.tenant_id,
            "created_at": user.created_at
        }
    }