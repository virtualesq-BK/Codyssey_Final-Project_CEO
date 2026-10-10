"""
FastAPI routes
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.orchestrator import Orchestrator
from app.core.schemas import BusinessIdea, BusinessStage, UserProfile, WorkflowResult
from app.rag.providers import get_adapters

router = APIRouter(prefix="/api/v1")


class AnalyzeRequest(BaseModel):
    title: str
    problem: str
    customer: str
    solution: str
    industry: str
    location: str = "전국"
    business_stage: BusinessStage = BusinessStage.IDEA
    user_profile: UserProfile | None = None


class AnalyzeResponse(BaseModel):
    idea_id: str
    workflow_result: WorkflowResult


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    idea = BusinessIdea(
        idea_id=str(uuid.uuid4()),
        **req.model_dump(),
    )
    adapters = get_adapters()
    orchestrator = Orchestrator(
        evidence_retriever=adapters.evidence_retriever if adapters else None,
        benchmark_provider=adapters.benchmark_provider if adapters else None,
        risk_evidence_provider=adapters.risk_evidence_provider if adapters else None,
    )
    try:
        result = await orchestrator.run(idea)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return AnalyzeResponse(idea_id=idea.idea_id, workflow_result=result)


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "나도사장 API"}
