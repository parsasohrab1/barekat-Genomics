"""انتخاب صف Celery بر اساس اولویت نمونه."""

from barekat_genomics.services.annotation_cache_service import (
    CELERY_QUEUE_DEFAULT,
    CELERY_QUEUE_URGENT,
    PRIORITY_NORMAL,
    PRIORITY_URGENT,
)


def resolve_priority(priority: str | None) -> str:
    if priority == PRIORITY_URGENT:
        return PRIORITY_URGENT
    return PRIORITY_NORMAL


def resolve_celery_queue(priority: str) -> str:
    return CELERY_QUEUE_URGENT if priority == PRIORITY_URGENT else CELERY_QUEUE_DEFAULT
