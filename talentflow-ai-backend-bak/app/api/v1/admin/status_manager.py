# app/api/v1/admin/status_manager.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User
from app.models.job_position import JobPosition
from app.models.resume import Resume
from app.models.skills import SkillDict
from app.core.database import get_db
from app.core.deps import get_current_active_admin

router = APIRouter(prefix="/api/v1/admin", tags=["Admin-Stats"])


@router.get("/stats/overview")
async def get_stats_overview(current_user: User = Depends(get_current_active_admin), db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(select(func.count(User.id)))
    total_users = user_result.scalar()

    job_result = await db.execute(select(func.count(JobPosition.id)))
    total_jobs = job_result.scalar()

    resume_result = await db.execute(select(func.count(Resume.id)))
    total_resumes = resume_result.scalar()

    pending_result = await db.execute(select(func.count(Resume.id)).where(Resume.status.in_(["pending", "processed"])))
    pending_reviews = pending_result.scalar()

    from sqlalchemy import text
    trend_rows = await db.execute(text(
        "SELECT DATE(created_at) AS date, COUNT(*) AS count FROM resumes "
        "WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 6 DAY) "
        "GROUP BY DATE(created_at) ORDER BY date"
    ))
    trend = [{"date": str(row[0]), "count": row[1]} for row in trend_rows.fetchall()]

    category_rows = await db.execute(
        select(
            func.ifnull(SkillDict.category, "未分类").label("name"),
            func.count(SkillDict.id).label("value"),
        ).group_by(SkillDict.category).order_by(func.count(SkillDict.id).desc())
    )
    distribution = [{"name": row.name, "value": row.value} for row in category_rows.fetchall()]

    return {
        "code": 200,
        "data": {
            "overview": {
                "total_users": total_users or 0,
                "total_jobs": total_jobs or 0,
                "total_resumes": total_resumes or 0,
                "pending_reviews": pending_reviews or 0,
            },
            "trend": trend,
            "distribution": distribution,
        },
    }
