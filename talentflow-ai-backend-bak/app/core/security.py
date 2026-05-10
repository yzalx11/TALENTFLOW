from datetime import datetime,timedelta,timezone
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings
from app.core.logger import logger
import bcrypt
# 配置 passlib 使用 bcrypt 算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str)->bool:
    """
    用户登录时，验证其输入的明文密码，与数据库中取出的哈希密码是否匹配。
    返回值:True (密码正确) / False (密码错误)
    """

    try:
        # bcrypt 原生库要求输入必须是 bytes 类型
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"❌ [系统故障] 密码底层校验异常: {str(e)}", exc_info=True)
        return False


def get_password_hash(password:str)->str:
    """
    将用户输入的明文密码进行 Bcrypt 哈希加密。
    存入数据库的一定是这个函数的返回值。
    """
    #用bcrypt将明文密码转换为哈希字符串
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

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