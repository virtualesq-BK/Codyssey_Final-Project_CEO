"""
B팀 RAG(bizrag · Pinecone 시맨틱 검색) → 상세분석 근거 수집기 (EvidenceRetriever 규약)

providers.py/bizrag_adapters.py(A)는 그대로 두고, 상세분석 작업(analyze_jobs)에서만 이 다리를 쓴다.
- bizrag는 backend/rag 아래 별도 패키지라 import 경로를 더해 주고, 루트 .env의 Pinecone·임베딩 설정을 넘긴다
- Pinecone 결과의 본문은 metadata.text 에 있다 (adapters의 _to_evidence는 chunk/content만 읽어 비게 됨)
- 지금 적재된 자료(통계표 목록·소비자 피해구제 등)는 아이템과 무관한 결과가 상위에 올 때가 많아,
  유사도 하한 + 검색어 핵심 단어 포함 여부로 걸러 관련 있는 것만 근거로 넘긴다
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

from app.core.schemas import Evidence

logger = logging.getLogger(__name__)

RAG_DIR = Path(__file__).resolve().parents[2] / "rag"
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
ENV_KEYS = ("PINECONE_API_KEY", "PINECONE_INDEX_NAME", "PINECONE_NAMESPACE", "PINECONE_CLOUD", "PINECONE_REGION", "EMBEDDING_PROVIDER", "EMBEDDING_MODEL")

MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.35"))
MAX_PER_QUERY = int(os.getenv("RAG_MAX_PER_QUERY", "4"))
AGENT_PREFIX = re.compile(r"^[A-Za-z]+Agent\s+")
STOPWORDS = {"창업", "사업", "운영", "서비스", "전국", "통계", "시장", "규모", "성장률", "소비자", "트렌드", "정부지원", "창업지원사업", "관련", "있는", "위한", "하는", "있음"}


def _short_query(query: str) -> str:
    """에이전트가 넘기는 긴 검색어(에이전트명 + 프로필 전문)를 앞쪽 핵심만 남긴다"""
    q = AGENT_PREFIX.sub("", query).replace("\n", " ")
    q = re.sub(r"[·•\-–—(),:/]", " ", q)
    return " ".join(q.split()[:12])


def _keywords(query: str) -> list[str]:
    return [w for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", query) if w not in STOPWORDS][:10]


def relevant(hit: dict[str, Any], keywords: list[str]) -> bool:
    """유사도 하한을 넘고, 제목·본문에 검색어 핵심 단어가 하나라도 있어야 근거로 쓴다"""
    score = hit.get("score")
    if not isinstance(score, (int, float)) or score < MIN_SCORE:
        return False
    hay = f"{hit.get('title') or ''} {hit.get('text') or ''}"
    return any(k in hay for k in keywords)


def to_evidence(hit: dict[str, Any]) -> Evidence:
    source = hit.get("source") or "bizrag"
    return Evidence(
        title=str(hit.get("title") or source)[:120],
        source=f"RAG · {source}",
        url=hit.get("url") or None,
        content=str(hit.get("text") or "")[:800],
        confidence=float(hit["score"]) if isinstance(hit.get("score"), (int, float)) else 0.5,
    )


class BizragRetriever:
    def __init__(self, knowledge: Any):
        self._k = knowledge

    async def __call__(self, query: str) -> list[Evidence]:
        q = _short_query(query)
        keys = _keywords(q)
        store = self._k.pinecone
        if not store or not q:
            return []
        try:
            hits = await asyncio.to_thread(store.search, q, None, None, MAX_PER_QUERY * 3)
        except Exception as exc:  # noqa: BLE001 — 근거 수집 실패는 분석을 멈추지 않는다
            logger.warning("[RAG] 검색 실패 q=%r: %s", q[:40], exc)
            return []
        kept = [to_evidence(h) for h in hits if relevant(h, keys)][:MAX_PER_QUERY]
        logger.info("[RAG] %r → %d건 중 %d건 사용", q[:30], len(hits), len(kept))
        return kept


_retriever: Optional[BizragRetriever] = None
_tried = False


def build_bizrag_retriever() -> Optional[BizragRetriever]:
    """Pinecone 키가 있으면 bizrag 검색기를 한 번만 만든다 (임베딩 모델 로딩이 무거워서). RAG_ENABLED=false로 끌 수 있다"""
    global _retriever, _tried
    if _tried:
        return _retriever
    _tried = True
    if os.getenv("RAG_ENABLED", "true").lower() in ("0", "false", "no"):
        return None
    try:
        from dotenv import dotenv_values

        env = dotenv_values(ENV_FILE) if ENV_FILE.exists() else {}
        for k in ENV_KEYS:
            if env.get(k) and not os.environ.get(k):
                os.environ[k] = env[k]  # bizrag App은 os.environ과 rag/.env만 읽는다
        if not os.environ.get("PINECONE_API_KEY"):
            logger.info("[RAG] PINECONE_API_KEY 없음 — RAG 근거 비활성화")
            return None
        if str(RAG_DIR) not in sys.path:
            sys.path.insert(0, str(RAG_DIR))
        from bizrag.app import App  # type: ignore[import]
        from bizrag.knowledge import Knowledge  # type: ignore[import]

        _retriever = BizragRetriever(Knowledge(App(root=RAG_DIR)))
        logger.info("[RAG] bizrag Pinecone 연결")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[RAG] bizrag 연결 실패 — RAG 근거 없이 진행: %s", exc)
        _retriever = None
    return _retriever
