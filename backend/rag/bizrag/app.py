"""설정 로드, 커넥터 생성, 주기 판단(sync)."""
from __future__ import annotations

import os
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from dotenv import dotenv_values

from .connectors import REGISTRY, ApiError, Connector, Job
from .store import Store

ROOT = Path(os.environ.get("BIZRAG_HOME", Path(__file__).resolve().parent.parent))

CADENCE = {
    "daily": timedelta(hours=20),
    "weekly": timedelta(days=6, hours=20),
    "monthly": timedelta(days=27),
    "quarterly": timedelta(days=85),
}


class App:
    def __init__(self, root: Path | str = ROOT, store: Store | None = None, http=None):
        self.root = Path(root)
        cfg_path = self.root / "config" / "sources.yaml"
        self.cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
        env_file = self.root / ".env"
        self.env = {**(dotenv_values(env_file) if env_file.exists() else {}), **{
            k: v for k, v in os.environ.items() if k.isupper()}}
        db = self.cfg.get("database", "data/knowledge.db")
        self.store = store or Store(self.root / db)
        self.connectors: dict[str, Connector] = {}
        for name, cls in REGISTRY.items():
            ccfg = (self.cfg.get("sources") or {}).get(name, {}) or {}
            if name == "inbox":
                ccfg = {**ccfg, "path": str(self.root / ccfg.get("path", "inbox"))}
            c =cls(ccfg, self.env, self.store, http) if http else cls(ccfg, self.env, self.store)
            if c.enabled:
                self.connectors[name] = c

    def get(self, name: str):
        if name not in self.connectors:
            raise ApiError("config", f"'{name}' 소스가 비활성화되어 있음")
        return self.connectors[name]

    # ----------------------------------------------------------- check
    def check(self, only: list[str] | None = None):
        return [c.check() for n, c in self.connectors.items() if not only or n in only]

    # ------------------------------------------------------------ sync
    def all_jobs(self) -> list[Job]:
        jobs: list[Job] = []
        for c in self.connectors.values():
            jobs.extend(c.jobs())
        return jobs

    def is_due(self, job: Job, now: datetime | None = None) -> tuple[bool, str]:
        last = self.store.last_success(job.source, job.name)
        if last is None:
            return True, "최초 수집"
        now = now or datetime.now(timezone.utc)
        nxt = last + CADENCE.get(job.cadence, CADENCE["monthly"])
        if now >= nxt:
            return True, f"주기 도래 (마지막 {last:%Y-%m-%d})"
        return False, f"다음 수집 {nxt.astimezone():%Y-%m-%d %H:%M}"

    def sync(self, force: bool = False, only: list[str] | None = None, log=print) -> list[dict]:
        results = []
        for job in self.all_jobs():
            if only and job.source not in only:
                continue
            due, why = self.is_due(job)
            if not (due or force):
                log(f"  · {job.source}/{job.name}: 건너뜀 — {why}")
                results.append({"job": f"{job.source}/{job.name}", "status": "skipped", "why": why})
                continue
            log(f"  ▶ {job.source}/{job.name} ({job.cadence}) — {job.description}")
            run_id = self.store.start_run(job.source, job.name)
            try:
                n = job.run()
                self.store.conn.commit()
                self.store.finish_run(run_id, "ok", n, why)
                log(f"    ✓ {n}건 저장")
                results.append({"job": f"{job.source}/{job.name}", "status": "ok", "items": n})
            except ApiError as e:
                self.store.conn.rollback()
                self.store.finish_run(run_id, "error", 0, str(e))
                log(f"    ✗ {e}")
                results.append({"job": f"{job.source}/{job.name}", "status": "error", "error": str(e)})
            except Exception as e:
                self.store.conn.rollback()
                self.store.finish_run(run_id, "error", 0, f"{type(e).__name__}: {e}")
                log(f"    ✗ {type(e).__name__}: {e}")
                if os.environ.get("BIZRAG_DEBUG"):
                    traceback.print_exc()
                results.append({"job": f"{job.source}/{job.name}", "status": "error", "error": str(e)})
        return results
