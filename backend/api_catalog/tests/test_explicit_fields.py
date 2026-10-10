import tempfile
import unittest
from datetime import date
from pathlib import Path

from api_catalog import Catalog


class ExplicitFieldTests(unittest.TestCase):
    def test_api_fields_are_queryable_as_columns(self):
        raw = {
            "id": 99,
            "pbanc_sn": 1,
            "biz_pbanc_nm": "공고",
            "intg_pbanc_biz_nm": "통합 공고",
            "intg_pbanc_yn": "N",
            "biz_prch_dprt_nm": "담당부서",
            "sprv_inst": "공공기관",
            "prch_cnpl_no": "02-0000-0000",
            "pbanc_rcpt_end_dt": "20261020",
            "aply_trgt": "일반기업",
            "biz_enyy": "3년 미만",
            "biz_trgt_age": "만 20세 이상",
            "biz_gdnc_url": "https://example.test/guide",
        }
        with tempfile.TemporaryDirectory() as tmp:
            catalog = Catalog(Path(tmp) / "test.sqlite3")
            catalog.upsert(raw, date(2026, 10, 8))
            row = catalog.one("SELECT * FROM api_announcements")
            self.assertEqual(row["api_id"], "99")
            self.assertEqual(row["integrated_title"], "통합 공고")
            self.assertEqual(row["integrated_flag"], "N")
            self.assertEqual(row["department"], "담당부서")
            self.assertEqual(row["institution_type"], "공공기관")
            self.assertEqual(row["contact_phone"], "02-0000-0000")
            self.assertEqual(row["application_target"], "일반기업")
            self.assertEqual(row["business_age"], "3년 미만")
            self.assertEqual(row["age_condition"], "만 20세 이상")
            self.assertEqual(row["guide_url"], "https://example.test/guide")
            catalog.close()


if __name__ == "__main__":
    unittest.main()
