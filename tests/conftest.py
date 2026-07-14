"""Pytest configuration با دیتابیس تست SQLite و پوشش API."""

import os
import uuid
from pathlib import Path

# قبل از هر import برنامه
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("PIPELINE_MODE", "simulated")
os.environ.setdefault("ANNOTATION_CACHE_ENABLED", "false")
os.environ.setdefault("METRICS_ENABLED", "true")
os.environ.setdefault("AUDIT_LOG_ENABLED", "true")
os.environ.setdefault("MODEL_PATH", str(Path(__file__).resolve().parents[1] / "data" / "models"))
os.environ.setdefault(
    "KNOWLEDGE_DIR",
    str(Path(__file__).resolve().parents[1] / "data" / "reference" / "knowledge"),
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from barekat_genomics.api.main import create_app
from barekat_genomics.core.database import Base, get_db
from barekat_genomics.models.user import User

# مدل‌ها را برای metadata ثبت کنید
import barekat_genomics.models.organization  # noqa: F401
import barekat_genomics.models.billing  # noqa: F401
import barekat_genomics.models.cohort  # noqa: F401
import barekat_genomics.models.api_key  # noqa: F401
import barekat_genomics.models.result_cache  # noqa: F401
import barekat_genomics.models.knowledge_asset  # noqa: F401
import barekat_genomics.models.audit  # noqa: F401
import barekat_genomics.models.annotation_cache  # noqa: F401
import barekat_genomics.models.patient  # noqa: F401
import barekat_genomics.models.pipeline  # noqa: F401
import barekat_genomics.models.report  # noqa: F401
import barekat_genomics.models.sample  # noqa: F401
import barekat_genomics.models.variant  # noqa: F401
import barekat_genomics.models.user  # noqa: F401

DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_pragma(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    from barekat_genomics.models.organization import Organization, OrganizationMembership
    from barekat_genomics.core.tenant import DEFAULT_ORG_NAME, DEFAULT_ORG_SLUG

    org = Organization(
        slug=DEFAULT_ORG_SLUG,
        name=DEFAULT_ORG_NAME,
        name_fa="سازمان پیش‌فرض",
        deployment_mode="saas",
        is_active=True,
    )
    session.add(org)
    session.flush()
    session.add(
        User(
            id=DEV_USER_ID,
            email="dev@barekat.local",
            hashed_password="unused",
            full_name="Dev Admin",
            role="admin",
            organization_id=org.id,
            is_active=True,
        )
    )
    session.flush()
    session.add(
        OrganizationMembership(
            organization_id=org.id,
            user_id=DEV_USER_ID,
            org_role="owner",
        )
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_engine, db_session):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
