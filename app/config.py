from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    provider: Literal["mock", "openai"] = "mock"
    openai_api_key: SecretStr | None = None
    openai_model: str = Field(default="gpt-4o-mini", min_length=1, max_length=100)
    runbook_dir: Path = Path(__file__).parent / "data" / "runbooks"
    min_similarity: float = Field(default=0.12, gt=0, le=1)
    max_context_chars: int = Field(default=12000, ge=1024, le=32000)
    request_timeout_seconds: float = Field(default=30, gt=0, le=120)
    provider_timeout_seconds: float = Field(default=10, gt=0, le=60)
    provider_max_attempts: int = Field(default=2, ge=1, le=3)
    max_concurrent_investigations: int = Field(default=8, ge=1, le=64)
    max_request_bytes: int = Field(default=65536, ge=1024, le=1048576)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @model_validator(mode="after")
    def validate_provider(self) -> "Settings":
        if self.provider == "openai" and (
            self.openai_api_key is None or not self.openai_api_key.get_secret_value().strip()
        ):
            raise ValueError("OPENAI_API_KEY is required when PROVIDER=openai")
        return self
