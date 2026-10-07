"""
SQLAlchemy models for Token usage logging
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class TokenUsageLog(Base):
    __tablename__ = "token_usage_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    idea_id = Column(String, nullable=False, index=True)
    agent_name = Column(String, nullable=False)
    model = Column(String, nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkflowLog(Base):
    __tablename__ = "workflow_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    idea_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False)
    total_execution_time_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
