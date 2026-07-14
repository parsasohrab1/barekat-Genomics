"""پیکربندی Celery برای پردازش ناهمزمان."""

from celery import Celery
from kombu import Exchange, Queue

from barekat_genomics.core.config import get_settings
from barekat_genomics.services.annotation_cache_service import CELERY_QUEUE_DEFAULT, CELERY_QUEUE_URGENT

settings = get_settings()

celery_app = Celery(
    "barekat_genomics",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

default_exchange = Exchange("barekat", type="direct")

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue=CELERY_QUEUE_DEFAULT,
    task_queues=(
        Queue(CELERY_QUEUE_URGENT, exchange=default_exchange, routing_key=CELERY_QUEUE_URGENT),
        Queue(CELERY_QUEUE_DEFAULT, exchange=default_exchange, routing_key=CELERY_QUEUE_DEFAULT),
    ),
    task_routes={
        "barekat_genomics.run_pipeline": {"queue": CELERY_QUEUE_DEFAULT},
    },
    task_annotations={
        "barekat_genomics.run_pipeline": {
            "max_retries": 3,
            "acks_late": True,
        },
    },
)

celery_app.autodiscover_tasks(["barekat_genomics.tasks"])
