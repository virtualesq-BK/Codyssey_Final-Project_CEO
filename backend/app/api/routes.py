"""
FastAPI routes
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.agents.orchestrator import Orchestrator
from app.core.schemas import BusinessIdea, BusinessStage, UserProfile, WorkflowResult
from app.rag.providers import get_adapters
from app.rag.external_retrievers import build_external_retriever

router = APIRouter(prefix="/api/v1")


# ── 공고 샘플 데이터 ────────────────────────────────────────────
_SAMPLE_PROGRAMS = [
    {
        "id": "P001", "title": "2024년 초기창업패키지", "organization": "중소벤처기업부",
        "category": "창업지원", "region": "전국", "deadline_status": "모집중",
        "ends_on": "2025-03-31", "starts_on": "2025-01-02",
        "target": "창업 3년 이내 기업", "body": "우수한 아이디어와 기술력을 보유한 초기창업자를 발굴·지원하여 성공적인 창업 생태계 조성",
        "detail_url": "https://www.k-startup.go.kr",
        "amount": "최대 1억원",
    },
    {
        "id": "P002", "title": "청년창업사관학교", "organization": "중소벤처기업진흥공단",
        "category": "청년창업", "region": "전국", "deadline_status": "모집중",
        "ends_on": "2025-04-30", "starts_on": "2025-02-01",
        "target": "만 39세 이하 예비창업자 및 창업 3년 이내 기업", "body": "청년 창업자에게 창업 공간, 멘토링, 사업화 자금을 패키지로 지원",
        "detail_url": "https://www.sbc.or.kr",
        "amount": "최대 1억원",
    },
    {
        "id": "P003", "title": "TIPS(민간투자주도형 기술창업지원)", "organization": "중소벤처기업부",
        "category": "기술창업", "region": "전국", "deadline_status": "모집중",
        "ends_on": "2025-12-31", "starts_on": "2025-01-01",
        "target": "기술기반 스타트업", "body": "민간 투자사가 선발·투자한 스타트업에 R&D 자금과 창업지원금을 매칭 지원",
        "detail_url": "https://www.k-startup.go.kr/tips",
        "amount": "최대 5억원",
    },
    {
        "id": "P004", "title": "서울창업허브 입주기업 모집", "organization": "서울특별시",
        "category": "공간지원", "region": "서울", "deadline_status": "모집중",
        "ends_on": "2025-05-31", "starts_on": "2025-03-01",
        "target": "서울 소재 창업 7년 이내 기업", "body": "서울창업허브 내 사무공간, 회의실, 네트워킹 공간 등 제공",
        "detail_url": "https://seoulstartuphub.com",
        "amount": "공간 무상 제공",
    },
    {
        "id": "P005", "title": "소셜벤처 성장지원 프로그램", "organization": "한국사회투자",
        "category": "소셜임팩트", "region": "전국", "deadline_status": "모집중",
        "ends_on": "2025-06-30", "starts_on": "2025-04-01",
        "target": "소셜벤처, 사회적기업", "body": "사회문제 해결을 위한 비즈니스 모델을 가진 소셜벤처에 투자·보육 지원",
        "detail_url": "https://ksi.or.kr",
        "amount": "최대 5천만원",
    },
    {
        "id": "P006", "title": "K-스타트업 글로벌진출 지원", "organization": "창업진흥원",
        "category": "글로벌", "region": "전국", "deadline_status": "마감임박(D-3)",
        "ends_on": "2025-02-28", "starts_on": "2025-01-15",
        "target": "해외 진출을 희망하는 스타트업", "body": "해외 액셀러레이터 연계, 현지화 지원, 글로벌 네트워킹 기회 제공",
        "detail_url": "https://www.k-startup.go.kr/global",
        "amount": "최대 3천만원",
    },
    {
        "id": "P007", "title": "디지털 헬스케어 스타트업 공모전", "organization": "보건복지부",
        "category": "헬스케어", "region": "전국", "deadline_status": "모집중",
        "ends_on": "2025-07-31", "starts_on": "2025-05-01",
        "target": "디지털 헬스케어 분야 창업기업", "body": "디지털 헬스케어 혁신 기술을 보유한 스타트업 발굴 및 사업화 지원",
        "detail_url": "https://mohw.go.kr",
        "amount": "최대 2억원",
    },
    {
        "id": "P008", "title": "경기도 스타트업 캠퍼스 입주", "organization": "경기도경제과학진흥원",
        "category": "공간지원", "region": "경기", "deadline_status": "모집중",
        "ends_on": "2025-04-15", "starts_on": "2025-02-15",
        "target": "경기도 소재 또는 경기 이전 희망 스타트업", "body": "판교 스타트업 캠퍼스 입주공간, 투자유치 지원, 멘토링 서비스 제공",
        "detail_url": "https://geci.kr",
        "amount": "공간 지원 + 사업화 자금",
    },
]


class ProgramListResponse(BaseModel):
    total: int
    items: list[dict]


@router.get("/programs", response_model=ProgramListResponse)
async def list_programs(
    status: Optional[str] = Query(None, description="모집중 | 마감임박(D-3) | 마감"),
    region: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="검색어"),
) -> ProgramListResponse:
    items = list(_SAMPLE_PROGRAMS)
    if status:
        items = [p for p in items if p["deadline_status"] == status]
    if region:
        items = [p for p in items if p["region"] == region or p["region"] == "전국"]
    if category:
        items = [p for p in items if category in p["category"]]
    if q:
        q_lower = q.lower()
        items = [
            p for p in items
            if q_lower in p["title"].lower()
            or q_lower in p["organization"].lower()
            or q_lower in p["body"].lower()
        ]
    return ProgramListResponse(total=len(items), items=items)


@router.get("/programs/{program_id}")
async def get_program(program_id: str) -> dict:
    for p in _SAMPLE_PROGRAMS:
        if p["id"] == program_id:
            return p
    raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다.")


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
    evidence_retriever = (
        adapters.evidence_retriever if adapters else build_external_retriever()
    )
    orchestrator = Orchestrator(
        evidence_retriever=evidence_retriever,
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
