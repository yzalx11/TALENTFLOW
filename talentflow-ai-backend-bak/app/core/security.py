from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings
from app.core.logger import logger

# 配置 passlib 使用 argon2 算法
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    用户登录时，验证其输入的明文密码，与数据库中取出的哈希密码是否匹配。
    返回值:True (密码正确) / False (密码错误)
    """
    try:
        # 使用 passlib 的 verify 方法，它会自动识别哈希类型并进行比对
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"❌ [系统故障] 密码底层校验异常: {str(e)}", exc_info=True)
        return False


def get_password_hash(password: str) -> str:
    """
    将用户输入的明文密码进行 Argon2 哈希加密。
    存入数据库的一定是这个函数的返回值。
    """
    # 使用 passlib 的 hash 方法，它会自动生成安全的盐值 (salt) 并进行 Argon2 加密
    return pwd_context.hash(password)


def create_access_token(
    data: dict, 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    根据用户信息(通常是 user_id 或 username)生成 JWT 访问令牌
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    # 调用 jose.jwt 进行签名生成 Token 字符串
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt