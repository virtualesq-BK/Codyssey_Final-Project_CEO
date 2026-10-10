"""BizragAdapters 단위 테스트 — bizrag 미설치 환경에서도 동작한다."""
from __future__ import annotations

import pytest

from app.core.schemas import BusinessIdea, Evidence
from app.financial.benchmark import BenchmarkProvider
from app.rag.bizrag_adapters import BizragAdapters, _extract_numeric, _to_evidence
from app.risk.evidence import RiskEvidenceProvider
from app.risk.taxonomy import RiskCategory


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def idea():
    return BusinessIdea(
        idea_id="test-001",
        title="구독형 반려동물 용품 배송",
        problem="바쁜 직장인이 반려동물 용품을 매번 구매하기 불편하다",
        customer="20~40대 직장인 반려동물 보호자",
        solution="월정액 구독으로 반려동물 맞춤 용품 정기 배송",
        industry="반려동물",
        location="서울",
    )


class _FakeKnowledge:
    """bizrag.Knowledge 최소 구현체 — 네트워크·DB 없이 테스트용."""

    def search_knowledge(self, query: str, limit: int = 8) -> list[dict]:
        return [
            {
                "title": f"테스트 문서: {query[:20]}",
                "source": "테스트",
                "url": "https://example.com",
                "retrieved_at": "2026-01-01T00:00:00",
                "chunk": "반려동물 시장 규모는 약 3조 원이며 연 10% 성장 중이다.",
                "score": 0.75,
            }
        ]


@pytest.fixture
def adapters():
    return BizragAdapters(_FakeKnowledge(), search_limit=3)


# ── _to_evidence ─────────────────────────────────────────────────────────

def test_to_evidence_full_row():
    row = {
        "title": "시장 분석 보고서",
        "source": "KOSIS",
        "url": "https://kosis.kr/test",
        "retrieved_at": "2026-03-15T09:00:00",
        "chunk": "국내 반려동물 시장 규모 3조 원.",
        "score": 0.8,
    }
    ev = _to_evidence(row)
    assert isinstance(ev, Evidence)
    assert ev.source == "KOSIS"
    assert ev.confidence == 0.8
    assert ev.url == "https://kosis.kr/test"


def test_to_evidence_minimal_row():
    ev = _to_evidence({"source": "naver", "content": "내용"})
    assert ev.title == "naver"
    assert ev.confidence == 0.6  # 기본값


def test_to_evidence_content_truncated():
    ev = _to_evidence({"source": "x", "chunk": "a" * 3000})
    assert len(ev.content) <= 2000


# ── _extract_numeric ──────────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("월 50만원 수준", 500_000.0),
    ("가격 29,900원", 29_900.0),
    ("이탈률 5%", 0.05),
    ("성장률 200%", None),   # 100% 초과 → None (이탈률로 사용 불가)
    ("관련 정보 없음", None),
])
def test_extract_numeric(text, expected):
    assert _extract_numeric(text) == expected


# ── BizragAdapters ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_evidence_retriever_returns_list(adapters, idea):
    query = f"반려동물 {idea.industry} {idea.location}"
    results = await adapters.evidence_retriever(query)
    assert isinstance(results, list)
    assert all(isinstance(e, Evidence) for e in results)


@pytest.mark.asyncio
async def test_evidence_retriever_on_error(idea):
    class _BrokenKnowledge:
        def search_knowledge(self, *a, **kw):
            raise RuntimeError("DB 연결 실패")

    adapters = BizragAdapters(_BrokenKnowledge())
    result = await adapters.evidence_retriever("테스트")
    assert result == []  # 예외 → 빈 리스트, 터지지 않음


@pytest.mark.asyncio
async def test_get_benchmarks_returns_list(adapters, idea):
    results = await adapters.get_benchmarks(idea, ["price", "fixed_cost"])
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_get_evidence_returns_list(adapters, idea):
    results = await adapters.get_evidence(idea, RiskCategory.MARKET)
    assert isinstance(results, list)
    assert all(isinstance(e, Evidence) for e in results)


# ── Protocol 적합성 ────────────────────────────────────────────────────────

def test_benchmark_provider_protocol(adapters):
    assert isinstance(adapters.benchmark_provider, BenchmarkProvider)


def test_risk_evidence_provider_protocol(adapters):
    assert isinstance(adapters.risk_evidence_provider, RiskEvidenceProvider)
