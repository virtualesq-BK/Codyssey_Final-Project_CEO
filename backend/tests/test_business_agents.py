import json

import pytest

from app.agents.business_agents import CustomerAgent, BusinessModelAgent
from app.core.llm_provider import MockProvider
from app.core.schemas import AgentStatus, BusinessIdea


def idea():
    return BusinessIdea(idea_id="c1", title="Laundry", problem="No time",
                        customer="Workers", solution="Pickup", industry="Services")


def claim(text="Test", kind="hypothesis", refs=None):
    return {"text": text, "kind": kind, "evidence_indices": refs or []}


def customer_data():
    return {"summary": "Hypothesis persona", "primary_customer": claim(),
            "secondary_customer": claim(), "personas": [{
                "segment": "Workers", "persona": "Busy worker", "basis": "hypothesis",
                **{k: [claim()] for k in ["needs", "pain_points", "jobs_to_be_done",
                    "buying_motivation", "buying_barriers"]}}],
            "willingness_to_pay": claim(), "customer_acquisition": [claim()],
            "recommendations": ["Interview customers"], "confidence": 0.9}


def provider(data):
    llm = MockProvider()
    llm.set_responses([json.dumps(data)])
    return llm


@pytest.mark.asyncio
async def test_customer_without_evidence_is_partial_and_structured():
    result = await CustomerAgent(provider(customer_data())).run(idea())
    assert result.status == AgentStatus.PARTIAL
    assert result.evidence == []
    assert result.confidence <= 0.3
    assert result.findings[0]["customer_profile"]["personas"][0]["jobs_to_be_done"]


@pytest.mark.asyncio
async def test_unsupported_fact_is_downgraded():
    data = customer_data()
    data["primary_customer"] = claim(kind="fact", refs=[99])
    result = await CustomerAgent(provider(data)).run(idea())
    item = result.findings[0]["customer_profile"]["primary_customer"]
    assert item["kind"] == "hypothesis"
    assert item["evidence_indices"] == []


@pytest.mark.asyncio
async def test_business_model_consumes_customer_context():
    customer = await CustomerAgent(provider(customer_data())).run(idea())
    keys = ["value_proposition", "customer_segments", "revenue_model", "pricing",
            "sales_channels", "distribution", "customer_acquisition", "key_activities",
            "key_resources", "partners", "cost_structure", "competitive_differentiation"]
    data = {"summary": "Canvas hypotheses", "canvas": {k: [claim()] for k in keys},
            "recommendations": ["Test pricing"], "confidence": 0.8}
    agent = BusinessModelAgent(provider(data))
    agent.set_agent_results({"CustomerAgent": customer})
    result = await agent.run(idea())
    assert result.status == AgentStatus.PARTIAL
    assert result.findings[0]["business_model"]["canvas"]["pricing"][0]["kind"] == "hypothesis"


@pytest.mark.asyncio
async def test_invalid_persona_fails_using_base_error_handling():
    data = customer_data()
    data["personas"][0]["jobs_to_be_done"] = []
    agent = CustomerAgent(provider(data))
    agent.RETRY_DELAY_SEC = 0
    assert (await agent.run(idea())).status == AgentStatus.FAILED


@pytest.mark.asyncio
async def test_retrieved_evidence_supports_traceable_fact():
    from app.core.schemas import Evidence
    evidence = Evidence(title="Interview", source="Research", content="Workers lack time")
    async def retrieve(query):
        return [evidence]
    data = customer_data()
    data["primary_customer"] = claim("Workers lack time", "fact", [0])
    result = await CustomerAgent(provider(data), evidence_retriever=retrieve).run(idea())
    assert result.status == AgentStatus.SUCCESS
    assert result.evidence == [evidence]
    assert result.findings[0]["customer_profile"]["primary_customer"]["kind"] == "fact"


@pytest.mark.asyncio
async def test_retrieval_failure_preserves_hypothesis_analysis():
    async def retrieve(query):
        raise RuntimeError("offline")
    result = await CustomerAgent(provider(customer_data()), evidence_retriever=retrieve).run(idea())
    assert result.status == AgentStatus.PARTIAL
    assert result.evidence == []


@pytest.mark.asyncio
async def test_orchestrator_hands_customer_result_to_business_model():
    from app.agents.orchestrator import Orchestrator
    from app.core.schemas import AgentResult
    class CapturingBusinessModel(BusinessModelAgent):
        async def _execute(self, business_idea):
            assert self._customer_result is not None
            return AgentResult(agent_name=self.agent_name, status=AgentStatus.PARTIAL, summary="ok")
    llm = provider(customer_data())
    orchestrator = Orchestrator(llm_provider=llm, business_model_agent=CapturingBusinessModel(llm))
    result = await orchestrator.run(idea())
    assert result.agent_results["BusinessModelAgent"].status == AgentStatus.PARTIAL
    assert result.decision_result is not None
