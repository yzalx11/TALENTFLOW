import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

class Settings(BaseSettings):
    # 项目配置
    PROJECT_NAME: str = "TalentFlow-AI"
    API_V1_STR: str = "/api/v1"

    # 数据库配置 (MySQL)
    MYSQL_SERVER: str = os.getenv("MYSQL_SERVER", "localhost")
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "password")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "talentflow_db")

    # 向量数据库配置
    RAG_DB_DIR: str = os.getenv("RAG_DB_DIR", "./vector_db")

    PROJECT_ROOT: str = r"E:\project\talentflow-ai\talentflow-ai-backend"
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-change-in-prod")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_SERVER}/{self.MYSQL_DATABASE}"

settings = Settings()