# app/api/v1/user/recommend.py
from fastapi import APIRouter, Depends
from celery.result import AsyncResult

from app.models.user import User
from app.core.deps import get_current_user
from app.rag.recommendation import compute_recommendations
from app.celery_app import celery_app

router = APIRouter(prefix="/api/v1/user", tags=["User-Recommend"])


@router.post("/recommend")
def submit_recommend(current_user: User = Depends(get_current_user)):
    task = compute_recommendations.delay(current_user.id)
    return {"task_id": task.id, "status": "PENDING"}


@router.get("/recommend/{task_id}")
def get_recommend_result(task_id: str, current_user: User = Depends(get_current_user)):
    result = AsyncResult(task_id, app=celery_app)
    if result.state == "PENDING": return {"task_id": task_id, "status": "PENDING"}
    elif result.state == "STARTED": return {"task_id": task_id, "status": "STARTED"}
    elif result.state == "SUCCESS": return {"task_id": task_id, "status": "SUCCESS", "data": result.result}
    elif result.state == "FAILURE": return {"task_id": task_id, "status": "FAILURE", "error": str(result.info)}
    return {"task_id": task_id, "status": result.state}
