# app/models/base.py
from sqlalchemy.orm import declarative_base

# 创建所有数据库模型都必须继承的基类
Base = declarative_base()