# app/main.py
import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
os.environ["OMP_NUM_THREADS"] = "1" 

import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

# 把 Embedding 模型引入提到路由前
from app.core.embedding import get_embedding_function

print("=================================================")
print("🚀 [系统预热] 正在同步加载本地 Embedding 模型...")
try:
    # 让 PyTorch 先把模型加载进内存，抢占OpenMP 线程池
    get_embedding_function()
    print("✅ [系统预热] 模型加载成功，内存单例已就绪")
except Exception as e:
    print(f"❌ [系统预热] 模型加载失败: {e}")
print("=================================================")


#  等模型加载成功后，再导入包含 FAISS 向量库的路由
from app.api.v1 import auth
from app.api.v1.admin import user_manager, task_manager, job_manager, skill_manager, resume_manager, status_manager
from app.api.v1.mentor import dashboard as mentor_dashboard, task_manager as mentor_task, delivery_manager as mentor_delivery
from app.api.v1.user import recommend as user_recommend, task as user_task, resume as user_resume
from app.agent.router import router as agent_router
from app.agent.smart_deliver import router as smart_deliver_router
from app.api.v1 import internal


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
app.include_router(skill_manager.router)
app.include_router(resume_manager.router)
app.include_router(status_manager.router)
app.include_router(mentor_dashboard.router)
app.include_router(mentor_task.router)
app.include_router(mentor_delivery.router)
app.include_router(user_recommend.router)
app.include_router(user_task.router)
app.include_router(user_resume.router)
app.include_router(agent_router)
app.include_router(smart_deliver_router)
app.include_router(internal.router)

@app.get("/")
async def root():
    return {"message": "TalentFlow AI Backend is running"}

# 支持直接启动
if __name__ == "__main__":
    import uvicorn
    # 必须指定 reload=False 和 workers=1
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False, workers=1)