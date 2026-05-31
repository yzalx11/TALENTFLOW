# app/celery_app.py
import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")

celery_app = Celery(
    "talentflow",
    broker=f"{REDIS_URL}/0",
    backend=f"{REDIS_URL}/1",
    include=["app.rag.recommendation"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,
)
