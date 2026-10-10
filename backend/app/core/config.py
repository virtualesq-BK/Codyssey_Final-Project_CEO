from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 프로젝트 루트의 .env를 절대 경로로 탐색 (backend/app/core/ → 3단계 상위)
_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILE = _ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

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

    # 외부 API 키 — evidence_retriever 에서 사용
    naver_client_id: str = ""
    naver_client_secret: str = ""
    kosis_api_key: str = ""
    kipris_api_key: str = ""
    data_go_kr_service_key: str = ""


settings = Settings()
