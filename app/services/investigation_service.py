import asyncio

from starlette.concurrency import run_in_threadpool

from app.config import Settings
from app.errors import AppError
from app.models import InvestigationRequest, InvestigationResponse
from app.services.llm_service import AnalysisProvider
from app.services.prompt_service import build_context
from app.services.retrieval_service import Retriever


class InvestigationService:
    def __init__(
        self, retriever: Retriever, provider: AnalysisProvider, settings: Settings
    ) -> None:
        self.retriever = retriever
        self.provider = provider
        self.settings = settings
        self.capacity = asyncio.Semaphore(settings.max_concurrent_investigations)

    async def investigate(
        self,
        request: InvestigationRequest,
        request_id: str,
    ) -> InvestigationResponse:
        try:
            async with asyncio.timeout(self.settings.request_timeout_seconds):
                async with self.capacity:
                    return await self._investigate(request, request_id)
        except TimeoutError:
            raise AppError(
                "investigation_timeout", "Investigation exceeded its time budget.", 504
            ) from None

    async def _investigate(
        self,
        request: InvestigationRequest,
        request_id: str,
    ) -> InvestigationResponse:
        evidence = await run_in_threadpool(
            self.retriever.search,
            request.incident.retrieval_text(),
            request.top_k,
        )
        context = build_context(request.incident, evidence, self.settings.max_context_chars)
        warnings = [
            "Similarity is lexical relevance, not probability or root-cause confidence.",
            "Human review is required; no diagnostics or remediation have been executed.",
        ]
        if self.settings.provider == "mock":
            warnings.append("Mock mode uses a deterministic template, not an LLM.")
        if context.omitted_sources:
            warnings.append(
                f"Context budget omitted {context.omitted_sources} retrieved passage(s)."
            )
        analysis = None
        if context.evidence:
            analysis = await self.provider.generate(request.incident, context)
            allowed = {item.source_id for item in context.evidence}
            for finding in [*analysis.hypotheses, *analysis.recommended_checks]:
                if not set(finding.source_ids).issubset(allowed):
                    raise AppError(
                        "invalid_citation", "The model cited evidence outside its context."
                    )
        else:
            warnings.append(
                "No usable runbook evidence; gather more details or add a relevant runbook."
            )
        return InvestigationResponse(
            request_id=request_id,
            status="completed" if analysis is not None else "insufficient_evidence",
            provider=self.settings.provider,
            generation_mode="deterministic_template" if self.settings.provider == "mock" else "llm",
            analysis=analysis,
            evidence=context.evidence,
            warnings=warnings,
        )
