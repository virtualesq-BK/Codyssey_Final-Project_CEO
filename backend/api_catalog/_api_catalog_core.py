import argparse
import json
import os
import sqlite3
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path


ENDPOINT = "https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01"
STATUS_OPEN = "모집중"
STATUS_CLOSING = "마감임박(D-3)"
STATUS_CLOSED = "마감"

SCHEMA = """
CREATE TABLE IF NOT EXISTS api_announcements (
 source TEXT NOT NULL,
 source_id TEXT NOT NULL,
 title TEXT NOT NULL,
 organization TEXT,
 starts_on TEXT,
 ends_on TEXT NOT NULL,
 deadline_status TEXT NOT NULL,
 days_remaining INTEGER NOT NULL,
 open_flag TEXT,
 body TEXT,
 target TEXT,
 region TEXT,
 category TEXT,
 detail_url TEXT,
 application_url TEXT,
 raw_json TEXT NOT NULL,
 content_hash TEXT NOT NULL,
 first_seen_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 PRIMARY KEY (source, source_id),
 CHECK (deadline_status IN ('모집중','마감임박(D-3)','마감'))
);
CREATE INDEX IF NOT EXISTS idx_api_deadline_status
 ON api_announcements(deadline_status, ends_on);
"""

FIELDS = {
    "source_id": "pbanc_sn",
    "title": "biz_pbanc_nm",
    "organization": "pbanc_ntrp_nm",
    "starts_on": "pbanc_rcpt_bgng_dt",
    "ends_on": "pbanc_rcpt_end_dt",
    "open_flag": "rcrt_prgs_yn",
    "body": "pbanc_ctnt",
    "target": "aply_trgt_ctnt",
    "region": "supt_regin",
    "category": "supt_biz_clsfc",
    "detail_url": "detl_pg_url",
    "application_url": "aply_mthd_onli_rcpt_istc",
}


def load_env(path=".env"):
    file = Path(path)
    if not file.exists():
        return
    for line in file.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def stamp():
    return datetime.now(timezone.utc).isoformat()


def parse_api_date(value):
    if not value:
        raise ValueError("마감일이 없는 API 공고는 분류할 수 없습니다.")
    text = str(value).strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            pass
    raise ValueError(f"지원하지 않는 마감일 형식: {text}")


def classify_deadline(value, as_of=None):
    remaining = (parse_api_date(value) - (as_of or date.today())).days
    if remaining < 0:
        return STATUS_CLOSED, remaining
    if remaining <= 3:
        return STATUS_CLOSING, remaining
    return STATUS_OPEN, remaining


class Catalog:
    def __init__(self, path="data/api_catalog.sqlite3"):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    def rows(self, sql, args=()):
        return self.conn.execute(sql, args).fetchall()

    def one(self, sql, args=()):
        return self.conn.execute(sql, args).fetchone()

    def upsert(self, raw, as_of=None):
        values = {name: raw.get(key) for name, key in FIELDS.items()}
        source_id = str(values["source_id"] or "").strip()
        title = str(values["title"] or "").strip()
        if not source_id or not title:
            raise ValueError("API 공고 ID와 제목은 필수입니다.")
        status, remaining = classify_deadline(values["ends_on"], as_of)
        ends_on = parse_api_date(values["ends_on"]).isoformat()
        starts_on = parse_api_date(values["starts_on"]).isoformat() if values["starts_on"] else None
        raw_json = json.dumps(raw, ensure_ascii=False, sort_keys=True)
        fingerprint = sha256(raw_json.encode("utf-8")).hexdigest()
        old = self.one("SELECT content_hash FROM api_announcements WHERE source='kstartup' AND source_id=?", (source_id,))
        current = stamp()
        self.conn.execute(
            """INSERT INTO api_announcements VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(source,source_id) DO UPDATE SET
              title=excluded.title,organization=excluded.organization,
              starts_on=excluded.starts_on,ends_on=excluded.ends_on,
              deadline_status=excluded.deadline_status,days_remaining=excluded.days_remaining,
              open_flag=excluded.open_flag,body=excluded.body,target=excluded.target,
              region=excluded.region,category=excluded.category,
              detail_url=excluded.detail_url,application_url=excluded.application_url,
              raw_json=excluded.raw_json,content_hash=excluded.content_hash,
              updated_at=excluded.updated_at""",
            ("kstartup", source_id, title, values["organization"], starts_on, ends_on,
             status, remaining, values["open_flag"], values["body"], values["target"],
             values["region"], values["category"], values["detail_url"],
             values["application_url"], raw_json, fingerprint, current, current),
        )
        self.conn.commit()
        if old is None:
            return "new"
        return "unchanged" if old["content_hash"] == fingerprint else "updated"

    def refresh(self, as_of=None):
        for row in self.rows("SELECT source_id,ends_on FROM api_announcements"):
            status, remaining = classify_deadline(row["ends_on"], as_of)
            self.conn.execute(
                "UPDATE api_announcements SET deadline_status=?,days_remaining=?,updated_at=? WHERE source='kstartup' AND source_id=?",
                (status, remaining, stamp(), row["source_id"]),
            )
        self.conn.commit()


