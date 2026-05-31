# mcp_server/server.py
"""MCP Server — 标准化工具暴露，供 AI Agent 调用"""
import sys, os, asyncio
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
# 清理过期的 .pyc 确保加载最新代码
for root, dirs, files in os.walk(os.path.join(_root, "app")):
    if "__pycache__" in dirs:
        for f in os.listdir(os.path.join(root, "__pycache__")):
            os.remove(os.path.join(root, "__pycache__", f))

from fastmcp import FastMCP
from celery.result import AsyncResult

from app.core.database import SyncSessionLocal
from app.celery_app import celery_app
from app.rag.recommendation import compute_recommendations

mcp = FastMCP("JobPlatform-Tools")


@mcp.tool()
async def recommend_jobs(user_id: int) -> dict:
    """为用户推荐最匹配的职位，返回 Top-5 推荐结果"""
    task = compute_recommendations.delay(user_id)
    celery_result = AsyncResult(task.id, app=celery_app)
    try:
        # 异步等待 Celery 结果，不阻塞事件循环
        data = await asyncio.to_thread(celery_result.get, timeout=30)
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def get_user_resume_info(user_id: int) -> dict:
    """查询用户的简历基本信息（纯 pymysql，不依赖 app 模块避免 import 链冲突）"""
    import pymysql, os
    conn = pymysql.connect(
        host=os.getenv("MYSQL_SERVER", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", "password"),
        database=os.getenv("MYSQL_DATABASE", "dandelion_tribe"),
        charset="utf8mb4",
    )
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT name, title, skills, summary, education, experience FROM resumes WHERE user_id = %s LIMIT 1", (user_id,))
            row = cursor.fetchone()
            if not row:
                return {"error": "未找到简历"}
            return {"user_id": user_id, "name": row["name"], "title": row["title"],
                    "skills": row["skills"], "summary": row["summary"],
                    "education": row["education"], "experience": row["experience"]}
    finally:
        conn.close()


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8003)
