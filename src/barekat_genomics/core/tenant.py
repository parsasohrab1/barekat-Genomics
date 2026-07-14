"""حالت tenant جاری (contextvars) و ایزولاسیون داده."""

from __future__ import annotations

import uuid
from contextvars import ContextVar

from sqlalchemy.orm import Query

_current_org_id: ContextVar[uuid.UUID | None] = ContextVar("current_org_id", default=None)


def set_current_org_id(org_id: uuid.UUID | None) -> None:
    _current_org_id.set(org_id)


def get_current_org_id() -> uuid.UUID | None:
    return _current_org_id.get()


def filter_by_organization(query: Query, model, org_id: uuid.UUID | None) -> Query:
    """اعمال فیلتر organization_id در صورت وجود ستون و شناسه."""
    if org_id is None or not hasattr(model, "organization_id"):
        return query
    return query.filter(model.organization_id == org_id)


DEFAULT_ORG_SLUG = "default"
DEFAULT_ORG_NAME = "Default Organization"
