import asyncio
import logging
from typing import Protocol

import httpx
from pydantic import ValidationError

from app.config import Settings
from app.errors import AppError
from app.models import Analysis, CitedFinding, Incident
from app.services.prompt_service import SYSTEM_PROMPT, PromptContext

logger = logging.getLogger("incident_ai")


class AnalysisProvider(Protocol):
    async def generate(self, incident: Incident, context: PromptContext) -> Analysis: ...


class MockProvider:
    """Deterministic extractive template; no neural model or external requests."""

    async def generate(self, incident: Incident, context: PromptContext) -> Analysis:
        findings = [
            CitedFinding(
                text=(
                    f"Possible match: {item.title} / {item.section}. Confirm against live evidence."
                ),
                source_ids=[item.source_id],
            )
            for item in context.evidence
        ]
        checks = [
            CitedFinding(
                text=f"Compare the incident with this runbook excerpt: {item.text}",
                source_ids=[item.source_id],
            )
            for item in context.evidence
        ]
        return Analysis(
            summary=(
                f"Retrieved {len(context.evidence)} potentially relevant runbook passages for "
                f"{incident.service}. This deterministic template has not established a root cause."
            ),
            hypotheses=findings,
            recommended_checks=checks,
            missing_information=[
                "Confirm the incident timeline, affected users, and scope.",
                "Collect sanitized logs, relevant metrics, and recent deployment changes.",
            ],
        )


class OpenAIProvider:
    def __init__(self, client: httpx.AsyncClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings

    async def generate(self, incident: Incident, context: PromptContext) -> Analysis:
        payload = {
            "model": self.settings.openai_model,
            "store": False,
            "instructions": SYSTEM_PROMPT,
            "input": [{"role": "user", "content": context.user_message}],
            "max_output_tokens": 2000,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "incident_analysis",
                    "strict": True,
                    "schema": Analysis.model_json_schema(),
                }
            },
        }
        last_error = AppError("provider_unavailable", "The model provider is unavailable.")
        for attempt in range(self.settings.provider_max_attempts):
            try:
                response = await self.client.post("responses", json=payload)
            except httpx.TimeoutException:
                last_error = AppError("provider_timeout", "The model provider timed out.", 504)
            except httpx.RequestError:
                last_error = AppError(
                    "provider_unavailable", "Could not contact the model provider."
                )
            else:
                if response.status_code == 429:
                    last_error = AppError(
                        "provider_rate_limited", "The model provider is busy.", 503
                    )
                elif response.status_code >= 500:
                    last_error = AppError(
                        "provider_unavailable", "The model provider is unavailable."
                    )
                elif not response.is_success:
                    raise AppError("provider_rejected", "The model provider rejected the request.")
                else:
                    return self._parse(response)
            if attempt + 1 < self.settings.provider_max_attempts:
                logger.warning(
                    "provider_retry", extra={"attempt": attempt + 1, "error_code": last_error.code}
                )
                await asyncio.sleep(0.1 * (2**attempt))
        raise last_error

    @staticmethod
    def _parse(response: httpx.Response) -> Analysis:
        try:
            if len(response.content) > 128000:
                raise ValueError("Oversized response")
            data = response.json()
            if data.get("status") != "completed":
                raise ValueError("Incomplete response")
            parts: list[str] = []
            for output in data["output"]:
                if output.get("type") != "message":
                    continue
                for content in output["content"]:
                    if content.get("type") == "refusal":
                        raise AppError("provider_refusal", "The model declined this request.")
                    if content.get("type") == "output_text":
                        parts.append(content["text"])
            return Analysis.model_validate_json("".join(parts))
        except (ValueError, KeyError, TypeError, AttributeError, ValidationError):
            raise AppError(
                "invalid_provider_response", "The model returned an invalid analysis."
            ) from None
