import json
import logging
from io import StringIO

import pytest

from app.logging_config import JsonFormatter


def test_health_runbooks_and_documentation(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["provider"] == "mock"
    assert health.json()["indexed_chunks"] == 18
    assert len(client.get("/v1/runbooks").json()) == 6
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/v1/investigations" in schema["paths"]


def test_investigation_returns_cited_deterministic_analysis(client, incident_payload):
    first = client.post("/v1/investigations", json=incident_payload)
    second = client.post("/v1/investigations", json=incident_payload)
    assert first.status_code == 200
    data = first.json()
    assert data["status"] == "completed"
    assert data["generation_mode"] == "deterministic_template"
    assert data["evidence"][0]["runbook_id"] == "database-pool"
    assert data["request_id"] == first.headers["x-request-id"]
    assert data["request_id"] != second.json()["request_id"]
    assert data["analysis"] == second.json()["analysis"]
    allowed = {item["source_id"] for item in data["evidence"]}
    for finding in data["analysis"]["hypotheses"] + data["analysis"]["recommended_checks"]:
        assert set(finding["source_ids"]) <= allowed


def test_search_is_available_independently(client):
    response = client.post("/v1/search", json={"query": "OOMKilled memory pressure", "top_k": 1})
    assert response.status_code == 200
    assert response.json()["embedding_method"] == "tfidf"
    assert response.json()["evidence"][0]["runbook_id"] == "memory-pressure"


@pytest.mark.parametrize(
    "change",
    [
        {"top_k": 0},
        {"top_k": 6},
        {"unknown": True},
        {"incident": {}},
        {"incident": {"title": "   ", "description": " " * 20}},
    ],
)
def test_invalid_payload_returns_safe_error(client, incident_payload, change):
    response = client.post("/v1/investigations", json={**incident_payload, **change})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]


def test_malformed_json_is_sanitized(client):
    response = client.post(
        "/v1/investigations",
        content='{"secret":"super-secret",',
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422
    assert "super-secret" not in response.text


def test_large_request_rejected_even_without_content_length(client):
    response = client.post("/v1/investigations", content=iter([b"x" * 40000, b"y" * 40000]))
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"


def test_unknown_route_uses_error_envelope(client):
    response = client.get("/missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"


def test_request_ids_are_generated_not_trusted(client):
    response = client.get("/health", headers={"x-request-id": "untrusted-value"})
    assert response.headers["x-request-id"] != "untrusted-value"
    assert len(response.headers["x-request-id"]) == 32


def test_unknown_incident_abstains(client):
    payload = {
        "incident": {
            "title": "Quantum interferometer",
            "description": "Entangled photons exhibit anomalous polarization.",
        }
    }
    response = client.post("/v1/investigations", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_evidence"
    assert response.json()["analysis"] is None
    assert response.json()["evidence"] == []


def test_logs_exclude_incident_content(client, incident_payload, monkeypatch):
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    monkeypatch.setattr(logging.getLogger("incident_ai"), "handlers", [handler])
    incident_payload["incident"]["description"] += " SECRET_MARKER_123456"
    client.post("/v1/investigations", json=incident_payload)
    output = stream.getvalue()
    assert "SECRET_MARKER_123456" not in output
    records = [json.loads(line) for line in output.splitlines() if line.startswith("{")]
    assert any(record["event"] == "request_completed" for record in records)
