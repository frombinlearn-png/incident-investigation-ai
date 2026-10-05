from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
SourceId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9-]+#[0-9]{3,}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Incident(StrictModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=6000)
    service: str = Field(default="unknown", min_length=1, max_length=100)
    severity: Literal["SEV1", "SEV2", "SEV3", "SEV4"] = "SEV3"
    signals: list[ShortText] = Field(default_factory=list, max_length=20)

    def retrieval_text(self) -> str:
        return "\n".join([self.title, self.description, self.service, *self.signals])


class InvestigationRequest(StrictModel):
    incident: Incident
    top_k: int = Field(default=3, ge=1, le=5)


class SearchRequest(StrictModel):
    query: str = Field(min_length=3, max_length=6000)
    top_k: int = Field(default=3, ge=1, le=5)


class Evidence(StrictModel):
    source_id: SourceId
    runbook_id: str
    title: str
    section: str
    text: str
    score: float = Field(ge=0, le=1)


class CitedFinding(StrictModel):
    text: str = Field(min_length=1, max_length=1200)
    source_ids: list[SourceId] = Field(min_length=1, max_length=5)


class Analysis(StrictModel):
    summary: str = Field(min_length=1, max_length=1600)
    hypotheses: list[CitedFinding] = Field(min_length=1, max_length=5)
    recommended_checks: list[CitedFinding] = Field(min_length=1, max_length=8)
    missing_information: list[ShortText] = Field(min_length=1, max_length=8)


class InvestigationResponse(StrictModel):
    request_id: str
    status: Literal["completed", "insufficient_evidence"]
    provider: Literal["mock", "openai"]
    generation_mode: Literal["deterministic_template", "llm"]
    analysis: Analysis | None
    evidence: list[Evidence]
    warnings: list[str]


class SearchResponse(StrictModel):
    evidence: list[Evidence]
    embedding_method: Literal["tfidf"] = "tfidf"


class RunbookInfo(StrictModel):
    runbook_id: str
    title: str
    chunks: int


class HealthResponse(StrictModel):
    status: Literal["ok"] = "ok"
    provider: Literal["mock", "openai"]
    indexed_chunks: int
    embedding_method: Literal["tfidf"] = "tfidf"


class ErrorDetail(StrictModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(StrictModel):
    error: ErrorDetail
