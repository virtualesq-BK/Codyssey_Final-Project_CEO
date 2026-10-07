"""
FastAPI routes
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.orchestrator import Orchestrator
from app.core.schemas import BusinessIdea, BusinessStage, UserProfile, WorkflowResult

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
    orchestrator = Orchestrator()
    try:
        result = await orchestrator.run(idea)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return AnalyzeResponse(idea_id=idea.idea_id, workflow_result=result)


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "나도사장 API"}
