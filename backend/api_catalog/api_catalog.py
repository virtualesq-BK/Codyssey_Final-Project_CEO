import argparse
import json
import os

from _api_catalog_core import *
import _api_catalog_core as core


EXTRA_FIELDS = {
    "api_id": "id",
    "integrated_title": "intg_pbanc_biz_nm",
    "integrated_flag": "intg_pbanc_yn",
    "department": "biz_prch_dprt_nm",
    "institution_type": "sprv_inst",
    "contact_phone": "prch_cnpl_no",
    "application_target": "aply_trgt",
    "business_age": "biz_enyy",
    "age_condition": "biz_trgt_age",
    "guide_url": "biz_gdnc_url",
    "business_application_url": "biz_aply_url",
    "exclusion_target": "aply_excl_trgt_ctnt",
    "preference": "prfn_matr",
    "email_instructions": "aply_mthd_eml_rcpt_istc",
    "fax_instructions": "aply_mthd_fax_rcpt_istc",
    "other_instructions": "aply_mthd_etc_istc",
    "postal_instructions": "aply_mthd_pssr_rcpt_istc",
    "visit_instructions": "aply_mthd_vst_rcpt_istc",
}


class Catalog(core.Catalog):
    def __init__(self, path="data/api_catalog.sqlite3"):
        super().__init__(path)
        existing = {
            row["name"] for row in self.rows("PRAGMA table_info(api_announcements)")
        }
        for column in EXTRA_FIELDS:
            if column not in existing:
                self.conn.execute(
                    f'ALTER TABLE api_announcements ADD COLUMN "{column}" TEXT'
                )
        self.conn.commit()

    def upsert(self, raw, as_of=None):
        values = {name: raw.get(key) for name, key in core.FIELDS.items()}
        source_id = str(values["source_id"] or "").strip()
        title = str(values["title"] or "").strip()
        if not source_id or not title:
            raise ValueError("API 공고 ID와 제목은 필수입니다.")
        status, remaining = core.classify_deadline(values["ends_on"], as_of)
        ends_on = core.parse_api_date(values["ends_on"]).isoformat()
        starts_on = (
            core.parse_api_date(values["starts_on"]).isoformat()
            if values["starts_on"]
            else None
        )
        raw_json = json.dumps(raw, ensure_ascii=False, sort_keys=True)
        fingerprint = core.sha256(raw_json.encode("utf-8")).hexdigest()
        old = self.one(
            "SELECT content_hash FROM api_announcements WHERE source='kstartup' AND source_id=?",
            (source_id,),
        )
        current = core.stamp()
        base_columns = [
            "source", "source_id", "title", "organization", "starts_on", "ends_on",
            "deadline_status", "days_remaining", "open_flag", "body", "target",
            "region", "category", "detail_url", "application_url", "raw_json",
            "content_hash", "first_seen_at", "updated_at",
        ]
        extra_columns = list(EXTRA_FIELDS)
        columns = base_columns + extra_columns
        placeholders = ",".join("?" for _ in columns)
        updates = ",".join(
            f'"{column}"=excluded."{column}"'
            for column in columns
            if column not in {"source", "source_id", "first_seen_at"}
        )
        base_values = [
            "kstartup", source_id, title, values["organization"], starts_on, ends_on,
            status, remaining, values["open_flag"], values["body"], values["target"],
            values["region"], values["category"], values["detail_url"],
            values["application_url"], raw_json, fingerprint, current, current,
        ]
        extra_values = [raw.get(api_name) for api_name in EXTRA_FIELDS.values()]
        self.conn.execute(
            f"INSERT INTO api_announcements ({','.join(columns)}) VALUES ({placeholders}) "
            f"ON CONFLICT(source,source_id) DO UPDATE SET {updates}",
            base_values + extra_values,
        )
        self.conn.commit()
        if old is None:
            return "new"
        return "unchanged" if old["content_hash"] == fingerprint else "updated"


def main():
    core.load_env()
    parser = argparse.ArgumentParser(description="K-Startup API 원본 공고 DB")
    parser.add_argument(
        "--database",
        default=os.environ.get("API_CATALOG_DB") or "data/api_catalog.sqlite3",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("sync")
    command.add_argument("--as-of")
    command = sub.add_parser("import-json")
    command.add_argument("path")
    command.add_argument("--as-of")
    command = sub.add_parser("refresh-status")
    command.add_argument("--as-of")
    command = sub.add_parser("list")
    command.add_argument(
        "--status", choices=[STATUS_OPEN, STATUS_CLOSING, STATUS_CLOSED]
    )
    args = parser.parse_args()
    catalog = Catalog(args.database)
    try:
        if args.command == "sync":
            key = os.environ.get("DATA_GO_KR_SERVICE_KEY", "").strip()
            if not key:
                raise SystemExit("DATA_GO_KR_SERVICE_KEY가 비어 있습니다.")
            result = core.sync(catalog, key, core.parse_day(args.as_of))
        elif args.command == "import-json":
            result = core.import_json(catalog, args.path, core.parse_day(args.as_of))
        elif args.command == "refresh-status":
            catalog.refresh(core.parse_day(args.as_of))
            result = {
                "updated": len(catalog.rows("SELECT 1 FROM api_announcements"))
            }
        else:
            sql, params = "SELECT * FROM api_announcements", ()
            if args.status:
                sql += " WHERE deadline_status=?"
                params = (args.status,)
            result = [
                dict(row)
                for row in catalog.rows(sql + " ORDER BY ends_on,source_id", params)
            ]
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        catalog.close()


if __name__ == "__main__":
    main()
