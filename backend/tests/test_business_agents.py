import json
import asyncio

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


@pytest.mark.asyncio
async def test_retrieval_timeout_returns_partial_instead_of_hanging():
    async def retrieve(query):
        await asyncio.sleep(10)
        return []
    agent = CustomerAgent(provider(customer_data()), evidence_retriever=retrieve,
                          retrieval_timeout_sec=0.01)
    result = await asyncio.wait_for(agent.run(idea()), timeout=1)
    assert result.status == AgentStatus.PARTIAL
    assert not result.evidence


@pytest.mark.asyncio
async def test_downgraded_fact_caps_confidence_even_with_other_evidence():
    from app.core.schemas import Evidence
    async def retrieve(query):
        return [Evidence(title="Report", source="Research", content="Other data")]
    data = customer_data()
    data["primary_customer"] = claim(kind="fact", refs=[99])
    result = await CustomerAgent(provider(data), evidence_retriever=retrieve).run(idea())
    assert result.status == AgentStatus.PARTIAL
    assert result.confidence <= 0.3


@pytest.mark.asyncio
async def test_shared_retriever_is_used_by_both_agents_and_customer_context_is_sent():
    from app.agents.business_workflow import build_business_workflow
    from app.agents.business_agents import CompetitionAnalysis, CustomerProfile
    from app.core.schemas import Evidence
    queries = []

    def _competition_data():
        c = claim()
        competitor = {"name": "경쟁사A", "description": c, "strengths": [c],
                      "weaknesses": [c], "target_customer": c}
        return {"summary": "경쟁 분석", "direct_competitors": [competitor],
                "indirect_competitors": [], "differentiation": [c],
                "entry_barriers": [c], "competitive_position": c,
                "recommendations": ["조사 필요"], "confidence": 0.5}

    class InspectingProvider(MockProvider):
        async def generate_structured(self, prompt, response_model, system=""):
            payload = json.loads(prompt)
            if response_model is CustomerProfile:
                return response_model.model_validate(customer_data())
            if response_model is CompetitionAnalysis:
                return response_model.model_validate(_competition_data())
            # BusinessModelAnalysis
            assert payload["customer_result"]["findings"][0]["customer_profile"]["personas"]
            fields = response_model.model_fields["canvas"].annotation.model_fields
            return response_model.model_validate({"summary": "Canvas", "canvas": {
                key: [claim()] for key in fields}, "recommendations": ["Test"], "confidence": 0.8})

    async def retrieve(query):
        queries.append(query)
        return [Evidence(title="Report", source="Research", content="Data")]

    workflow = build_business_workflow(llm_provider=InspectingProvider(), evidence_retriever=retrieve)
    result = await workflow.run(idea())
    # CustomerAgent + CompetitorAgent + BusinessModelAgent 각 1회씩 검색
    assert len(queries) == 3
    assert len(set(queries)) == 3  # 모든 쿼리가 서로 다름
    assert result.agent_results["CustomerAgent"].evidence
    assert result.agent_results["CompetitorAgent"].evidence
    assert result.agent_results["BusinessModelAgent"].evidence


@pytest.mark.asyncio
async def test_failed_customer_clears_prior_context():
    from app.core.schemas import AgentResult
    agent = BusinessModelAgent(MockProvider())
    successful = await CustomerAgent(provider(customer_data())).run(idea())
    agent.set_agent_results({"CustomerAgent": successful})
    agent.set_agent_results({"CustomerAgent": AgentResult.failed("CustomerAgent", "offline")})
    assert agent._customer_result is None
    agent.set_agent_results({})
    assert agent._customer_result is None


@pytest.mark.asyncio
async def test_workflow_cancellation_is_not_swallowed_as_retrieval_failure():
    async def retrieve(query):
        raise asyncio.CancelledError()
    agent = CustomerAgent(provider(customer_data()), evidence_retriever=retrieve)
    with pytest.raises(asyncio.CancelledError):
        await agent.run(idea())
