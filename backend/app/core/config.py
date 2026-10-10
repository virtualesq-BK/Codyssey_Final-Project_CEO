from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    openai_base_url: str = ""   # 커스텀 엔드포인트 (프록시 등). 빈 문자열이면 기본값 사용
    anthropic_api_key: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./nadosajang.db"

    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # bizrag (B팀 RAG) — 값이 없으면 NullProvider 기본값으로 동작
    bizrag_db_path: str = ""


settings = Settings()
