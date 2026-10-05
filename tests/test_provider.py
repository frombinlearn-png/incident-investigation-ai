import json

import httpx
import pytest

from app.config import Settings
from app.errors import AppError
from app.services.llm_service import MockProvider, OpenAIProvider
from app.services.prompt_service import SYSTEM_PROMPT, build_context


@pytest.fixture
def provider_settings():
    return Settings(_env_file=None, provider="openai", openai_api_key="test-only-key")


@pytest.fixture
def context(retriever, incident):
    return build_context(incident, retriever.search(incident.retrieval_text()), 12000)


def envelope(analysis):
    return {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": analysis.model_dump_json()},
                ],
            }
        ],
    }


async def test_real_provider_wire_contract(provider_settings, context, incident):
    expected = await MockProvider().generate(incident, context)
    captured = []

    async def handler(request):
        captured.append(request)
        return httpx.Response(200, json=envelope(expected))

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://api.openai.com/v1/"
    ) as client:
        result = await OpenAIProvider(client, provider_settings).generate(incident, context)
    assert result == expected
    assert str(captured[0].url) == "https://api.openai.com/v1/responses"
    payload = json.loads(captured[0].content)
    assert payload["store"] is False
    assert payload["instructions"] == SYSTEM_PROMPT
    assert payload["input"][0]["content"] == context.user_message
    assert payload["text"]["format"]["strict"] is True
    assert payload["text"]["format"]["schema"]["additionalProperties"] is False


async def test_transient_failure_retries_then_succeeds(provider_settings, context, incident):
    expected = await MockProvider().generate(incident, context)
    attempts = []

    async def handler(request):
        attempts.append(request)
        return (
            httpx.Response(503)
            if len(attempts) == 1
            else httpx.Response(200, json=envelope(expected))
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://test/v1/"
    ) as client:
        assert (
            await OpenAIProvider(client, provider_settings).generate(incident, context) == expected
        )
    assert len(attempts) == 2


@pytest.mark.parametrize(
    ("status", "code", "attempts"),
    [
        (401, "provider_rejected", 1),
        (400, "provider_rejected", 1),
        (302, "provider_rejected", 1),
        (429, "provider_rate_limited", 2),
        (500, "provider_unavailable", 2),
    ],
)
async def test_http_failures_are_bounded_and_sanitized(
    provider_settings,
    context,
    incident,
    status,
    code,
    attempts,
):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(status, text="sensitive-upstream-error")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://test/v1/"
    ) as client:
        with pytest.raises(AppError) as error:
            await OpenAIProvider(client, provider_settings).generate(incident, context)
    assert error.value.code == code
    assert "sensitive-upstream-error" not in str(error.value)
    assert len(requests) == attempts


@pytest.mark.parametrize(
    ("error_type", "code"),
    [
        (httpx.ReadTimeout, "provider_timeout"),
        (httpx.ConnectError, "provider_unavailable"),
    ],
)
async def test_network_errors_are_mapped(provider_settings, context, incident, error_type, code):
    async def handler(request):
        raise error_type("private details", request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://test/v1/"
    ) as client:
        with pytest.raises(AppError) as error:
            await OpenAIProvider(client, provider_settings).generate(incident, context)
    assert error.value.code == code


@pytest.mark.parametrize(
    "data",
    [
        {},
        [],
        {"status": "incomplete", "output": []},
        {"status": "completed", "output": []},
        {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "not JSON"},
                    ],
                }
            ],
        },
        {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": '{"summary":"missing required fields"}'},
                    ],
                }
            ],
        },
    ],
)
def test_bad_provider_payload_is_rejected(data):
    with pytest.raises(AppError, match="invalid analysis"):
        OpenAIProvider._parse(httpx.Response(200, json=data))


def test_refusal_has_explicit_error():
    data = {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "refusal", "refusal": "No"},
                ],
            }
        ],
    }
    with pytest.raises(AppError) as error:
        OpenAIProvider._parse(httpx.Response(200, json=data))
    assert error.value.code == "provider_refusal"


def test_invalid_json_and_oversized_output_rejected():
    for text in ("not-json", "x" * 128001):
        with pytest.raises(AppError):
            OpenAIProvider._parse(httpx.Response(200, text=text))
