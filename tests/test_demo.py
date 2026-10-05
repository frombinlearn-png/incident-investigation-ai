import json

import httpx
import pytest

from app.demo import run_demo


@pytest.mark.parametrize("scenario", ["database-pool", "aem-cache", "unknown"])
async def test_demo_submits_packaged_incident(monkeypatch, capsys, scenario):
    original_client = httpx.AsyncClient

    async def handler(request):
        assert request.url.path == "/v1/investigations"
        assert "incident" in json.loads(request.content)
        return httpx.Response(200, json={"status": "completed"})

    monkeypatch.setattr(
        "app.demo.httpx.AsyncClient",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(handler),
            **kwargs,
        ),
    )
    assert await run_demo("http://test", scenario) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "completed"


@pytest.mark.parametrize("failure", ["http", "network"])
async def test_demo_reports_connection_and_api_failures(monkeypatch, capsys, failure):
    original_client = httpx.AsyncClient

    async def handler(request):
        if failure == "network":
            raise httpx.ConnectError("connection failed", request=request)
        return httpx.Response(503, json={"error": {"code": "provider_rate_limited"}})

    monkeypatch.setattr(
        "app.demo.httpx.AsyncClient",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(handler),
            **kwargs,
        ),
    )
    assert await run_demo("http://test", "database-pool") == 1
    assert capsys.readouterr().out
