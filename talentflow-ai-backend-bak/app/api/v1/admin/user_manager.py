# app/api/v1/admin/user_manager.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from app.models.user import User  # 注意这里：统一从 user.py 导入
from app.core.database import get_db
from app.core.security import get_password_hash  
from app.core.deps import get_current_active_admin

# from app.schemas.user_schema import UserRead 

router = APIRouter(prefix="/api/v1/admin", tags=["Admin-User-Manager"])

@router.get("/users")
def read_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = Query(None, description="搜索用户名或姓名")
):
    """
    管理员接口：获取用户列表，支持分页和关键字模糊搜索 (SQLAlchemy 版本)
    """
    query = db.query(User)
    
    if keyword:
        query = query.filter(
            or_(
                User.username.like(f"%{keyword}%"),
                User.full_name.like(f"%{keyword}%")
            )
        )
        
    # 分页并执行查询
    users = query.offset(skip).limit(limit).all()
    return users


@router.put("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    is_active: bool = Query(..., description="目标状态: True正常, False封禁"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """
    管理员接口：修改用户状态
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="该用户不存在")
    
    if user.id == current_user.id and not is_active:
        raise HTTPException(status_code=400, detail="不能封禁当前登录的管理员账号")
        
    user.is_active = is_active
    db.commit()
    
    status_msg = "已解封" if is_active else "已封禁"
    return {"message": f"用户 {user.username} {status_msg}"}


@router.put("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    new_password: str = Query(..., description="新密码", min_length=6),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """
    管理员接口：重置指定用户的密码
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="该用户不存在")
        
    hashed_password = get_password_hash(new_password)
    user.password = hashed_password
    
    db.commit()
    return {"message": f"用户 {user.username} 的密码已成功重置"}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """
    管理员接口：删除指定用户
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="该用户不存在")
        
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录的管理员账号")
        
    db.delete(user)
    db.commit()
    
    return {"message": f"用户 {user.username} 已被成功删除"}