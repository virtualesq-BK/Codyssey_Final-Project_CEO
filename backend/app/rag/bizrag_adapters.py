"""
bizrag ↔ Agent 인터페이스 어댑터

B팀의 bizrag.Knowledge가 반환하는 list[dict]를
A팀 Agent 인터페이스(Evidence, Benchmark)로 변환한다.

사용 예시:
    from backend.rag.bizrag.knowledge import Knowledge
    from app.rag.bizrag_adapters import BizragAdapters

    knowledge = Knowledge("backend/rag/data/knowledge.db")
    adapters = BizragAdapters(knowledge)

    orchestrator = Orchestrator(
        evidence_retriever=adapters.evidence_retriever,
        benchmark_provider=adapters.benchmark_provider,
        risk_evidence_provider=adapters.risk_evidence_provider,
    )
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.core.schemas import BusinessIdea, Evidence
from app.financial.benchmark import Benchmark, BenchmarkProvider
from app.financial.calculator import FinancialInputs
from app.risk.evidence import RiskEvidenceProvider
from app.risk.taxonomy import RiskCategory

logger = logging.getLogger(__name__)

# bizrag search_knowledge() 결과 dict → Evidence 변환 시 confidence 기본값
_DEFAULT_CONFIDENCE = 0.6

# FinancialInputs 필드명 → bizrag 검색 키워드 매핑
# 산업 평균 benchmark를 검색할 때 사용한다
_BENCHMARK_KEYWORDS: dict[str, list[str]] = {
    "price": ["가격", "요금", "월정액", "구독료"],
    "variable_cost_per_unit": ["변동비", "원가", "재료비", "서비스 비용"],
    "fixed_cost": ["고정비", "임대료", "인건비", "운영비"],
    "acquisition_cost": ["고객 획득 비용", "마케팅 비용", "광고비", "CAC"],
    "monthly_churn_rate": ["이탈률", "해지율", "churn"],
}

# RiskCategory → bizrag 검색 키워드 매핑
_RISK_KEYWORDS: dict[RiskCategory, list[str]] = {
    RiskCategory.MARKET: ["시장 규모", "시장 성장률", "소비자 트렌드"],
    RiskCategory.COMPETITION: ["경쟁사", "시장 점유율", "경쟁 현황"],
    RiskCategory.TECHNOLOGY: ["기술 특허", "기술 규제", "기술 트렌드"],
    RiskCategory.FINANCIAL: ["재무 리스크", "자금 조달", "투자 현황"],
    RiskCategory.REGULATORY: ["법령", "규제", "인허가", "고시"],
    RiskCategory.EXECUTION: ["창업 실패", "운영 리스크", "인력 채용"],
}


def _to_evidence(row: dict[str, Any]) -> Evidence:
    """bizrag search_knowledge() 결과 dict 한 행을 Evidence로 변환한다."""
    published_at: datetime | None = None
    raw_date = row.get("retrieved_at") or row.get("published_at")
    if isinstance(raw_date, str):
        try:
            published_at = datetime.fromisoformat(raw_date)
        except ValueError:
            pass

    content = row.get("chunk") or row.get("content") or row.get("summary") or ""
    title = row.get("title") or row.get("doc_title") or row.get("source", "출처 미상")
    source = row.get("source") or "bizrag"
    url = row.get("url") or row.get("link")

    confidence_raw = row.get("score")
    if isinstance(confidence_raw, (int, float)) and 0.0 <= float(confidence_raw) <= 1.0:
        confidence = float(confidence_raw)
    else:
        confidence = _DEFAULT_CONFIDENCE

    return Evidence(
        title=str(title),
        source=str(source),
        url=str(url) if url else None,
        published_at=published_at,
        content=str(content)[:2000],  # LLM 컨텍스트 길이 제한
        confidence=confidence,
    )


class BizragAdapters:
    """
    bizrag.Knowledge 인스턴스를 받아 세 가지 Agent 인터페이스를 제공한다.

    knowledge: bizrag.Knowledge 인스턴스 (타입 힌트는 Any — bizrag 미설치 환경 호환)
    search_limit: search_knowledge() 호출당 최대 결과 수
    """

    def __init__(self, knowledge: Any, search_limit: int = 6) -> None:
        self._k = knowledge
        self._limit = search_limit

    # ── EvidenceRetriever ────────────────────────────────────────────────
    # CustomerAgent / BusinessModelAgent 가 사용하는 callable
    # 시그니처: async (query: str) -> list[Evidence]

    async def evidence_retriever(self, query: str) -> list[Evidence]:
        """query 문자열로 bizrag를 검색해 Evidence 리스트를 반환한다."""
        try:
            rows: list[dict] = self._k.search_knowledge(query, limit=self._limit)
            return [_to_evidence(r) for r in rows]
        except Exception as exc:
            logger.warning("[BizragAdapters.evidence_retriever] 검색 실패 query=%r: %s", query, exc)
            return []

    # ── BenchmarkProvider ────────────────────────────────────────────────
    # FinancialAgent 가 사용하는 Protocol 구현
    # 시그니처: async get_benchmarks(idea, variables) -> list[Benchmark]

    async def get_benchmarks(
        self, idea: BusinessIdea, variables: list[str]
    ) -> list[Benchmark]:
        """부족한 재무 변수(variables)에 대한 산업 평균 benchmark를 반환한다."""
        results: list[Benchmark] = []
        for var in variables:
            keywords = _BENCHMARK_KEYWORDS.get(var, [var])
            query = f"{idea.industry} {idea.location} {' '.join(keywords)}"
            try:
                rows: list[dict] = self._k.search_knowledge(query, limit=3)
                for row in rows:
                    value = _extract_numeric(row.get("content") or row.get("chunk") or "")
                    if value is None:
                        continue
                    results.append(Benchmark(
                        variable=var,
                        value=value,
                        evidence=_to_evidence(row),
                    ))
                    break  # 변수당 첫 번째 유효한 수치만 사용
            except Exception as exc:
                logger.warning(
                    "[BizragAdapters.get_benchmarks] 실패 var=%s: %s", var, exc
                )
        return results

    # ── RiskEvidenceProvider ─────────────────────────────────────────────
    # RiskAgent 가 사용하는 Protocol 구현
    # 시그니처: async get_evidence(idea, category) -> list[Evidence]

    async def get_evidence(
        self, idea: BusinessIdea, category: RiskCategory
    ) -> list[Evidence]:
        """risk category에 맞는 근거를 bizrag에서 검색해 반환한다."""
        keywords = _RISK_KEYWORDS.get(category, [category.value])
        query = f"{idea.industry} {idea.location} {' '.join(keywords)}"
        try:
            rows: list[dict] = self._k.search_knowledge(query, limit=self._limit)
            return [_to_evidence(r) for r in rows]
        except Exception as exc:
            logger.warning(
                "[BizragAdapters.get_evidence] 실패 category=%s: %s", category, exc
            )
            return []

    # ── Orchestrator 주입용 프로퍼티 ─────────────────────────────────────
    # Orchestrator(evidence_retriever=adapters.evidence_retriever, ...) 형태로 사용

    @property
    def benchmark_provider(self) -> "BizragAdapters":
        """BenchmarkProvider Protocol을 만족하는 self 반환 (get_benchmarks 메서드 포함)."""
        return self

    @property
    def risk_evidence_provider(self) -> "BizragAdapters":
        """RiskEvidenceProvider Protocol을 만족하는 self 반환 (get_evidence 메서드 포함)."""
        return self


def _extract_numeric(text: str) -> float | None:
    """
    텍스트에서 첫 번째 숫자(원 단위 또는 % 등)를 추출한다.
    단위 변환은 하지 않으며, 원 단위 정수 또는 소수만 반환한다.
    추출 실패 시 None 반환 — benchmark에 근거 없는 수치를 넣지 않는다.
    """
    import re
    # 숫자 + 단위 패턴: 만원, 원, % 등 포함 숫자를 우선 추출
    patterns = [
        r"(\d[\d,]*)\s*만\s*원",   # X만원 → X * 10000
        r"(\d[\d,]*)\s*원",         # X원
        r"(\d[\d,]*\.?\d*)\s*%",    # X%  → 0.X (0~1 스케일)
        r"(\d[\d,]*\.?\d*)",        # 그 외 숫자
    ]
    for i, pat in enumerate(patterns):
        m = re.search(pat, text.replace(" ", ""))
        if m:
            raw = float(m.group(1).replace(",", ""))
            if i == 0:      # 만원
                return raw * 10_000
            if i == 2:      # %
                value = raw / 100.0
                return value if 0.0 < value <= 1.0 else None
            return raw
    return None
