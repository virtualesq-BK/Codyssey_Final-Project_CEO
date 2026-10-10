"""수동 투입 폴더 (inbox/).

자동 API가 없는 자료(예: 국가데이터처 온라인 수집 가격 정보 CSV)를 inbox/<데이터셋이름>/ 에 넣으면
다음 sync 때 records로 적재하고 inbox/_done/ 으로 옮긴다. 인코딩(UTF-8/CP949) 자동 판별.
"""
from __future__ import annotations

import csv
import io
import shutil
from datetime import datetime
from pathlib import Path

from .base import Connector, Job


def read_csv_any(path: Path) -> list[dict]:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")
    return [dict(r) for r in csv.DictReader(io.StringIO(text))]


class Inbox(Connector):
    name = "inbox"
    title = "수동 투입 폴더 (CSV)"
    key_envs = ()
    signup_url = "키 불필요"

    @property
    def root(self) -> Path:
        return Path(self.cfg.get("path", "inbox"))

    def _check(self) -> str:
        self.root.mkdir(parents=True, exist_ok=True)
        pending = [p for p in self.root.rglob("*.csv") if "_done" not in p.parts]
        return f"대기 중 CSV {len(pending)}개 ({self.root.resolve()})"

    def jobs(self) -> list[Job]:
        return [Job(self.name, "csv", "daily", self.sync, "inbox/ 폴더의 CSV 적재")]

    def sync(self) -> int:
        self.root.mkdir(parents=True, exist_ok=True)
        done = self.root / "_done"
        n = 0
        for p in sorted(self.root.rglob("*.csv")):
            if "_done" in p.parts:
                continue
            dataset = p.parent.name if p.parent != self.root else p.stem
            rows = read_csv_any(p)
            version = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y%m%d") + ":" + p.name
            n += self.store.insert_records("inbox", dataset, version, rows)
            self.store.mark_version("inbox", dataset, version, p.name, len(rows))
            self.store.conn.commit()
            dest = done / dataset
            dest.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), dest / p.name)
        return n
