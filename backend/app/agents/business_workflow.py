"""Composition helper: inject B's shared retrieval adapter into both C agents."""
from app.agents.business_agents import BusinessModelAgent, CustomerAgent, EvidenceRetriever
from app.agents.orchestrator import Orchestrator
from app.core.llm_provider import LLMProvider


def build_business_workflow(
    *,
    llm_provider: LLMProvider | None = None,
    evidence_retriever: EvidenceRetriever | None = None,
    retrieval_timeout_sec: float = 10.0,
) -> Orchestrator:
    """Create per-request workflow; callers own the shared retriever lifecycle.

    A missing retriever uses the agents' explicit insufficient-evidence path.
    No B-team module is imported until its adapter is supplied by the caller.
    """
    options = dict(llm_provider=llm_provider, evidence_retriever=evidence_retriever,
                   retrieval_timeout_sec=retrieval_timeout_sec)
    return Orchestrator(
        llm_provider=llm_provider,
        customer_agent=CustomerAgent(**options),
        business_model_agent=BusinessModelAgent(**options),
    )
