import asyncio

import pytest

from app.api import analyze_jobs
from app.api.analyze_jobs import AnalyzeJobRequest
from app.rag.user_validation import (
    UserValidationRetriever,
    UserValidationRiskProvider,
    ValidationInput,
    strength,
    to_evidence,
)
from app.risk.taxonomy import RiskCategory


def v(**kw):
    base = dict(hypothesis="교사가 학습지 제작에 주 3시간 이상 쓴다", result="supported", method="고객 인터뷰", sample_size=12)
    base.update(kw)
    return ValidationInput(**base)


def test_evidence_marks_self_report_and_result():
    ev = to_evidence(v(metric="12명 중 9명"))
    assert ev.source.startswith("창업가 검증 · 고객 인터뷰 12명")
    assert "검증됨" in ev.content and "12명 중 9명" in ev.content and "자가 보고" in ev.content


def test_refuted_is_passed_through():
    ev = to_evidence(v(result="refuted"))
    assert "반증됨" in ev.content


def test_strength_depends_on_method_and_sample():
    small = strength(v(sample_size=3))
    big_sale = strength(v(method="판매 테스트", sample_size=120))
    assert small < strength(v()) < big_sale
    assert 0.2 <= small and big_sale <= 0.8


@pytest.mark.asyncio
async def test_retriever_routes_by_area():
    r = UserValidationRetriever([
        v(area="CustomerAgent"),
        v(area="MarketAgent", hypothesis="시장 가설"),
        v(area="FinancialAgent", hypothesis="가격 가설"),
    ])
    customer = await r("CustomerAgent 교육 교사 전국 문제")
    market = await r("교육 전국 시장 규모 성장률 통계")
    bm = await r("BusinessModelAgent 교육 교사")
    assert [e.title for e in customer] == ["창업가 검증 · 교사가 학습지 제작에 주 3시간 이상 쓴다"]
    assert [e.title for e in market] == ["창업가 검증 · 시장 가설"]
    # 재무 검증은 수익 구조 쪽 근거로
    assert [e.title for e in bm] == ["창업가 검증 · 가격 가설"]


@pytest.mark.asyncio
async def test_risk_provider_adds_once_to_execution():
    p = UserValidationRiskProvider(None, [v(area="RiskAgent", hypothesis="규제 문제 없음")])
    assert await p.get_evidence(None, RiskCategory.MARKET) == []
    assert len(await p.get_evidence(None, RiskCategory.EXECUTION)) == 1


@pytest.mark.asyncio
async def test_job_accepts_validations(monkeypatch):
    seen = {}

    class FakeOrchestrator:
        def __init__(self, evidence_retriever=None, benchmark_provider=None, risk_evidence_provider=None):
            seen["retriever"] = evidence_retriever
            self.agents = {}
            self._decision_agent = type("D", (), {"decide": staticmethod(lambda idea: asyncio.sleep(0))})()

        async def run(self, idea):
            from app.core.schemas import WorkflowResult, AgentStatus

            seen["evidence"] = await seen["retriever"]("CustomerAgent x")
            return WorkflowResult(idea_id=idea.idea_id, status=AgentStatus.PARTIAL)

    monkeypatch.setattr(analyze_jobs, "Orchestrator", FakeOrchestrator)
    monkeypatch.setattr(analyze_jobs, "get_adapters", lambda: None)
    monkeypatch.setattr(analyze_jobs, "build_external_retriever", lambda: None)
    monkeypatch.setattr(analyze_jobs, "build_web_search_retriever", lambda: None)
    monkeypatch.setattr(analyze_jobs, "build_bizrag_retriever", lambda: None)
    req = AnalyzeJobRequest(
        title="t", problem="p", customer="c", solution="s", industry="i",
        validations=[{"hypothesis": "h", "area": "CustomerAgent", "result": "supported", "method": "설문조사", "sample_size": 40}],
    )
    created = await analyze_jobs.start_job(req)
    for _ in range(50):
        job = await analyze_jobs.get_job(created.job_id)
        if job.status != "running":
            break
        await asyncio.sleep(0.01)
    assert job.status == "done", job.error
    assert [e.source for e in seen["evidence"]] == ["창업가 검증 · 설문조사 40명"]
