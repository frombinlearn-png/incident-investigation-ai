import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models import Incident
from app.services.retrieval_service import Retriever, load_chunks

DATA_DIR = Path(__file__).parents[1] / "app" / "data"


@pytest.fixture(autouse=True)
def clean_settings_environment(monkeypatch):
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


@pytest.fixture
def settings():
    return Settings(_env_file=None, provider="mock", runbook_dir=DATA_DIR / "runbooks")


@pytest.fixture
def incident_payload():
    return json.loads((DATA_DIR / "incidents" / "database-pool.json").read_text(encoding="utf-8"))


@pytest.fixture
def incident(incident_payload):
    return Incident.model_validate(incident_payload["incident"])


@pytest.fixture
def retriever(settings):
    return Retriever(load_chunks(settings.runbook_dir), settings.min_similarity)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client
