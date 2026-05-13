# app/core/vector_store.py
import os
from langchain_community.vectorstores import FAISS
from app.core.embedding import get_embedding_function
from app.core.config import settings
from app.core.logger import logger

# --- 1. 配置常量 (完全采用老师的架构写法) ---
VECTOR_DB_PATH = settings.VECTOR_DB_PATH
# LangChain 会自动在这个目录下生成 index.faiss 和 index.pkl
# 我们统一管控这个根目录

# 2. 确保目录在服务启动时就存在 (Fail-Fast 原则)
os.makedirs(VECTOR_DB_PATH, exist_ok=True)


def add_documents_to_faiss(chunks: list, metadatas: list = None):
    """
    将切分好的文本块转换为向量，并保存到本地 FAISS 数据库中
    """
    if not chunks:
        return
        
    embeddings = get_embedding_function()
    
    try:
        # 使用常量 VECTOR_DB_PATH
        if os.path.exists(os.path.join(VECTOR_DB_PATH, "index.faiss")):
            logger.info("📦 检测到已有 FAISS 索引，正在加载并追加新数据...")
            vector_store = FAISS.load_local(
                VECTOR_DB_PATH, 
                embeddings, 
                allow_dangerous_deserialization=True
            )
            vector_store.add_texts(texts=chunks, metadatas=metadatas)
        else:
            logger.info("🆕 未检测到 FAISS 索引，正在创建全新数据库...")
            vector_store = FAISS.from_texts(texts=chunks, embedding=embeddings, metadatas=metadatas)
            
        # 保存时也只用传常量目录
        vector_store.save_local(VECTOR_DB_PATH)
        logger.info(f"✅ 成功将 {len(chunks)} 条向量存入 FAISS！")
        
        return vector_store
    except Exception as e:
        logger.error(f"❌ 操作 FAISS 数据库时发生错误: {e}")
        raise e