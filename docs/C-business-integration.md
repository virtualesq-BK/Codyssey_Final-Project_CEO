# C Agent integration

CustomerAgent and BusinessModelAgent inherit existing BaseAgent and use
LLMProvider.generate_structured, BusinessIdea, AgentResult and Evidence.
Existing imports from dummy_agents remain compatible.

Customer findings contain `customer_profile`: primary/secondary customer,
structured hypothesis personas (needs, pain points, JTBD, motivations and
barriers), willingness to pay and acquisition hypotheses.
Business findings contain `business_model.canvas`: value proposition,
segments, revenue, pricing, sales/distribution, acquisition, activities,
resources, partners, costs and differentiation.
Both carry recommendations and confidence. Each claim has text, kind
(fact/hypothesis/recommendation) and zero-based evidence_indices referring
to that AgentResult.evidence. Invalid or missing citations downgrade facts.
Citation validity establishes traceability, not truth or semantic entailment;
human source review and real customer research remain necessary.

Orchestrator passes Phase 1 results through BusinessModelAgent.set_agent_results
before Phase 2. Failed customer results are excluded. DecisionAgent receives
both structured results through its existing interface. Orchestrator instances
are stateful: create one per workflow; do not share across concurrent requests.

## Shared RAG pending

This branch contains no B-team Shared RAG implementation or published interface.
No independent RAG system is created. Optional evidence_retriever is an async
callable `(query: str) -> list[Evidence]`; adapt the actual B interface to it and
inject both agents via the existing Orchestrator constructor. This seam is not
a claim that B integration is complete. Retrieval failure/absence produces
PARTIAL, empty evidence and confidence capped at 0.3. No fabricated evidence
or automatic price statistics are supplied. Live LLM/RAG verification remains
pending credentials and the shared retriever.

Run tests from backend using `python -m pytest -q`. Tests use MockProvider;
they verify output constraints, insufficient evidence, citation handling,
retrieval failure and Customer-to-BusinessModel-to-Decision integration.

## Connecting B later

Use the composition helper after B publishes the actual interface:

```python
from app.agents.business_workflow import build_business_workflow

# adapter: async (query: str) -> list[app.core.schemas.Evidence]
# Implement this adapter against B's published API, preserving source metadata.
workflow = build_business_workflow(evidence_retriever=adapter,
                                   retrieval_timeout_sec=10.0)
result = await workflow.run(idea)
```

The same adapter is used by both C agents. Each query identifies the agent;
B can route Customer queries to customer research and BusinessModel queries
to pricing/model benchmarks. The caller owns connection setup and cleanup.
Retrieval times out after 10 seconds by default; errors/timeouts continue
analysis as hypotheses with PARTIAL status. Downgraded facts also cap confidence
at 0.3, even if unrelated sources were retrieved. LLM errors still use BaseAgent
retry/failure handling. Async adapters must not perform blocking work in the
event loop; use B's async API or an appropriate executor.

Before integrating: check B's returned type, metadata and cancellation behavior;
map documents to existing Evidence (never fabricate metadata); run the complete
backend suite; then validate live LLM and RAG with locally configured keys.
The API currently uses Orchestrator directly. Once B's adapter exists, the API
composition can use build_business_workflow with that adapter. No automatic
discovery, temporary RAG implementation or B-branch mutation is needed.
