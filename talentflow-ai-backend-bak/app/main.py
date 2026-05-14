# app/main.py
import os
# 🟢 第一步：注入 Windows 防崩溃环境变量 (必须在所有 AI 库导入前)
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
os.environ["OMP_NUM_THREADS"] = "1" 

import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

# 导入路由
from app.api.v1 import auth
from app.api.v1.admin import user_manager, task_manager, job_manager


from app.core.embedding import get_embedding_function

# 🟢 执行预加载
print("=================================================")
print("🚀 [系统预热] 正在同步加载本地 Embedding 模型...")
try:
    # 这一步会触发 get_embedding_function 内部的打印，大约耗时 5-10 秒
    get_embedding_function()
    print("✅ [系统预热] 模型加载成功，内存单例已就绪")
except Exception as e:
    print(f"❌ [系统预热] 模型加载失败: {e}")
print("=================================================")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🌐 [服务启动] FastAPI 异步服务已进入就绪状态")
    yield 
    print("🛑 [系统关闭] 正在清理资源...")

app = FastAPI(title="AI蒲公英部落", lifespan=lifespan)

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       
    allow_credentials=True,    
    allow_methods=["*"],       
    allow_headers=["*"],       
)

# 注册路由
app.include_router(auth.router)
app.include_router(user_manager.router)
app.include_router(task_manager.router)
app.include_router(job_manager.router)

@app.get("/")
async def root():
    return {"message": "TalentFlow AI Backend is running"}

if __name__ == "__main__":
    import uvicorn
    # 手动调用 uvicorn，并强制设置 workers=1 保证稳定性
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)