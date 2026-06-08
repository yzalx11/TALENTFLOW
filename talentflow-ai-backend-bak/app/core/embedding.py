#负责将文本转化为向量
# app/core/embedding.py
import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_UPDATE_DICT"] = "0"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
from app.core.config import settings
from app.core.logger import logger
from langchain_huggingface import HuggingFaceEmbeddings

_embedding_instance = None

def get_embedding_function():
    global _embedding_instance
    if _embedding_instance is not None:
        return _embedding_instance

    model_path = settings.EMBEDDING_MODEL_PATH
    if not model_path or not os.path.isdir(model_path):
        raise FileNotFoundError(f"Embedding 模型路径不存在: {model_path}")
    logger.info(f"⏳ [初始化] 正在加载本地 Embedding 模型: {model_path}")
    
    # 初始化配置
    model_kwargs = {
        'device': 'cpu',
        'trust_remote_code': True ,
        'local_files_only': True, 
    }
    
    encode_kwargs = {
        'normalize_embeddings': True ,#余弦相似度
        'batch_size': 16,  
    }
    
    # 3. 实例化模型并返回
    embeddings = HuggingFaceEmbeddings(
        model_name=model_path,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )
    logger.info("✅ [初始化] Embedding 模型加载成功！")
    _embedding_instance = embeddings
    return _embedding_instance