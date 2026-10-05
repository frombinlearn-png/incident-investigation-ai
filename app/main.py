import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException

from app.config import Settings
from app.errors import AppError
from app.logging_config import configure_logging
from app.middleware import RequestMiddleware, error_response
from app.models import (
    ErrorResponse,
    HealthResponse,
    InvestigationRequest,
    InvestigationResponse,
    RunbookInfo,
    SearchRequest,
    SearchResponse,
)
from app.services.investigation_service import InvestigationService
from app.services.llm_service import AnalysisProvider, MockProvider, OpenAIProvider
from app.services.retrieval_service import Retriever, load_chunks

logger = logging.getLogger("incident_ai")


def create_app(
    settings: Settings | None = None,
    provider: AnalysisProvider | None = None,
) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        configure_logging(settings.log_level)
        chunks = await run_in_threadpool(load_chunks, settings.runbook_dir)
        retriever = await run_in_threadpool(Retriever, chunks, settings.min_similarity)
        headers = {}
        if settings.provider == "openai" and settings.openai_api_key:
            headers["Authorization"] = f"Bearer {settings.openai_api_key.get_secret_value()}"
        async with httpx.AsyncClient(
            base_url="https://api.openai.com/v1/",
            headers=headers,
            timeout=settings.provider_timeout_seconds,
            follow_redirects=False,
            limits=httpx.Limits(max_connections=settings.max_concurrent_investigations),
        ) as client:
            selected_provider = provider or (
                MockProvider() if settings.provider == "mock" else OpenAIProvider(client, settings)
            )
            application.state.retriever = retriever
            application.state.investigator = InvestigationService(
                retriever, selected_provider, settings
            )
            logger.info("application_ready")
            yield

    application = FastAPI(
        title="Incident Investigation AI",
        version="0.1.0",
        lifespan=lifespan,
        description="Evidence-first triage demo. Local TF-IDF retrieval; mock or OpenAI synthesis.",
        responses={status: {"model": ErrorResponse} for status in (413, 422, 500, 502, 503, 504)},
    )
    application.add_middleware(RequestMiddleware, max_request_bytes=settings.max_request_bytes)

    @application.exception_handler(AppError)
    async def app_error(request: Request, error: AppError):
        logger.warning(
            "application_error",
            extra={"request_id": request.state.request_id, "error_code": error.code},
        )
        return error_response(
            error.code, error.message, request.state.request_id, error.status_code
        )

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError):
        return error_response(
            "invalid_request",
            "Request does not match the API schema. See /docs.",
            request.state.request_id,
            422,
        )

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException):
        return error_response(
            "http_error",
            "The requested operation is unavailable.",
            request.state.request_id,
            error.status_code,
        )

    @application.get("/health", response_model=HealthResponse, tags=["operations"])
    async def health(request: Request):
        return HealthResponse(
            provider=settings.provider, indexed_chunks=len(request.app.state.retriever.chunks)
        )

    @application.get("/v1/runbooks", response_model=list[RunbookInfo], tags=["knowledge"])
    async def runbooks(request: Request):
        return request.app.state.retriever.list_runbooks()

    @application.post("/v1/search", response_model=SearchResponse, tags=["knowledge"])
    async def search(body: SearchRequest, request: Request):
        evidence = await run_in_threadpool(
            request.app.state.retriever.search, body.query, body.top_k
        )
        return SearchResponse(evidence=evidence)

    @application.post("/v1/investigations", response_model=InvestigationResponse, tags=["triage"])
    async def investigate(body: InvestigationRequest, request: Request):
        return await request.app.state.investigator.investigate(body, request.state.request_id)

    return application
