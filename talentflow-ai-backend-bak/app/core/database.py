import os
from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
# 加载环境变量
load_dotenv()

# 确保项目根目录下存在 data 目录（通常用于存放 SQLite 文件或上传的文件）
os.makedirs("./data", exist_ok=True)


connect_args = {"check_same_thread": False}


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:123456@localhost:3306/dandelion_tribe?charset=utf8mb4"
)

# 创建数据库引擎
engine = create_engine(DATABASE_URL, echo=False)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)


def create_db_and_tables():
    """
    初始化数据库表结构
    必须在应用启动时调用，确保模型被注册并创建对应的表
    """
    from app import models

    # 根据导入的模型定义，在数据库中创建所有表（如果表不存在）
    SQLModel.metadata.create_all(engine)
    print("数据库表已检查/创建完成")


def get_db():
    """
    FastAPI 依赖注入: 获取数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session():
    """
    直接获取数据库会话（非依赖注入场景使用）
    """
    with Session(engine) as session:
        yield session