import json

import httpx
from fastapi.testclient import TestClient

from app.main import create_app


def test_openai_mode_wires_auth_and_parses_cited_response(
    settings,
    incident_payload,
    monkeypatch,
):
    original_client = httpx.AsyncClient
    captured = []

    async def handler(request):
        captured.append(request)
        payload = json.loads(request.content)
        context = json.loads(payload["input"][0]["content"])
        source_id = context["runbooks"][0]["source_id"]
        analysis = {
            "summary": "The evidence suggests database pool pressure; verify before changing it.",
            "hypotheses": [
                {"text": "Possible connection pool exhaustion.", "source_ids": [source_id]}
            ],
            "recommended_checks": [
                {"text": "Inspect waiting connections.", "source_ids": [source_id]}
            ],
            "missing_information": ["Database connection metrics at incident time."],
        }
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": json.dumps(analysis)}],
                    }
                ],
            },
        )

    monkeypatch.setattr(
        "app.main.httpx.AsyncClient",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(handler),
            **kwargs,
        ),
    )
    config = type(settings)(
        _env_file=None,
        provider="openai",
        openai_api_key="test-key-not-a-real-secret",
        runbook_dir=settings.runbook_dir,
    )
    with TestClient(create_app(config)) as client:
        response = client.post("/v1/investigations", json=incident_payload)
    assert response.status_code == 200
    assert response.json()["provider"] == "openai"
    assert response.json()["generation_mode"] == "llm"
    assert len(captured) == 1
    assert captured[0].headers["authorization"] == "Bearer test-key-not-a-real-secret"
    assert str(captured[0].url) == "https://api.openai.com/v1/responses"
