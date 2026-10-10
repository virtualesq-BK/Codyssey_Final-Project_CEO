import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from api_catalog import Catalog, classify_deadline


class CatalogTests(unittest.TestCase):
    def test_three_deadline_categories(self):
        day = date(2026, 10, 8)
        self.assertEqual(classify_deadline((day + timedelta(days=4)).isoformat(), day), ("모집중", 4))
        self.assertEqual(classify_deadline((day + timedelta(days=3)).isoformat(), day), ("마감임박(D-3)", 3))
        self.assertEqual(classify_deadline(day.isoformat(), day), ("마감임박(D-3)", 0))
        self.assertEqual(classify_deadline((day - timedelta(days=1)).isoformat(), day), ("마감", -1))

    def test_raw_api_data_is_preserved_and_updated(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog = Catalog(Path(tmp) / "test.sqlite3")
            raw = {"pbanc_sn": 1, "biz_pbanc_nm": "공고", "pbanc_rcpt_end_dt": "20261020", "extra": "보존"}
            self.assertEqual(catalog.upsert(raw, date(2026, 10, 8)), "new")
            raw["biz_pbanc_nm"] = "수정 공고"
            self.assertEqual(catalog.upsert(raw, date(2026, 10, 8)), "updated")
            row = catalog.one("SELECT * FROM api_announcements")
            self.assertEqual(row["title"], "수정 공고")
            self.assertEqual(json.loads(row["raw_json"])["extra"], "보존")
            self.assertEqual(catalog.one("SELECT COUNT(*) n FROM api_announcements")["n"], 1)
            catalog.close()


if __name__ == "__main__":
    unittest.main()
