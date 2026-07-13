"""Pytest configuration."""

import os
from pathlib import Path

# Tests run without JWT — dev admin user is injected automatically
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("PIPELINE_MODE", "simulated")
os.environ.setdefault("ANNOTATION_CACHE_ENABLED", "false")
os.environ.setdefault("METRICS_ENABLED", "true")
os.environ.setdefault("MODEL_PATH", str(Path(__file__).resolve().parents[1] / "data" / "models"))
os.environ.setdefault("KNOWLEDGE_DIR", str(Path(__file__).resolve().parents[1] / "data" / "reference" / "knowledge"))


import pytest
from fastapi.testclient import TestClient

from barekat_genomics.api.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)
