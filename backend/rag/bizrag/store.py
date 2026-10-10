"""지식 저장소 (SQLite 단일 파일).

두 계층으로 저장한다.
  1) 정형 데이터
     - observations : 시계열/통계 수치 (검색지수, 통계표, 경제지표). 조회 조건 서명(query_sig)을 함께 저장
     - records      : 행 단위 원자료 (가격표, 피해구제 건, 해외진출기업, CSV 등)
  2) 문서 데이터 (RAG 대상)
     - documents + chunks(FTS5) : 법령 조문, 특허 초록, 통계표 설명, 상담 답변 등

모든 행은 출처 메타데이터(source, url, retrieved_at, license, original_id)를 가진다.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .textindex import chunk_text, to_index_text, to_match_query

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS fetch_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  job TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT,            -- ok | error | skipped
  items INTEGER DEFAULT 0,
  message TEXT
);
CREATE INDEX IF NOT EXISTS ix_runs ON fetch_runs(source, job, status, finished_at);

CREATE TABLE IF NOT EXISTS documents (
  doc_id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  doc_type TEXT NOT NULL,
  title TEXT,
  body TEXT,
  url TEXT,
  published_at TEXT,
  retrieved_at TEXT NOT NULL,
  license TEXT,
  original_id TEXT,
  content_hash TEXT,
  meta_json TEXT
);
CREATE INDEX IF NOT EXISTS ix_docs_source ON documents(source, doc_type);

CREATE TABLE IF NOT EXISTS chunks (
  chunk_id TEXT PRIMARY KEY,
  doc_id TEXT NOT NULL,
  seq INTEGER NOT NULL,
  text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_chunks_doc ON chunks(doc_id);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(chunk_id UNINDEXED, grams);

CREATE TABLE IF NOT EXISTS observations (
  source TEXT NOT NULL,
  dataset TEXT NOT NULL,      -- 예: datalab_search, kosis:101/DT_xxx, wb:NY.GDP.MKTP.CD
  series_key TEXT NOT NULL,   -- 예: 키워드그룹명, 국가코드, 분류조합
  query_sig TEXT NOT NULL,    -- 같은 조회 조건끼리만 비교 가능 (네이버 상대지수 등)
  period TEXT NOT NULL,
  value REAL,
  unit TEXT,
  dims_json TEXT,
  retrieved_at TEXT NOT NULL,
  PRIMARY KEY (source, dataset, series_key, query_sig, period)
);

CREATE TABLE IF NOT EXISTS records (
  source TEXT NOT NULL,
  dataset TEXT NOT NULL,
  version TEXT NOT NULL,
  row_hash TEXT NOT NULL,
  row_json TEXT NOT NULL,
  retrieved_at TEXT NOT NULL,
  PRIMARY KEY (source, dataset, row_hash)
);
CREATE INDEX IF NOT EXISTS ix_records ON records(source, dataset, version);

CREATE TABLE IF NOT EXISTS dataset_versions (
  source TEXT NOT NULL,
  dataset TEXT NOT NULL,
  version TEXT NOT NULL,
  label TEXT,
  rows INTEGER,
  ingested_at TEXT NOT NULL,
  PRIMARY KEY (source, dataset, version)
);

CREATE TABLE IF NOT EXISTS query_cache (
  cache_key TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  params_json TEXT,
  result_json TEXT,
  fetched_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_hash(obj: Any) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    @contextmanager
    def tx(self):
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    # ------------------------------------------------------------------ runs
    def start_run(self, source: str, job: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO fetch_runs(source, job, started_at, status) VALUES (?,?,?,'running')",
            (source, job, now_iso()),
        )
        self.conn.commit()
        return cur.lastrowid

    def finish_run(self, run_id: int, status: str, items: int = 0, message: str = "") -> None:
        self.conn.execute(
            "UPDATE fetch_runs SET finished_at=?, status=?, items=?, message=? WHERE id=?",
            (now_iso(), status, items, message[:2000], run_id),
        )
        self.conn.commit()

    def last_success(self, source: str, job: str) -> datetime | None:
        row = self.conn.execute(
            "SELECT finished_at FROM fetch_runs WHERE source=? AND job=? AND status='ok' "
            "ORDER BY finished_at DESC LIMIT 1",
            (source, job),
        ).fetchone()
        return datetime.fromisoformat(row[0]) if row else None

    def run_summary(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            """SELECT source, job,
                      MAX(CASE WHEN status='ok' THEN finished_at END) AS last_ok,
                      (SELECT status FROM fetch_runs r2 WHERE r2.source=r.source AND r2.job=r.job
                         ORDER BY id DESC LIMIT 1) AS last_status,
                      (SELECT message FROM fetch_runs r2 WHERE r2.source=r.source AND r2.job=r.job
                         ORDER BY id DESC LIMIT 1) AS last_message
               FROM fetch_runs r GROUP BY source, job ORDER BY source, job"""
        ).fetchall()

    # ------------------------------------------------------------- documents
    def upsert_document(
        self,
        *,
        source: str,
        doc_type: str,
        original_id: str,
        title: str,
        body: str,
        url: str | None = None,
        published_at: str | None = None,
        license: str | None = None,
        meta: dict | None = None,
    ) -> bool:
        """문서를 저장하고 청크 색인을 갱신한다. 내용이 바뀌었을 때만 True."""
        doc_id = f"{source}:{doc_type}:{original_id}"
        content_hash = stable_hash([title, body])
        old = self.conn.execute(
            "SELECT content_hash FROM documents WHERE doc_id=?", (doc_id,)
        ).fetchone()
        if old and old[0] == content_hash:
            self.conn.execute(
                "UPDATE documents SET retrieved_at=? WHERE doc_id=?", (now_iso(), doc_id)
            )
            return False
        self.conn.execute(
            """INSERT INTO documents(doc_id, source, doc_type, title, body, url, published_at,
                                     retrieved_at, license, original_id, content_hash, meta_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(doc_id) DO UPDATE SET title=excluded.title, body=excluded.body,
                 url=excluded.url, published_at=excluded.published_at,
                 retrieved_at=excluded.retrieved_at, license=excluded.license,
                 content_hash=excluded.content_hash, meta_json=excluded.meta_json""",
            (
                doc_id, source, doc_type, title, body, url, published_at, now_iso(),
                license, original_id, content_hash,
                json.dumps(meta or {}, ensure_ascii=False, default=str),
            ),
        )
        old_chunks = [r[0] for r in self.conn.execute(
            "SELECT chunk_id FROM chunks WHERE doc_id=?", (doc_id,))]
        if old_chunks:
            self.conn.executemany("DELETE FROM chunks_fts WHERE chunk_id=?", [(c,) for c in old_chunks])
            self.conn.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
        pieces = chunk_text(body) or [title or ""]
        for i, piece in enumerate(pieces):
            cid = f"{doc_id}#{i}"
            self.conn.execute(
                "INSERT INTO chunks(chunk_id, doc_id, seq, text) VALUES (?,?,?,?)",
                (cid, doc_id, i, piece),
            )
            # 제목을 각 청크 색인에 함께 넣어 제목어로도 찾히게 한다
            self.conn.execute(
                "INSERT INTO chunks_fts(chunk_id, grams) VALUES (?,?)",
                (cid, to_index_text(f"{title}\n{piece}")),
            )
        return True

    def search(
        self,
        query: str,
        *,
        sources: Iterable[str] | None = None,
        doc_types: Iterable[str] | None = None,
        limit: int = 8,
    ) -> list[dict]:
        match = to_match_query(query)
        if not match:
            return []
        sql = """SELECT c.chunk_id, c.text, d.doc_id, d.source, d.doc_type, d.title, d.url,
                        d.published_at, d.retrieved_at, d.license, d.meta_json,
                        bm25(chunks_fts) AS score
                 FROM chunks_fts JOIN chunks c ON c.chunk_id = chunks_fts.chunk_id
                 JOIN documents d ON d.doc_id = c.doc_id
                 WHERE chunks_fts MATCH ?"""
        args: list[Any] = [match]
        if sources:
            s = list(sources)
            sql += f" AND d.source IN ({','.join('?' * len(s))})"
            args += s
        if doc_types:
            t = list(doc_types)
            sql += f" AND d.doc_type IN ({','.join('?' * len(t))})"
            args += t
        sql += " ORDER BY score LIMIT ?"
        args.append(limit)
        rows = self.conn.execute(sql, args).fetchall()
        return [
            {
                "doc_id": r["doc_id"], "source": r["source"], "doc_type": r["doc_type"],
                "title": r["title"], "text": r["text"], "url": r["url"],
                "published_at": r["published_at"], "retrieved_at": r["retrieved_at"],
                "license": r["license"], "meta": json.loads(r["meta_json"] or "{}"),
                "score": round(-r["score"], 3),
            }
            for r in rows
        ]

    # ---------------------------------------------------------- observations
    def upsert_observations(self, rows: Iterable[dict]) -> int:
        n = 0
        ts = now_iso()
        for r in rows:
            self.conn.execute(
                """INSERT INTO observations(source, dataset, series_key, query_sig, period, value,
                                            unit, dims_json, retrieved_at)
                   VALUES (?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(source, dataset, series_key, query_sig, period) DO UPDATE SET
                     value=excluded.value, unit=excluded.unit, dims_json=excluded.dims_json,
                     retrieved_at=excluded.retrieved_at""",
                (
                    r["source"], r["dataset"], r["series_key"], r.get("query_sig", ""),
                    str(r["period"]), r.get("value"), r.get("unit"),
                    json.dumps(r.get("dims") or {}, ensure_ascii=False), ts,
                ),
            )
            n += 1
        return n

    def get_series(
        self,
        *,
        source: str | None = None,
        dataset: str | None = None,
        series_like: str | None = None,
        query_sig: str | None = None,
        limit: int = 2000,
    ) -> list[dict]:
        sql = "SELECT * FROM observations WHERE 1=1"
        args: list[Any] = []
        for col, val in (("source", source), ("dataset", dataset), ("query_sig", query_sig)):
            if val:
                sql += f" AND {col}=?"
                args.append(val)
        if series_like:
            sql += " AND series_key LIKE ?"
            args.append(f"%{series_like}%")
        sql += " ORDER BY dataset, series_key, query_sig, period LIMIT ?"
        args.append(limit)
        out = []
        for r in self.conn.execute(sql, args):
            d = dict(r)
            d["dims"] = json.loads(d.pop("dims_json") or "{}")
            out.append(d)
        return out

    # --------------------------------------------------------------- records
    def insert_records(self, source: str, dataset: str, version: str, rows: Iterable[dict]) -> int:
        n = 0
        ts = now_iso()
        seen: dict[str, int] = {}
        for row in rows:
            h = stable_hash(row)
            # ID 칸이 없는 데이터(예: 피해구제)는 같은 내용의 서로 다른 행이 있으므로, 한 번에 받은 묶음 안의
            # k번째 동일 행은 따로 저장한다. 다른 버전에 같은 행이 다시 오면 같은 해시가 되어 건너뛴다.
            k = seen.get(h, 0)
            seen[h] = k + 1
            if k:
                h = stable_hash({"row_hash": h, "dup": k})
            cur = self.conn.execute(
                """INSERT OR IGNORE INTO records(source, dataset, version, row_hash, row_json, retrieved_at)
                   VALUES (?,?,?,?,?,?)""",
                (source, dataset, version, h, json.dumps(row, ensure_ascii=False, default=str), ts),
            )
            n += cur.rowcount
        return n

    def find_records(
        self, *, source: str | None = None, dataset: str | None = None,
        contains: str | None = None, limit: int = 200,
    ) -> list[dict]:
        sql = "SELECT source, dataset, version, row_json, retrieved_at FROM records WHERE 1=1"
        args: list[Any] = []
        if source:
            sql += " AND source=?"; args.append(source)
        if dataset:
            sql += " AND dataset=?"; args.append(dataset)
        if contains:
            sql += " AND row_json LIKE ?"; args.append(f"%{contains}%")
        sql += " ORDER BY version DESC LIMIT ?"
        args.append(limit)
        return [
            {"source": r[0], "dataset": r[1], "version": r[2], "row": json.loads(r[3]), "retrieved_at": r[4]}
            for r in self.conn.execute(sql, args)
        ]

    # -------------------------------------------------------------- versions
    def has_version(self, source: str, dataset: str, version: str) -> bool:
        return self.conn.execute(
            "SELECT 1 FROM dataset_versions WHERE source=? AND dataset=? AND version=?",
            (source, dataset, version),
        ).fetchone() is not None

    def mark_version(self, source: str, dataset: str, version: str, label: str, rows: int) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO dataset_versions(source, dataset, version, label, rows, ingested_at)
               VALUES (?,?,?,?,?,?)""",
            (source, dataset, version, label, rows, now_iso()),
        )

    # ----------------------------------------------------------------- cache
    def cache_get(self, source: str, params: dict) -> Any | None:
        key = f"{source}:{stable_hash(params)}"
        row = self.conn.execute(
            "SELECT result_json, expires_at FROM query_cache WHERE cache_key=?", (key,)
        ).fetchone()
        if not row:
            return None
        if datetime.fromisoformat(row[1]) < datetime.now(timezone.utc):
            return None
        return json.loads(row[0])

    def cache_put(self, source: str, params: dict, result: Any, ttl_hours: float) -> None:
        key = f"{source}:{stable_hash(params)}"
        now = datetime.now(timezone.utc).replace(microsecond=0)
        self.conn.execute(
            """INSERT OR REPLACE INTO query_cache(cache_key, source, params_json, result_json, fetched_at, expires_at)
               VALUES (?,?,?,?,?,?)""",
            (
                key, source, json.dumps(params, ensure_ascii=False, default=str),
                json.dumps(result, ensure_ascii=False, default=str),
                now.isoformat(), (now + timedelta(hours=ttl_hours)).isoformat(),
            ),
        )
        self.conn.commit()

    # ----------------------------------------------------------------- stats
    def stats(self) -> dict:
        q = lambda s: self.conn.execute(s).fetchall()
        return {
            "documents": [dict(r) for r in q(
                "SELECT source, doc_type, COUNT(*) n FROM documents GROUP BY source, doc_type")],
            "observations": [dict(r) for r in q(
                "SELECT source, COUNT(DISTINCT dataset) datasets, COUNT(*) n FROM observations GROUP BY source")],
            "records": [dict(r) for r in q(
                "SELECT source, dataset, COUNT(*) n FROM records GROUP BY source, dataset")],
        }
