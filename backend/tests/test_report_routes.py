from app.api.report_routes import AreaScore, ScoreResponse, clamp


def test_clamp_keeps_known_areas_in_order_and_bounds():
    resp = ScoreResponse(scores=[
        AreaScore(area="RiskAgent", score=0, reason="위험 큼"),
        AreaScore(area="MarketAgent", score=12, reason="성장 시장"),
        AreaScore(area="Unknown", score=5),
    ])
    out = clamp(resp, ["MarketAgent", "CustomerAgent", "RiskAgent"])
    assert [(s.area, s.score) for s in out.scores] == [("MarketAgent", 10), ("RiskAgent", 1)]


def test_reason_strips_input_names_and_confidence():
    from app.api.report_routes import _tidy

    assert _tidy("finance_summary의 월 169만원 매출은 근거 없음 (신뢰도 0%)") == "월 169만원 매출은 근거 없음"
    assert _tidy("고객 수 미입력으로 신뢰도 없음.") == "고객 수 미입력으로 근거 부족."
    assert _tidy("출처 불명으로 신뢰도 극히 낮음.") == "출처 불명으로 근거 부족."
