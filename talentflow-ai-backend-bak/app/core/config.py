# app/core/config.py
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
load_dotenv()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
class Settings(BaseSettings):
    # 项目配置
    PROJECT_NAME: str = "TalentFlow-AI"
    API_V1_STR: str = "/api/v1"
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "data", "uploads", "jobs")
    VECTOR_DB_PATH: str = os.path.join(BASE_DIR, "data", "faiss_db")
    
    # MySQL
    MYSQL_SERVER: str = os.getenv("MYSQL_SERVER", "localhost")
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "password")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "talentflow_db")

    #LLM
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE")

    PROJECT_ROOT: str = r"D:\py_lesson\talentflow-ai>\talentflow-ai-backend-bak"
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-change-in-prod")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_SERVER}/{self.MYSQL_DATABASE}"

settings = Settings()