# 负责database的增删改查操作设计
from typing import Optional
from app.models import user as user_model

#从SQLAlchemy导入session类型
from sqlalchemy.orm import Session as SQLASession

from app import schemas
from app.core import security #负责密码哈希


def get_user_by_username(db:SQLASession,username:str) -> Optional[user_model.User]:
    '''
    根据用户名查询用户
    用SQLAlchemy的query写法
    '''
    return db.query(user_model.User).filter(user_model.User.username == username).first()

def get_user_by_id(db: SQLASession, user_id: int) -> Optional[user_model.User]:
    """
    根据用户ID查询用户
    用SQLAlchemy的query写法
    """
    return db.query(user_model.User).filter(user_model.User.id == user_id).first()

def create_user(db:SQLASession,user_in:schemas.UserCreate) -> user_model.User:
    hashed_password = security.get_password_hash(user_in.password)
    db_user = user_model.User(
        username=user_in.username,
        password=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)  # 刷新对象，获取数据库生成的ID等字段
    return db_user


