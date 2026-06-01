from celery import Celery
from decouple import config

celery_app = Celery(
    "code_review_bot",
    broker=config("REDIS_URL", default="redis://localhost:6379/0"),
    backend=config("REDIS_URL", default="redis://localhost:6379/0"),
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)