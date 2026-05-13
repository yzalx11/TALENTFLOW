# app/utils/file_parser.py
import os
import shutil
import time
import pdfplumber
from docx import Document
from fastapi import UploadFile
from app.core.config import settings
from app.core.logger import logger
# 配置常量 ---
UPLOAD_DIR = settings.UPLOAD_DIR

# 确保上传目录存在 
os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_upload_file_to_disk(file: UploadFile) -> str:
    """
    负责将上传的文件保存到本地物理硬盘
    """
    # 直接使用常量目录，不再需要在函数里判断了
    safe_filename = f"{int(time.time())}_{file.filename}"
    file_location = os.path.join(UPLOAD_DIR, safe_filename)
    
    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return file_location
    except Exception as e:
        logger.error(f"❌ 文件落盘失败: {e}")
        return ""
    finally:
        file.file.seek(0)