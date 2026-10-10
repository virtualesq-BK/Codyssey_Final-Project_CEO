"""B팀의 공유 검색 어댑터를 C팀 Agent에 주입하는 워크플로 구성 도우미."""
from app.agents.business_agents import (
    BusinessModelAgent,
    CompetitorAgent,
    CustomerAgent,
    EvidenceRetriever,
)
from app.agents.orchestrator import Orchestrator
from app.core.llm_provider import LLMProvider


def build_business_workflow(
    *,
    llm_provider: LLMProvider | None = None,
    evidence_retriever: EvidenceRetriever | None = None,
    retrieval_timeout_sec: float = 10.0,
) -> Orchestrator:
    """요청마다 워크플로를 생성하며, 공유 검색기의 생성과 정리는 호출자가 담당한다.

    검색기가 없으면 각 Agent가 근거 부족 상태를 명시해 반환한다.
    호출자가 어댑터를 제공하기 전에는 B팀 모듈을 가져오지 않는다.
    """
    options = dict(llm_provider=llm_provider, evidence_retriever=evidence_retriever,
                   retrieval_timeout_sec=retrieval_timeout_sec)
    return Orchestrator(
        llm_provider=llm_provider,
        customer_agent=CustomerAgent(**options),
        competitor_agent=CompetitorAgent(**options),
        business_model_agent=BusinessModelAgent(**options),
    )
