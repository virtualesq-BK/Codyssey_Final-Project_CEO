"""
공통 Domain Schema
모든 Agent가 사용하는 데이터 모델 정의
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


# ──────────────────────────────────────────
# Enums
# ──────────────────────────────────────────

class BusinessStage(str, Enum):
    IDEA = "idea"
    VALIDATION = "validation"
    EARLY = "early"
    GROWTH = "growth"


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


class Decision(str, Enum):
    GO = "GO"
    PIVOT = "PIVOT"
    VALIDATE_MORE = "VALIDATE_MORE"
    STOP = "STOP"


# ──────────────────────────────────────────
# Core Models
# ──────────────────────────────────────────

class UserProfile(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    background: Optional[str] = None        # 직업/경력
    capital: Optional[float] = None          # 가용 자본 (만원)
    region: Optional[str] = None             # 거주 지역
    experience: Optional[str] = None         # 창업 경험 여부


class BusinessIdea(BaseModel):
    idea_id: str = Field(..., description="고유 식별자")
    title: str = Field(..., min_length=1, description="사업 아이디어 제목")
    problem: str = Field(..., min_length=1, description="해결하려는 문제")
    customer: str = Field(..., min_length=1, description="타겟 고객")
    solution: str = Field(..., min_length=1, description="제안 솔루션")
    industry: str = Field(..., description="산업 분야")
    location: str = Field(default="전국", description="사업 지역")
    business_stage: BusinessStage = Field(default=BusinessStage.IDEA)
    user_profile: Optional[UserProfile] = None

    @field_validator("title", "problem", "customer", "solution")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("빈 문자열은 허용되지 않습니다")
        return v.strip()


class Evidence(BaseModel):
    title: str
    source: str
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    content: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class AgentResult(BaseModel):
    agent_name: str
    status: AgentStatus
    summary: str
    findings: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None

    @classmethod
    def failed(cls, agent_name: str, error: str) -> "AgentResult":
        return cls(
            agent_name=agent_name,
            status=AgentStatus.FAILED,
            summary=f"Agent 실행 실패: {error}",
            error_message=error,
            confidence=0.0,
        )

    @classmethod
    def skipped(cls, agent_name: str, reason: str) -> "AgentResult":
        return cls(
            agent_name=agent_name,
            status=AgentStatus.SKIPPED,
            summary=f"Agent 건너뜀: {reason}",
            confidence=0.0,
        )


class DecisionResult(BaseModel):
    summary: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    financial_summary: str = ""
    validation_items: list[str] = Field(default_factory=list)
    action_plan: list[str] = Field(default_factory=list)
    decision: Decision
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)
    disclaimer: str = Field(
        default="본 분석은 의사결정 지원 목적이며 실제 사업 성공을 보장하지 않습니다.",
        description="면책 조항"
    )


class TokenUsage(BaseModel):
    agent_name: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    estimated_cost_usd: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WorkflowResult(BaseModel):
    idea_id: str
    status: AgentStatus
    agent_results: dict[str, AgentResult] = Field(default_factory=dict)
    decision_result: Optional[DecisionResult] = None
    token_usages: list[TokenUsage] = Field(default_factory=list)
    total_execution_time_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
