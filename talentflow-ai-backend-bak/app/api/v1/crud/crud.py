# 负责database的增删改查操作设计
from typing import Optional
from app.models import user as user_model

#从SQLAlchemy导入session类型
from sqlalchemy.orm import Session as SQLASession
from sqlalchemy.orm import Session

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

def create_user(db:SQLASession,user_in:schemas.UserCreate,tenant_id:int) -> user_model.User:
    hashed_password = security.get_password_hash(user_in.password)
    db_user = user_model.User(
        username=user_in.username,
        password=hashed_password,
        tenant_id=tenant_id,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)  # 刷新对象，获取数据库生成的ID等字段
    return db_user


def get_user_sessions(db: Session, tenant_id: int, user_id: int = None, limit: int = 100):
    """获取会话列表，严格限制在当前 tenant_id 下"""
    query = db.query(user_model.ChatSessionDB).filter(user_model.ChatSessionDB.tenant_id == tenant_id)
    if user_id:
        query = query.filter(user_model.ChatSessionDB.user_id == user_id)
    return query.order_by(user_model.ChatSessionDB.created_at.desc()).limit(limit).all()

def get_chat_messages(db: Session, session_id: int):
    """获取某个会话的所有消息"""
    return db.query(user_model.ChatMessageDB).filter(
        user_model.ChatMessageDB.session_id == session_id
    ).order_by(user_model.ChatMessageDB.created_at.asc()).all()

def get_session_by_id(db: Session, session_id: int,user_id:str):
    """根据会话ID获取会话详情"""
    return db.query(user_model.ChatSessionDB)\
        .filter(user_model.ChatSessionDB.id == session_id,
                user_model.ChatSessionDB.user_id == user_id,)\
                .first()

def create_chat_session(db: Session, user_id: int, tenant_id: int, title: str):
    """创建新会话"""
    db_session = user_model.ChatSessionDB(user_id=user_id, tenant_id=tenant_id, title=title)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def create_chat_message(db: Session, session_id: int, role: str, content: str):
    """保存单条聊天记录"""
    db_msg = user_model.ChatMessageDB(session_id=session_id, role=role, content=content)
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)
    return db_msg

def delete_chat_session(db: Session, session_id: int):
    """删除指定的会话"""
    db_session = db.query(user_model.ChatSessionDB).filter(user_model.ChatSessionDB.id == session_id).first()
    if db_session:
        db.delete(db_session)
        db.commit()
        return True
    return False