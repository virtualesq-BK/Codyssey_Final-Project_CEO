"""
RAG provider 싱글턴 관리

앱 시작 시 BIZRAG_DB_PATH 환경변수를 읽어 BizragAdapters를 초기화한다.
경로가 없거나 bizrag 미설치 시 Null* 기본값으로 조용히 폴백한다.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_adapters: Optional["BizragAdapters"] = None  # noqa: F821


def init_rag_providers(db_path: str) -> None:
    """
    FastAPI lifespan에서 호출한다.
    db_path가 빈 문자열이거나 파일이 없으면 초기화를 건너뛴다.
    """
    global _adapters

    if not db_path:
        logger.info("[RAG] BIZRAG_DB_PATH 미설정 — NullProvider로 동작합니다")
        return

    path = Path(db_path)
    if not path.exists():
        logger.warning("[RAG] bizrag DB 파일 없음: %s — NullProvider로 동작합니다", path)
        return

    try:
        from bizrag.knowledge import Knowledge  # type: ignore[import]
        from app.rag.bizrag_adapters import BizragAdapters

        knowledge = Knowledge(str(path))
        _adapters = BizragAdapters(knowledge)
        logger.info("[RAG] bizrag 연결 완료: %s", path)
    except ModuleNotFoundError:
        logger.warning("[RAG] bizrag 패키지 미설치 — NullProvider로 동작합니다")
    except Exception as exc:
        logger.error("[RAG] bizrag 초기화 실패: %s — NullProvider로 동작합니다", exc)


def get_adapters() -> Optional["BizragAdapters"]:  # noqa: F821
    return _adapters
