from functools import lru_cache
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SDP_", extra="ignore")

    app_name: str = "Synthetic Data Platform"
    version: str = "0.1.0"
    cors_origins: list[str] = ["http://localhost:8501", "http://localhost:3000"]
    llm_model: str = "gpt-4o-mini"
    # pydantic-settings doesn't export to os.environ, so the AI layer passes this to LiteLLM explicitly.
    openai_api_key: str | None = Field(
        default=None, validation_alias=AliasChoices("SDP_OPENAI_API_KEY", "OPENAI_API_KEY")
    )

    @property
    def llm_configured(self) -> bool:
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
    