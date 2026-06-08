# app/core/config.py
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
load_dotenv()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    PROJECT_NAME: str = "TalentFlow-AI"
    API_V1_STR: str = "/api/v1"
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "data", "uploads", "jobs")
    VECTOR_DB_PATH: str = os.path.join(BASE_DIR, "data", "faiss_db")
    
    # MySQL
    MYSQL_SERVER: str = "localhost"
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "password"
    MYSQL_DATABASE: str = "talentflow_db"

    # LLM
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = ""

    # 模型路径
    EMBEDDING_MODEL_PATH: str = "/app/data/models/text2vec-base-chinese"
    RERANKER_MODEL_PATH: str = "/app/data/models/bge-reranker-v2-m3"
    MODELS_BASE_DIR: str = "/app/data/models"

    PROJECT_ROOT: str = r"D:\py_lesson\talentflow-ai>\talentflow-ai-backend-bak"
    # 安全配置
    SECRET_KEY: str = "super-secret-key-change-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_SERVER}/{self.MYSQL_DATABASE}"

settings = Settings()