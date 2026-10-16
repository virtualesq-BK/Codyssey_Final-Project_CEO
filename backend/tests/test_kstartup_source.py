from datetime import date

from app.api.kstartup_source import deadline_status, to_program


def test_to_program_maps_fields_and_detail_link():
    p = to_program({
        "biz_pbanc_nm": "2026 동네창업학교", "pbanc_sn": "179527", "pbanc_ntrp_nm": "충남신용보증재단",
        "supt_biz_clsfc": "멘토링ㆍ컨설팅ㆍ교육", "supt_regin": "충남", "pbanc_rcpt_bgng_dt": "20261007",
        "pbanc_rcpt_end_dt": "20261104", "aply_trgt_ctnt": "예비창업자", "biz_enyy": "예비창업자", "pbanc_ctnt": "교육생 모집",
        "aply_mthd_onli_rcpt_istc": "None",
    })
    assert p["id"] == "KS179527" and p["region"] == "충남" and p["ends_on"] == "2026-11-04"
    assert p["detail_url"].endswith("pbancSn=179527")
    assert p["apply_url"] == ""


def test_deadline_status():
    today = date(2026, 10, 16)
    assert deadline_status(date(2026, 10, 18), today) == "마감임박(D-3)"
    assert deadline_status(date(2026, 10, 30), today) == "모집중"
    assert deadline_status(date(2026, 10, 15), today) == "마감"


def test_missing_title_is_skipped():
    assert to_program({"pbanc_sn": "1"}) is None
