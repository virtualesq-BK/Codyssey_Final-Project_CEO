async def test_statement_caps_lines_per_group(monkeypatch):
    import json

    from app.api import finance_routes
    from app.core.llm_provider import MockProvider

    lines = [{"group": "opex", "label": f"비용{i}", "amount": 1000, "basis": ""} for i in range(9)]
    lines.append({"group": "revenue", "label": "구독 매출", "amount": 5000000, "basis": "구독자 250명 × 2만원"})
    llm = MockProvider()
    llm.set_responses([json.dumps({"unit_label": "구독자", "unit_count": 250, "lines": lines}, ensure_ascii=False)])
    monkeypatch.setattr(finance_routes, "_llm", lambda: llm)
    res = await finance_routes.statement(finance_routes.StatementRequest(revenue_type="구독형"))
    assert sum(1 for l in res.lines if l.group == "opex") == 6
    assert res.unit_label == "구독자" and res.unit_count == 250
