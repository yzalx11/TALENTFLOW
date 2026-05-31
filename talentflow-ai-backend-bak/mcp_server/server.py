# mcp_server/server.py
"""
MCP Server — 将推荐系统封装为标准工具，供 AI Agent 调用
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import FastMCP
from celery.result import AsyncResult

from app.celery_app import celery_app
from app.rag.recommendation import compute_recommendations

mcp = FastMCP("JobPlatform-Tools")


@mcp.tool()
async def recommend_jobs(user_id: int) -> dict:
    """
    为用户推荐最匹配的职位。

    该工具会触发 AI 推荐引擎，综合计算用户技能与所有职位的匹配度，
    返回 Top-5 推荐结果，包含得分、匹配技能和职位详情。

    Args:
        user_id: 用户ID

    Returns:
        包含 recommendations 列表的字典，每项包含 job_id, title, score, matched_skills 等
    """
    task = compute_recommendations.delay(user_id)
    result = AsyncResult(task.id, app=celery_app)
    try:
        data = result.get(timeout=30)
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def get_user_resume_info(user_id: int) -> dict:
    """
    查询用户的简历基本信息。

    Args:
        user_id: 用户ID

    Returns:
        用户的简历信息
    """
    from app.core.database import SessionLocal
    from app.models.resume import Resume

    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.user_id == user_id).first()
        if not resume:
            return {"error": "未找到简历"}

        return {
            "user_id": user_id,
            "name": resume.name,
            "title": resume.title,
            "skills": resume.skills,
            "summary": resume.summary,
            "education": resume.education,
            "experience": resume.experience,
        }
    finally:
        db.close()


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8002)
 