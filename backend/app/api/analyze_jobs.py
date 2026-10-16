"""
상세분석(진단) 백그라운드 작업 API
POST /analyze 는 2~3분 동안 요청을 붙잡고 있어서, 화면을 떠나면 결과를 잃는다.
여기서는 작업을 서버에서 따로 돌리고, 프론트는 짧은 요청으로 진행 상황·결과를 받아 간다.

- 작업 상태는 메모리에만 둔다 (서버가 재시작되면 사라짐 → 프론트는 404를 '끊김'으로 처리)
- 에이전트별 진행은 Orchestrator(A 소유)를 고치지 않고, 이 작업의 에이전트 인스턴스 run/decide만 감싸서 기록한다
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.orchestrator import Orchestrator
from app.api.routes import AnalyzeRequest, AnalyzeResponse
from app.core.schemas import BusinessIdea
from app.rag.external_retrievers import build_external_retriever
from app.rag.providers import get_adapters
from app.rag.bizrag_bridge import build_bizrag_retriever
from app.rag.web_search_retriever import CombinedRetriever, build_web_search_retriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analyze/jobs")

JOB_TTL_SEC = 2 * 60 * 60
# 웹검색은 한 번에 10~25초 걸려, 에이전트의 기본 근거 대기(10초)를 늘린다
RETRIEVAL_TIMEOUT_SEC = 60.0
STAGES = ["MarketAgent", "CustomerAgent", "CompetitorAgent", "BusinessModelAgent", "FinancialAgent", "RiskAgent", "DecisionAgent"]

StageState = Literal["waiting", "running", "done", "failed"]


class StageProgress(BaseModel):
    state: StageState = "waiting"
    status: Optional[str] = None  # 에이전트 결과 상태 (success / partial / failed …)
    summary: str = ""
    evidence: int = 0
    elapsed_ms: int = 0


class JobState(BaseModel):
    job_id: str
    status: Literal["running", "done", "failed"] = "running"
    started_at: str
    finished_at: Optional[str] = None
    stages: dict[str, StageProgress]
    result: Optional[AnalyzeResponse] = None
    error: Optional[str] = None


class JobCreated(BaseModel):
    job_id: str


_jobs: dict[str, tuple[float, JobState]] = {}
# 작업 태스크가 GC되지 않게 잡아 둔다
_tasks: set[asyncio.Task] = set()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cleanup() -> None:
    cutoff = time.time() - JOB_TTL_SEC
    for jid in [j for j, (t, _) in _jobs.items() if t < cutoff]:
        _jobs.pop(jid, None)


def _track(job: JobState, name: str, obj: object, method: str) -> None:
    """에이전트 인스턴스의 run(또는 decide)을 감싸 시작·끝을 기록한다 (클래스·isinstance는 그대로)"""
    original = getattr(obj, method)

    async def wrapped(*args, **kwargs):
        stage = job.stages[name]
        stage.state = "running"
        t0 = time.monotonic()
        try:
            res = await original(*args, **kwargs)
        except Exception:
            stage.state = "failed"
            stage.elapsed_ms = int((time.monotonic() - t0) * 1000)
            raise
        stage.elapsed_ms = int((time.monotonic() - t0) * 1000)
        status = getattr(res, "status", None)
        stage.status = getattr(status, "value", status) if status is not None else "success"
        stage.state = "failed" if stage.status == "failed" else "done"
        stage.summary = (getattr(res, "summary", "") or "").split(" / ")[0][:120]
        stage.evidence = len(getattr(res, "evidence", []) or [])
        return res

    setattr(obj, method, wrapped)


async def _run(job: JobState, req: AnalyzeRequest) -> None:
    idea = BusinessIdea(idea_id=str(uuid.uuid4()), **req.model_dump())
    adapters = get_adapters()
    # 근거 = 공공 API 직접 검색(KOSIS·KIPRIS) + B팀 RAG(Pinecone) + 웹검색, 셋 다 합친다
    base_retriever = adapters.evidence_retriever if adapters else build_external_retriever()
    rag = await asyncio.to_thread(build_bizrag_retriever)  # 첫 호출은 임베딩 모델 로딩으로 느림
    web = build_web_search_retriever()
    extra = [r for r in (rag, web) if r]
    orchestrator = Orchestrator(
        evidence_retriever=CombinedRetriever(base_retriever, *extra) if extra else base_retriever,
        benchmark_provider=adapters.benchmark_provider if adapters else None,
        risk_evidence_provider=adapters.risk_evidence_provider if adapters else None,
    )
    for name, agent in orchestrator.agents.items():
        if extra and hasattr(agent, "retrieval_timeout_sec"):
            agent.retrieval_timeout_sec = RETRIEVAL_TIMEOUT_SEC
        if name in job.stages:
            _track(job, name, agent, "run")
    _track(job, "DecisionAgent", orchestrator._decision_agent, "decide")
    try:
        result = await orchestrator.run(idea)
        job.result = AnalyzeResponse(idea_id=idea.idea_id, workflow_result=result)
        job.status = "done"
    except Exception as exc:  # noqa: BLE001 — 어떤 실패든 작업 상태로 돌려준다
        logger.error("[analyze job %s] 실패: %s", job.job_id, exc)
        job.status = "failed"
        job.error = str(exc)
    job.finished_at = _now()


@router.post("", response_model=JobCreated)
async def start_job(req: AnalyzeRequest) -> JobCreated:
    _cleanup()
    job = JobState(job_id=str(uuid.uuid4()), started_at=_now(), stages={s: StageProgress() for s in STAGES})
    _jobs[job.job_id] = (time.time(), job)
    task = asyncio.create_task(_run(job, req))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return JobCreated(job_id=job.job_id)


@router.get("/{job_id}", response_model=JobState)
async def get_job(job_id: str) -> JobState:
    hit = _jobs.get(job_id)
    if not hit:
        raise HTTPException(status_code=404, detail="분석 작업을 찾을 수 없어요. 서버가 다시 시작돼 끊겼을 수 있어요.")
    return hit[1]