def extract_rows(payload):
    candidates = [payload.get("data"), payload.get("response", {}).get("body", {}).get("items", {}).get("item")]
    for rows in candidates:
        if isinstance(rows, list):
            return rows
        if isinstance(rows, dict):
            return [rows]
    return []


def total_count(payload):
    for value in (payload.get("totalCount"), payload.get("response", {}).get("body", {}).get("totalCount")):
        if value not in (None, ""):
            return int(value)
    return None


def request_page(service_key, page, page_size=100):
    params = {
        "serviceKey": urllib.parse.unquote(service_key),
        "page": page,
        "perPage": page_size,
        "returnType": "json",
        "cond[rcrt_prgs_yn::EQ]": "Y",
    }
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "kstartup-api-catalog/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8-sig"))


def sync(catalog, service_key, as_of=None, max_pages=30):
    stats = {"new": 0, "updated": 0, "unchanged": 0}
    read = 0
    seen_pages = set()
    for page in range(1, max_pages + 1):
        payload = request_page(service_key, page)
        rows = extract_rows(payload)
        fingerprint = sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
        if rows and fingerprint in seen_pages:
            raise RuntimeError("API가 같은 페이지를 반복 반환했습니다.")
        seen_pages.add(fingerprint)
        for row in rows:
            stats[catalog.upsert(row, as_of)] += 1
        read += len(rows)
        total = total_count(payload)
        if not rows or (total is not None and read >= total):
            return stats
    raise RuntimeError("API 페이지 상한에 도달했습니다.")


def import_json(catalog, path, as_of=None):
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    records = payload if isinstance(payload, list) else [payload]
    stats = {"new": 0, "updated": 0, "unchanged": 0}
    for record in records:
        stats[catalog.upsert(record, as_of)] += 1
    return stats


def parse_day(value):
    return parse_api_date(value) if value else date.today()


def main():
    load_env()
    parser = argparse.ArgumentParser(description="K-Startup API 원본 공고 DB")
    parser.add_argument("--database", default=os.environ.get("API_CATALOG_DB") or "data/api_catalog.sqlite3")
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("sync")
    command.add_argument("--as-of")
    command = sub.add_parser("import-json")
    command.add_argument("path")
    command.add_argument("--as-of")
    command = sub.add_parser("refresh-status")
    command.add_argument("--as-of")
    command = sub.add_parser("list")
    command.add_argument("--status", choices=[STATUS_OPEN, STATUS_CLOSING, STATUS_CLOSED])
    args = parser.parse_args()
    catalog = Catalog(args.database)
    try:
        if args.command == "sync":
            key = os.environ.get("DATA_GO_KR_SERVICE_KEY", "").strip()
            if not key:
                raise SystemExit("DATA_GO_KR_SERVICE_KEY가 비어 있습니다.")
            result = sync(catalog, key, parse_day(args.as_of))
        elif args.command == "import-json":
            result = import_json(catalog, args.path, parse_day(args.as_of))
        elif args.command == "refresh-status":
            catalog.refresh(parse_day(args.as_of))
            result = {"updated": len(catalog.rows("SELECT 1 FROM api_announcements"))}
        else:
            sql, params = "SELECT * FROM api_announcements", ()
            if args.status:
                sql += " WHERE deadline_status=?"
                params = (args.status,)
            result = [dict(row) for row in catalog.rows(sql + " ORDER BY ends_on,source_id", params)]
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        catalog.close()


if __name__ == "__main__":
    main()
