"""World Bank 지표 (키 불필요). 월 1회 감시 국가×지표 최신값 갱신 + 검색 시 임의 지표 조회."""
from __future__ import annotations

from .base import ApiError, Connector, Job

BASE = "https://api.worldbank.org/v2"

DEFAULT_INDICATORS = {
    "SP.POP.TOTL": "인구",
    "NY.GDP.MKTP.CD": "GDP(US$)",
    "NY.GDP.PCAP.CD": "1인당 GDP(US$)",
    "NE.CON.PRVT.CD": "가계 최종소비지출(US$)",
    "IT.NET.USER.ZS": "인터넷 이용률(%)",
    "SP.URB.TOTL.IN.ZS": "도시화율(%)",
    "SP.POP.65UP.TO.ZS": "65세 이상 인구비율(%)",
    "FP.CPI.TOTL.ZG": "소비자물가 상승률(%)",
}
DEFAULT_COUNTRIES = ["KOR", "USA", "JPN", "CHN", "VNM", "IDN", "THA", "DEU", "GBR", "IND"]


class WorldBank(Connector):
    name = "worldbank"
    title = "World Bank 지표"
    key_envs = ()
    signup_url = "키 불필요"
    license = "CC BY 4.0 (World Bank)"

    def _get(self, countries: list[str], indicator: str, mrv: int) -> list[dict]:
        url = f"{BASE}/country/{';'.join(countries)}/indicator/{indicator}"
        resp = self.http.get(url, params={"format": "json", "mrv": mrv, "per_page": 2000})
        if resp.status_code != 200:
            raise ApiError("server" if resp.status_code >= 500 else "input", f"HTTP {resp.status_code}")
        data = resp.json()
        if isinstance(data, list) and data and isinstance(data[0], dict) and data[0].get("message"):
            m = data[0]["message"][0]
            raise ApiError("input", f"{m.get('key')}: {m.get('value')}")
        return data[1] if isinstance(data, list) and len(data) > 1 and data[1] else []

    def _check(self) -> str:
        rows = self._get(["KOR"], "SP.POP.TOTL", 1)
        return f"OK (한국 인구 {rows[0]['date']}: {rows[0]['value']:,.0f})" if rows else "OK (빈 결과)"

    def indicator(self, indicator: str, countries: list[str] | None = None, mrv: int = 15) -> dict:
        countries = countries or ["KOR"]
        params = {"i": indicator, "c": sorted(countries), "mrv": mrv}
        return self.cached("wb_indicator", params, 24 * 30, lambda: self._load(indicator, countries, mrv))

    def _load(self, indicator: str, countries: list[str], mrv: int) -> dict:
        rows = self._get(countries, indicator, mrv)
        name = rows[0]["indicator"]["value"] if rows else indicator
        obs = [{"source": "worldbank", "dataset": f"wb:{indicator}", "series_key": r["countryiso3code"] or r["country"]["id"],
                "query_sig": "", "period": r["date"], "value": r["value"], "unit": name,
                "dims": {"country": r["country"]["value"]}} for r in rows if r.get("value") is not None]
        self.store.upsert_observations(obs)
        self.store.conn.commit()
        latest: dict[str, tuple] = {}
        for o in obs:
            k = o["series_key"]
            if k not in latest or o["period"] > latest[k][0]:
                latest[k] = (o["period"], o["value"])
        return {"indicator": indicator, "name": name, "rows": len(obs), "latest": latest}

    def jobs(self) -> list[Job]:
        return [Job(self.name, "indicators", self.cfg.get("cadence", "monthly"), self.sync, "감시 국가×지표 갱신")]

    def sync(self) -> int:
        inds = self.cfg.get("indicators") or DEFAULT_INDICATORS
        countries = self.cfg.get("countries") or DEFAULT_COUNTRIES
        n = 0
        for ind in inds:
            n += self._load(ind, countries, int(self.cfg.get("mrv", 15)))["rows"]
        return n
