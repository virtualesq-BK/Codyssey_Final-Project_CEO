from app.api.market_routes import EvidenceIn, PointIn, SamIn, SeriesIn, SizingDraft, SomIn, TamIn, build, parse_money

EV = [
    EvidenceIn(title="헤럴드경제", content="국내 에듀테크 시장 규모는 2021년 약 7조3000억원에서 2025년 약 10조원으로 전망"),
    EvidenceIn(title="IMARC", content="한국 에드테크 시장은 2024년 48억 달러, 2033년 100억 달러에 달할 것"),
]


def test_parse_money():
    assert parse_money("약 7조3000억원") == (7.3e12, "KRW")
    assert parse_money("48억 달러") == (4.8e9, "USD")
    assert parse_money("$4.8 billion") == (4.8e9, "USD")


def test_build_converts_and_computes_without_trusting_model_math():
    draft = SizingDraft(
        tam=TamIn(raw="48억 달러", year=2024, evidence_index=1),
        sam=SamIn(share=0.4, basis="K-12 비중"),
        som=SomIn(units=900, unit_label="학급", price_per_year=2_100_000, basis="20% 채택"),
        series=[
            SeriesIn(name="국내 (헤럴드)", evidence_index=0, points=[PointIn(year=2021, raw="약 7조3000억원"), PointIn(year=2025, raw="약 10조원", projected=True)]),
            SeriesIn(name="지어낸 숫자", evidence_index=1, points=[PointIn(year=2024, raw="48억 달러"), PointIn(year=2030, raw="200억 달러")]),
        ],
    )
    out = build(draft, EV)
    assert out.tam.value == 4.8e9 * 1400 and not out.tam.estimated
    assert out.sam.value == out.tam.value * 0.4
    assert out.som.value == 900 * 2_100_000
    assert [s.name for s in out.series] == ["국내 (헤럴드)"]  # 근거에 없는 200억 달러 시리즈는 점이 1개라 버림
    assert out.series[0].unit == "KRW" and out.series[0].points[0].value == 7.3e12


def test_tam_not_in_evidence_is_dropped():
    out = build(SizingDraft(tam=TamIn(raw="500조원", evidence_index=0), sam=SamIn(share=0.5), som=SomIn()), EV)
    assert out.tam.value is None and out.tam.display == "자료 부족" and out.sam.value is None
