from fastapi import FastAPI
from contextlib import asynccontextmanager
# 导入路由
from app.api.v1 import auth
from app.api.v1.admin import user_manager

# 导入 CORS 中间件, 用于处理浏览器的跨域资源共享请求
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("正在连接数据库...")
    yield 
    print("服务正在关闭，清理资源...")

app = FastAPI(title="AI蒲公英部落",lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # 允许所有来源的跨域请求 (生产环境建议指定具体域名)
    allow_credentials=True,    # 允许跨域请求携带 Cookie 或认证信息
    allow_methods=["*"],       # 允许所有 HTTP 方法 (GET, POST, PUT, DELETE 等)
    allow_headers=["*"],       
)

#注册路由

app.include_router(auth.router)
app.include_router(user_manager.router)
@app.get("/")
async def root():
    return {"message":"Hello"}