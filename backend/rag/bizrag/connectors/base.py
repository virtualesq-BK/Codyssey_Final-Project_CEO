"""커넥터 공통 부분: HTTP 호출, 오류 원인 분류, 수집 작업(Job) 정의."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

import requests

from ..store import Store

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 bizrag/0.1"
)

# 오류 종류 -> 사용자에게 보여줄 설명
ERROR_KINDS = {
    "missing_key": "키가 .env에 없음",
    "auth": "인증 실패 (키 값 확인)",
    "not_approved": "활용신청/권한 미승인",
    "quota": "호출 한도 초과",
    "maintenance": "제공기관 점검/일시 장애",
    "input": "요청 파라미터 오류",
    "no_data": "조회 결과 없음",
    "network": "네트워크 연결 실패",
    "server": "제공기관 서버 오류",
    "config": "설정 필요",
    "unknown": "알 수 없는 오류",
}


class ApiError(Exception):
    def __init__(self, kind: str, message: str, hint: str = ""):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.hint = hint

    def __str__(self) -> str:
        label = ERROR_KINDS.get(self.kind, self.kind)
        s = f"[{label}] {self.message}"
        return f"{s} → {self.hint}" if self.hint else s


@dataclass
class CheckResult:
    source: str
    title: str
    ok: bool
    message: str
    kind: str = ""
    hint: str = ""
    sub: list["CheckResult"] = field(default_factory=list)


@dataclass
class Job:
    source: str
    name: str
    cadence: str  # daily | weekly | monthly | quarterly
    run: Callable[[], int]  # 저장한 항목 수를 반환
    description: str = ""


class Http:
    def __init__(self, timeout: float = 25, retries: int = 2, sleep: float = 0.15):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = USER_AGENT
        self.timeout = timeout
        self.retries = retries
        self.sleep = sleep

    def request(self, method: str, url: str, **kw) -> requests.Response:
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                resp = self.s.request(method, url, timeout=self.timeout, **kw)
                if resp.status_code in (502, 503, 504) and attempt < self.retries:
                    time.sleep(1.0 + attempt)
                    continue
                time.sleep(self.sleep)  # 제공기관 부하 방지
                return resp
            except requests.RequestException as e:  # 연결 실패, 타임아웃
                last = e
                time.sleep(1.0 + attempt)
        host = url.split("/")[2] if "//" in url else url
        raise ApiError("network", f"{host} 연결 실패 ({type(last).__name__})",
                       "인터넷 연결·회사 방화벽/프록시 확인")

    def get(self, url: str, **kw) -> requests.Response:
        return self.request("GET", url, **kw)

    def post(self, url: str, **kw) -> requests.Response:
        return self.request("POST", url, **kw)


def status_to_kind(code: int) -> str:
    if code in (401,):
        return "auth"
    if code in (403,):
        return "not_approved"
    if code == 429:
        return "quota"
    if code in (400, 404, 422):
        return "input"
    if code >= 500:
        return "server"
    return "unknown"


class Connector:
    """모든 소스의 공통 인터페이스.

    - check(): 키/권한이 실제로 동작하는지 최소 호출로 확인
    - jobs():  주기 수집 작업 목록 (sync가 실행 시점을 판단)
    - 그 밖의 public 메서드: 에이전트가 검색 시 부르는 on-demand 조회 (결과는 DB에 저장되고 캐시됨)
    """

    name = "base"
    title = "base"
    key_envs: tuple[str, ...] = ()
    signup_url = ""
    license = ""

    def __init__(self, cfg: dict, env: dict, store: Store, http: Http | None = None):
        self.cfg = cfg or {}
        self.env = env
        self.store = store
        self.http = http or Http()

    @property
    def enabled(self) -> bool:
        return self.cfg.get("enabled", True)

    def key(self, name: str) -> str:
        v = (self.env.get(name) or "").strip()
        if not v:
            raise ApiError("missing_key", f"{name} 값이 비어 있음", f"발급: {self.signup_url}")
        return v

    def missing_keys(self) -> list[str]:
        return [k for k in self.key_envs if not (self.env.get(k) or "").strip()]

    def check(self) -> CheckResult:
        missing = self.missing_keys()
        if missing:
            return CheckResult(self.name, self.title, False, f"{', '.join(missing)} 미입력",
                               "missing_key", f"발급: {self.signup_url}")
        try:
            msg = self._check()
            return CheckResult(self.name, self.title, True, msg)
        except ApiError as e:
            return CheckResult(self.name, self.title, False, e.message, e.kind, e.hint)
        except Exception as e:  # 파싱 오류 등
            return CheckResult(self.name, self.title, False, f"{type(e).__name__}: {e}", "unknown")

    def _check(self) -> str:
        raise NotImplementedError

    def jobs(self) -> list[Job]:
        return []

    def cached(self, cache_name: str, params: dict, ttl_hours: float, fn: Callable[[], Any]) -> Any:
        """검색 시 호출(on-demand) 공통 래퍼: 캐시가 살아 있으면 API를 부르지 않는다."""
        hit = self.store.cache_get(cache_name, params)
        if hit is not None:
            if isinstance(hit, dict):
                hit = {**hit, "_cache": "hit"}
            return hit
        result = fn()
        self.store.conn.commit()
        self.store.cache_put(cache_name, params, result, ttl_hours)
        return result
