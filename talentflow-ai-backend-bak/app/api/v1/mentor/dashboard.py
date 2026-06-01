# app/api/v1/mentor/dashboard.py
"""导师工作台 — 动态时间轴 + 统计看板"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.models.user import User
from app.core.database import get_db
from app.core.deps import get_current_user

router = APIRouter(prefix="/api/v1/mentor", tags=["Mentor-Dashboard"])


def _require_mentor(current_user: User) -> User:
    if current_user.role != 2: raise HTTPException(status_code=403, detail="仅导师可访问")
    return current_user


@router.get("/timeline")
async def get_timeline(limit: int = Query(10, ge=1, le=50), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    mentor = _require_mentor(current_user)
    sql = text("""SELECT event_type, title, detail, user_name, event_time, ref_id, ref_status FROM (
        SELECT 'task_update' AS event_type, t.title,
        CASE t.status WHEN 0 THEN '任务已发布（草稿）' WHEN 1 THEN '任务进行中' WHEN 2 THEN '任务已暂停' WHEN 3 THEN '任务已完成' ELSE '任务状态更新' END AS detail,
        COALESCE(u.full_name, u.username, '未知用户') AS user_name, t.created_at AS event_time, t.id AS ref_id, NULL AS ref_status
        FROM tasks t LEFT JOIN users u ON u.id = t.taken_by WHERE t.mentor_id = :mentor_id AND t.status != 0
        UNION ALL
        SELECT 'new_delivery' AS event_type, t.title,
        CASE a.status WHEN 'applied' THEN '投递了任务' WHEN 'approved' THEN '投递已通过' WHEN 'rejected' THEN '投递已驳回' ELSE CONCAT('投递状态: ', a.status) END AS detail,
        COALESCE(u2.full_name, u2.username, '未知用户') AS user_name, a.created_at AS event_time, a.id AS ref_id, a.status AS ref_status
        FROM applications a JOIN tasks t ON t.id = a.task_id JOIN users u2 ON u2.id = a.user_id WHERE t.mentor_id = :mentor_id) combined
        ORDER BY event_time DESC LIMIT :limit""")
    rows = await db.execute(sql, {"mentor_id": mentor.id, "limit": limit})
    return [{"event_type": r[0], "title": r[1], "detail": r[2], "user_name": r[3], "event_time": str(r[4]), "ref_id": r[5], "ref_status": r[6]} for r in rows.fetchall()]


@router.get("/stats")
async def get_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    mentor = _require_mentor(current_user)
    sql = text("""SELECT (SELECT COUNT(*) FROM tasks WHERE mentor_id = :mid) AS total_published,
        (SELECT COUNT(*) FROM tasks WHERE mentor_id = :mid AND status = 1) AS in_progress,
        (SELECT COALESCE(SUM(price), 0) FROM tasks WHERE mentor_id = :mid) AS total_bounty,
        (SELECT COUNT(*) FROM applications a JOIN tasks t ON t.id = a.task_id WHERE t.mentor_id = :mid AND a.status = 'applied') AS pending_reviews""")
    row = await db.execute(sql, {"mid": mentor.id}); r = row.fetchone()
    return {"total_published": r[0] or 0, "in_progress": r[1] or 0, "total_bounty": r[2] or 0, "pending_reviews": r[3] or 0}
