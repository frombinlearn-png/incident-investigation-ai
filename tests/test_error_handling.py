import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.errors import AppError
from app.main import create_app
from app.models import InvestigationRequest
from app.services.investigation_service import InvestigationService
from app.services.llm_service import MockProvider


class BrokenProvider:
    async def generate(self, incident, context):
        raise RuntimeError("secret database password")


def test_unexpected_exception_is_sanitized(settings, incident_payload):
    with TestClient(create_app(settings, BrokenProvider())) as client:
        response = client.post("/v1/investigations", json=incident_payload)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "password" not in response.text


@pytest.mark.parametrize(
    ("code", "status"),
    [
        ("provider_timeout", 504),
        ("provider_rate_limited", 503),
        ("invalid_provider_response", 502),
    ],
)
def test_provider_errors_preserve_status(settings, incident_payload, code, status):
    class FailedProvider:
        async def generate(self, incident, context):
            raise AppError(code, "Provider failed.", status)

    with TestClient(create_app(settings, FailedProvider())) as client:
        response = client.post("/v1/investigations", json=incident_payload)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


async def test_unknown_evidence_skips_provider(settings, retriever):
    service = InvestigationService(retriever, BrokenProvider(), settings)
    request = InvestigationRequest.model_validate(
        {
            "incident": {
                "title": "Quantum interferometer",
                "description": "Entangled photon polarization drift.",
            }
        }
    )
    response = await service.investigate(request, "test")
    assert response.status == "insufficient_evidence"


async def test_context_omission_is_reported(settings, retriever, incident_payload):
    config = settings.model_copy(update={"max_context_chars": 1024})
    service = InvestigationService(retriever, MockProvider(), config)
    response = await service.investigate(
        InvestigationRequest.model_validate(incident_payload),
        "test",
    )
    assert any("Context budget omitted" in warning for warning in response.warnings)
    assert len(response.evidence) < 3


async def test_unknown_citation_is_rejected(settings, retriever, incident_payload):
    class FabricatedCitationProvider:
        async def generate(self, incident, context):
            analysis = await MockProvider().generate(incident, context)
            analysis.hypotheses[0].source_ids = ["invented#001"]
            return analysis

    service = InvestigationService(retriever, FabricatedCitationProvider(), settings)
    with pytest.raises(AppError) as error:
        await service.investigate(InvestigationRequest.model_validate(incident_payload), "test")
    assert error.value.code == "invalid_citation"


async def test_deadline_cancels_provider_and_releases_capacity(
    settings, retriever, incident_payload
):
    cancelled = asyncio.Event()

    class HangingProvider:
        async def generate(self, incident, context):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

    config = settings.model_copy(
        update={"request_timeout_seconds": 0.05, "max_concurrent_investigations": 1}
    )
    service = InvestigationService(retriever, HangingProvider(), config)
    request = InvestigationRequest.model_validate(incident_payload)
    with pytest.raises(AppError) as error:
        await service.investigate(request, "test")
    assert error.value.code == "investigation_timeout"
    assert cancelled.is_set()
    service.provider = MockProvider()
    assert (await service.investigate(request, "next")).status == "completed"


async def test_requests_can_overlap_without_blocking_event_loop(settings, incident_payload):
    entered = asyncio.Event()
    active = 0

    class RendezvousProvider:
        async def generate(self, incident, context):
            nonlocal active
            active += 1
            if active == 2:
                entered.set()
            await asyncio.wait_for(entered.wait(), timeout=2)
            return await MockProvider().generate(incident, context)

    application = create_app(settings, RendezvousProvider())
    async with application.router.lifespan_context(application):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://test"
        ) as client:
            responses = await asyncio.gather(
                *[client.post("/v1/investigations", json=incident_payload) for _ in range(2)]
            )
    assert all(response.status_code == 200 for response in responses)
    assert active == 2


async def test_concurrency_limit_is_enforced(settings, retriever, incident_payload):
    active = 0
    peak = 0

    class CountingProvider:
        async def generate(self, incident, context):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return await MockProvider().generate(incident, context)

    config = settings.model_copy(update={"max_concurrent_investigations": 2})
    service = InvestigationService(retriever, CountingProvider(), config)
    request = InvestigationRequest.model_validate(incident_payload)
    results = await asyncio.gather(
        *[service.investigate(request, str(index)) for index in range(6)]
    )
    assert all(result.status == "completed" for result in results)
    assert peak == 2


def test_openai_requires_key_and_hides_it_in_repr():
    with pytest.raises(ValidationError, match="OPENAI_API_KEY"):
        Settings(_env_file=None, provider="openai")
    configured = Settings(_env_file=None, provider="openai", openai_api_key="secret-value")
    assert "secret-value" not in repr(configured)


def test_settings_load_environment(monkeypatch):
    monkeypatch.setenv("MIN_SIMILARITY", "0.4")
    assert Settings(_env_file=None).min_similarity == 0.4


def test_startup_rejects_missing_corpus(settings, tmp_path):
    with pytest.raises(ValueError, match="No Markdown"):
        with TestClient(create_app(settings.model_copy(update={"runbook_dir": tmp_path}))):
            pass
