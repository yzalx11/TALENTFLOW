# app/api/v1/admin/status_manager.py
"""
管理后台统计看板 API — 关键指标 + 趋势图 + 占比图
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.models.user import User
from app.models.job_position import JobPosition
from app.models.resume import Resume
from app.models.skills import SkillDict
from app.core.database import get_db
from app.core.deps import get_current_active_admin

router = APIRouter(prefix="/api/v1/admin", tags=["Admin-Stats"])


@router.get("/stats/overview")
def get_stats_overview(
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
):
    """返回管理后台首页的三组统计数据"""

    # 1. 关键指标
    total_users = db.query(func.count(User.id)).scalar()
    total_jobs = db.query(func.count(JobPosition.id)).scalar()
    total_resumes = db.query(func.count(Resume.id)).scalar()
    pending_reviews = db.query(func.count(Resume.id)).filter(
        Resume.status.in_(["pending", "processed"])
    ).scalar()

    overview = {
        "total_users": total_users or 0,
        "total_jobs": total_jobs or 0,
        "total_resumes": total_resumes or 0,
        "pending_reviews": pending_reviews or 0,
    }

    # 2. 近七天趋势 — 简历入库量（若无则用用户注册量）
    trend_sql = text("""
        SELECT DATE(created_at) AS date, COUNT(*) AS count
        FROM resumes
        WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
        GROUP BY DATE(created_at)
        ORDER BY date
    """)
    try:
        rows = db.execute(trend_sql).fetchall()
        trend = [{"date": str(r[0]), "count": r[1]} for r in rows]
    except Exception:
        trend = []

    # 3. 技能分类占比
    rows = (
        db.query(
            func.ifnull(SkillDict.category, "未分类").label("name"),
            func.count(SkillDict.id).label("value"),
        )
        .group_by(SkillDict.category)
        .order_by(func.count(SkillDict.id).desc())
        .all()
    )
    distribution = [{"name": r.name, "value": r.value} for r in rows]

    return {
        "code": 200,
        "data": {
            "overview": overview,
            "trend": trend,
            "distribution": distribution,
        },
    }
