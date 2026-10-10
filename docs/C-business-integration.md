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
