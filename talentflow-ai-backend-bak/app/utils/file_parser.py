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
        
def extract_text_from_local_file(file_location: str, fallback_text: str = "") -> str:
    """
    读取本地文件并解析文本（融合了高级表格解析能力）
    """
    if not file_location or not os.path.exists(file_location):
        return fallback_text
        
    file_ext = os.path.splitext(file_location)[1].lower()
    full_text = ""
    
    try:
        if file_ext == '.pdf':
            with pdfplumber.open(file_location) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
                        
        elif file_ext in ['.docx', '.doc']:
            doc = Document(file_location)
            full_text_parts = []
            
            # 1. 提取普通段落
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text_parts.append(para.text.strip())
                    
            # 2. 提取表格数据
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        # 用 | 隔开单元格，保留表格的列语义
                        full_text_parts.append(" | ".join(row_text)) 
                        
            full_text = "\n".join(full_text_parts)
            
        elif file_ext == '.txt':
            with open(file_location, 'r', encoding='utf-8', errors='ignore') as f:
                full_text = f.read()
                
    except Exception as e:
        # 使用 logger 记录错误
        logger.error(f"❌ 文件 {file_location} 解析失败: {e}")
        full_text = fallback_text

    return full_text.strip() if full_text else fallback_text

def split_text_pure_python(text: str, chunk_size: int = 250, chunk_overlap: int = 30) -> list[str]:
    """
    纯 Python 实现的文本切片器，完美替代 LangChain 避免 Windows 底层死锁
    """
    if not text:
        return []
        
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        
        # 如果已经读到文本末尾，直接把剩下的全部加入并结束
        if end == text_length:
            chunks.append(text[start:end].strip())
            break
            
        # 为了不把一句话切断，我们在结尾附近寻找标点符号或换行符作为"自然断句点"
        search_start = max(start, end - chunk_overlap * 2)
        search_window = text[search_start:end]
        
        break_point = end
        # 按优先级寻找分隔符
        for sep in ["\n\n", "\n", "。", "！", "？", "；", "，", "、", " "]:
            pos = search_window.rfind(sep)
            if pos != -1:
                break_point = search_start + pos + len(sep)
                break
                
        chunks.append(text[start:break_point].strip())
        
        # 下一个切片从断句点往回退 overlap 个字符的位置开始
        next_start = break_point - chunk_overlap
        # 安全垫：确保指针必须往前移动，防止死循环
        start = max(next_start, start + 1) 
        
    # 过滤掉可能产生的空字符串
    return [c for c in chunks if c]