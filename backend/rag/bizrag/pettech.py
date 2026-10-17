"""Isolated, provenance-preserving pet market statistics collector.

python -m bizrag.pettech collect
python -m bizrag.pettech search "1인 가구 양육비"
python -m bizrag.pettech mcp
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import requests
import yaml
from dotenv import dotenv_values

from .connectors.kosis import parse_kosis_json
from .store import Store, now_iso, stable_hash
from .util import to_float

ROOT = Path(__file__).resolve().parents[1]


def pinecone_status(output):
    """Keep remote verification valid only while the exported corpus is unchanged."""
    report_path=output/'pinecone_upload.json'
    payload=output/'exports/pinecone_chunks.jsonl'
    if report_path.exists() and payload.exists():
        report=json.loads(report_path.read_text(encoding='utf-8'))
        current=hashlib.sha256(payload.read_bytes()).hexdigest()
        if report.get('status')=='verified' and report.get('corpus_sha256')==current:
            return {'pinecone_uploaded':True,'pinecone':report}
    return {'pinecone_uploaded':False}


SEOUL = timezone(timedelta(hours=9))
NOTES = {
    'kosis': '2025년 표본조사 공표값. 사례수는 전국 반려가구 총수가 아니다. 중복응답 비율은 합계 100%가 아닐 수 있다. 특성별 결과는 교차결합할 수 없다. 평균 양육 수를 전국 총 마리 수로 해석하지 않는다.',
    'ecos': '소비자물가지수(2020=100)는 가격 수준의 상대지표이며, 시장 매출액·가구 지출액이 아니다. 전년동월 대비는 같은 품목의 12개월 전 값과 비교한다.',
    'naver': 'NAVER 검색 관심도·쇼핑 클릭 추이는 동일 요청 내 최대=100인 상대지수이며 절대 검색량·판매량·고객수·구매전환율이 아니다. query_sig가 다른 요청의 지수는 직접 비교하지 않는다. 연령·성별 필터 지수로 이용자 구성비를 산출하지 않는다. 키워드는 전체 시장을 포괄하지 않는다.',
}


def dump(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def number(value):
    result = to_float(value)
    return result if result is not None and math.isfinite(result) else None


def pct(current, previous):
    if current is None or previous in (None, 0):
        return None
    return round((current / previous - 1) * 100, 4)


def month_start(end: date, count: int):
    index = end.year * 12 + end.month - count
    return date(index // 12, index % 12 + 1, 1)


def dimension_labels(items: list[dict]):
    """Qualify repeated labels such as '20대' by their parent (householder/carer)."""
    lookup = {(r.get('OBJ_ID'), r.get('ITM_ID')): r for r in items}
    out = {}
    for key, r in lookup.items():
        parts, seen, node = [], set(), r
        while node and node.get('ITM_ID') not in seen:
            seen.add(node.get('ITM_ID'))
            parts.insert(0, node.get('ITM_NM', ''))
            node = lookup.get((r.get('OBJ_ID'), node.get('UP_ITM_ID')))
        out[key] = ' > '.join(filter(None, parts))
    return out


class Collector:
    def __init__(self, cfg_path=ROOT / 'config/pettech.yaml', env_path=ROOT / 'new.env', as_of=None, offline=False):
        self.cfg = yaml.safe_load(Path(cfg_path).read_text(encoding='utf-8'))
        self.output = ROOT / self.cfg['output']
        self.env = {**dotenv_values(env_path), **{k: v for k, v in os.environ.items() if k.isupper()}}
        self.as_of = as_of or datetime.now(SEOUL).date()
        self.end = self.as_of.replace(day=1) - timedelta(days=1)
        self.db = Store(self.output / 'knowledge.db')
        self.http = requests.Session()
        self.http.headers['User-Agent'] = 'bizrag-pettech/1.0 (public statistical research)'
        self.results = []
        self.offline = offline
        self.captured = {}

    def close(self):
        self.http.close()
        self.db.close()

    def key(self, name):
        key = self.env.get(name)
        if not key:
            raise ValueError(f'{name} is missing in new.env')
        return key

    def request(self, method, url, **kwargs):
        for attempt in range(3):
            try:
                r = self.http.request(method, url, timeout=(10, 55), **kwargs)
            except requests.RequestException as exc:
                if attempt < 2:
                    time.sleep(1 + attempt)
                    continue
                # requests exceptions include URLs with API keys; do not propagate them.
                raise RuntimeError(f'network: {type(exc).__name__}') from None
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(2 + attempt)
                continue
            if r.status_code != 200:
                raise RuntimeError(f'HTTP {r.status_code}')
            time.sleep(.12)
            return r

    def raw(self, source, label, params, data):
        # params are explicitly built without authentication fields.
        envelope={'source':source,'retrieved_at':now_iso(),'request':params,'response':data}
        target=self.output/'raw'/source/f'{label}.json'
        if source=='naver':
            if target.exists():
                previous=json.loads(target.read_text(encoding='utf-8'))
                self.archive_raw(label,previous)
            self.archive_raw(label,envelope)
        dump(target,envelope)
        self.captured[source,label]=envelope['retrieved_at']

    def archive_raw(self,label,envelope):
        stamp=envelope['retrieved_at'].replace(':','').replace('+','_')
        dump(self.output/'raw/naver/history'/label/f'{stamp}_{stable_hash(envelope)[:8]}.json',envelope)

    def replay(self, source, label, params):
        envelope=json.loads((self.output/'raw'/source/f'{label}.json').read_text(encoding='utf-8'))
        if envelope['request'] != params:
            raise ValueError('Saved raw request differs from current configuration')
        self.captured[source,label]=envelope['retrieved_at']
        return envelope['response']

    def kosis(self, endpoint, params, label):
        if self.offline:
            return self.replay('kosis',label,params)
        r = self.request('GET', f'https://kosis.kr/openapi/{endpoint}', params={
            'apiKey': self.key('KOSIS_API_KEY'), 'format': 'json', 'jsonVD': 'Y', **params})
        data = parse_kosis_json(r.text)
        if isinstance(data, dict):
            raise RuntimeError(f"KOSIS error {data.get('err') or data.get('errCode') or 'unexpected response'}")
        if not isinstance(data, list):
            raise RuntimeError('KOSIS response is not a list')
        self.raw('kosis', label, params, data)
        return data

    def ecos(self, service, suffix, label, params):
        if self.offline:
            return self.replay('ecos',label,params)[service]
        key = self.key('BOK_API_KEY')
        r = self.request('GET', f'https://ecos.bok.or.kr/api/{service}/{key}/json/kr/{suffix}')
        data = r.json()
        if service not in data:
            raise RuntimeError(f"ECOS error {(data.get('RESULT') or {}).get('CODE','unexpected response')}")
        self.raw('ecos', label, params, data)
        return data[service]

    def job(self, source, label, fn):
        run = self.db.start_run(source, label)
        before = self.db.conn.execute('SELECT COUNT(*) FROM observations WHERE source=?',(source,)).fetchone()[0]
        result_start = len(self.results)
        try:
            count = fn()
            if any(r['status']=='error' for r in self.results[result_start:]):
                raise RuntimeError('One or more source jobs failed; inspect individual run records')
            if count is None:
                count = self.db.conn.execute('SELECT COUNT(*) FROM observations WHERE source=?',(source,)).fetchone()[0] - before
            self.db.conn.commit()
            self.db.finish_run(run, 'ok', count)
            result = {'source': source, 'job': label, 'status': 'ok', 'rows': count}
        except Exception as exc:
            self.db.conn.rollback()
            # Defense in depth: sanitize any third-party exception before persistence.
            message = str(exc)
            for key in ('KOSIS_API_KEY', 'BOK_API_KEY', 'NAVER_CLIENT_ID', 'NAVER_CLIENT_SECRET'):
                secret = self.env.get(key)
                if secret:
                    message = message.replace(secret, '[REDACTED]')
            message = message[:400]
            self.db.finish_run(run, 'error', message=message)
            result = {'source': source, 'job': label, 'status': 'error', 'error': message}
        self.results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)

    def document(self, source, oid, title, body, url, meta):
        meta=dict(meta)
        dataset=meta.get('dataset','')
        if source=='kosis' and dataset:
            raw_label=dataset.rsplit('/',1)[-1]+'_data'
        elif source=='ecos' and dataset and meta.get('item_code'):
            raw_label=f"{dataset.split(':')[1]}_{meta['item_code']}_{meta['cycle']}"
        else:
            raw_label=meta.get('raw_label') or meta.get('query_sig')
        captured=self.captured.get((source,raw_label))
        raw_path=self.output/'raw'/source/f'{raw_label}.json'
        if not captured and raw_path.exists():
            captured=json.loads(raw_path.read_text(encoding='utf-8'))['retrieved_at']
        captured=captured or now_iso()
        meta.update(collected_at=captured,collected_at_kst=datetime.fromisoformat(captured).astimezone(SEOUL).isoformat())
        meta.setdefault('period_start',meta.get('period','공표표 참조'))
        meta.setdefault('period_end',meta.get('period',meta['period_start']))
        body=(f"데이터 기간: {meta['period_start']} ~ {meta['period_end']}\n"
              f"수집일(KST): {meta['collected_at_kst']}\n"+body)
        self.db.upsert_document(source=source, doc_type='pet_statistics', original_id=oid,
            title=title, body=body, url=url, license={'kosis':'KOSIS 통계자료 이용조건',
            'ecos':'한국은행 ECOS 통계자료 이용조건', 'naver':'NAVER API HUB 이용약관'}[source],
            meta={'domain':'pettech', 'note': NOTES[source], **meta})
        # Rebuilding a saved snapshot must retain the ORIGINAL API collection time.
        self.db.conn.execute('UPDATE documents SET retrieved_at=? WHERE doc_id=?',
                             (captured,f'{source}:pet_statistics:{oid}'))

    def collect_kosis(self):
        tables = self.kosis('statisticsSearch.do', {'method':'getList',
            'searchNm':'반려동물양육현황조사', 'resultCount':100, 'startCount':1}, 'survey_catalog')
        targets = {r['TBL_ID']: r for r in tables if r.get('STAT_NM') == '반려동물양육현황조사'
                   and r.get('ORG_ID') == '114' and r['TBL_ID'].startswith('DT_114063_')}
        if not targets:
            raise RuntimeError('2025 pet survey catalog is empty')
        for tbl, catalog in sorted(targets.items()):
            self.job('kosis', tbl, lambda t=tbl, c=catalog: self.collect_kosis_table(t, c))

    def collect_kosis_table(self, tbl, catalog):
        base = {'method':'getMeta', 'orgId':'114', 'tblId':tbl}
        items = self.kosis('statisticsData.do', {**base,'type':'ITM'}, tbl+'_items')
        periods = self.kosis('statisticsData.do', {**base,'type':'PRD'}, tbl+'_periods')
        year = str(self.cfg['survey_year'])
        if not any(str(p.get('STRT_PRD_DE','')) <= year <= str(p.get('END_PRD_DE','')) for p in periods):
            raise RuntimeError('Requested survey year is not published in this table')
        levels = sorted({int(r['OBJ_ID_SN']) for r in items if str(r.get('OBJ_ID_SN','')).isdigit()})
        params = {'method':'getList', 'orgId':'114','tblId':tbl,'itmId':'ALL','prdSe':'Y',
            'startPrdDe':year, 'endPrdDe':year, **{f'objL{i}':'ALL' for i in levels}}
        rows = self.kosis('Param/statisticsParameterData.do', params, tbl+'_data')
        if not rows or any(str(r.get('PRD_DE')) != year for r in rows):
            raise RuntimeError('Empty or wrong-year survey response')
        label_map = dimension_labels(items)
        obj_by_level = {int(r['OBJ_ID_SN']):r['OBJ_ID'] for r in items if str(r.get('OBJ_ID_SN','')).isdigit()}
        groups = defaultdict(list)
        obs = []
        url = f'https://kosis.kr/statHtml/statHtml.do?orgId=114&tblId={tbl}'
        for r in rows:
            dims, codes = {}, {}
            for i in levels:
                code = r.get(f'C{i}')
                if code is not None:
                    codes[f'C{i}'] = code
                    dims[r.get(f'C{i}_OBJ_NM') or f'분류{i}'] = label_map.get((obj_by_level[i],code),r.get(f'C{i}_NM',str(code)))
            # Keep codes as well as human-readable labels: equal labels need not be the same series.
            series_key = ' | '.join([f'{k}={v}' for k,v in dims.items()] + [r.get('ITM_NM','')])
            value = number(r.get('DT'))
            obs.append({'source':'kosis', 'dataset':f'kosis:114/{tbl}', 'series_key':series_key,
                'query_sig':stable_hash({'codes':codes,'itm':r.get('ITM_ID'),'year':year})[:16],
                'period':year, 'value':value, 'unit':r.get('UNIT_NM'),
                'dims':{'table':catalog['TBL_NM'],'codes':codes,'dimensions':dims,'raw_value':r.get('DT'),
                        'base':catalog.get('ITEM03'), 'url':url, 'request':params}})
            groups[r.get('C1','ALL')].append((dims, r, value))
        self.db.upsert_observations(obs)
        self.db.insert_records('kosis',f'kosis:114/{tbl}',year,rows)
        for c1, group in groups.items():
            header = f"2025년 반려동물양육현황조사 | {catalog['TBL_NM']}"
            context = next(iter(group[0][0].values()), '전체')
            lines = [header, f'특성: {context}', f"조사대상/주석: {catalog.get('ITEM03','공표표 참조')}", NOTES['kosis']]
            for dims,r,v in group:
                fact = ' | '.join(f'{k}: {val}' for k,val in dims.items())
                lines.append(f"{fact} | {r.get('ITM_NM','')} = {r.get('DT')} {r.get('UNIT_NM','')} (2025년)")
            self.document('kosis',f'{tbl}:{year}:{c1}',f'{header} | {context}', '\n'.join(lines),url,
                {'dataset':f'kosis:114/{tbl}','period':year,'base':catalog.get('ITEM03'),
                 'dimensions':{'특성':context},'request':params,'row_count':len(group)})
        return len(rows)

    def collect_ecos(self):
        code = self.cfg['ecos_stat_code']
        data = self.ecos('StatisticItemList',f'1/10000/{code}/','cpi_items',{'stat_code':code})
        if int(data.get('list_total_count',0)) > 10000:
            raise RuntimeError('ECOS item metadata requires pagination')
        items = data['row']
        for item, name in self.cfg['ecos_items'].items():
            for cycle in ('M','A'):
                matches = [r for r in items if r['ITEM_CODE']==item and r['CYCLE']==cycle and r['ITEM_NAME']==name]
                if len(matches) != 1:
                    raise RuntimeError(f'ECOS item metadata mismatch: {item}/{cycle}')
                self.job('ecos',f'{code}:{item}:{cycle}',lambda m=matches[0]: self.collect_ecos_series(m))

    def collect_ecos_series(self, item):
        code, ic, cycle = item['STAT_CODE'],item['ITEM_CODE'],item['CYCLE']
        start = str(self.cfg['ecos_start_year']) + ('01' if cycle=='M' else '')
        cutoff = self.end.strftime('%Y%m') if cycle=='M' else str(self.as_of.year-1)
        end = min(cutoff,item['END_TIME'])
        if start > end:
            raise RuntimeError('ECOS collection period is empty')
        params = {'stat_code':code,'item_code':ic,'item_name':item['ITEM_NAME'], 'cycle':cycle, 'start':start,'end':end}
        result = self.ecos('StatisticSearch', f'1/10000/{code}/{cycle}/{start}/{end}/{ic}/', f'{code}_{ic}_{cycle}',params)
        rows = result.get('row',[])
        if not rows or len(rows)!=int(result['list_total_count']):
            raise RuntimeError('ECOS incomplete or empty response')
        url = 'https://ecos.bok.or.kr/'
        obs = [{'source':'ecos','dataset':f'ecos:{code}', 'series_key':item['ITEM_NAME'],
            'query_sig':cycle,'period':r['TIME'],'value':number(r['DATA_VALUE']),'unit':r['UNIT_NAME'],
            'dims':{'item_code':ic,'cycle':cycle,'weight':item.get('WEIGHT'),'url':url,'request':params,
                    'raw_value':r['DATA_VALUE']}} for r in rows]
        self.db.upsert_observations(obs)
        self.db.insert_records('ecos',f'ecos:{code}:{ic}:{cycle}',end,rows)
        points = {r['TIME']:number(r['DATA_VALUE']) for r in rows}
        changes = []
        for period, val in sorted(points.items()):
            prior_year = str(int(period[:4])-1)+period[4:]
            yoy = pct(val,points.get(prior_year))
            changes.append({'source':'ecos','dataset':f'ecos:{code}:derived_yoy','series_key':item['ITEM_NAME'],
                'query_sig':cycle,'period':period,'value':yoy,'unit':'%',
                'dims':{'item_code':ic,'url':url,'formula':'(current / previous_year_same_period - 1) * 100',
                        'current_value':val,'previous_value':points.get(prior_year),'derived':True}})
        self.db.upsert_observations(changes)
        last = changes[-1]
        lines = [f"ECOS 소비자물가지수 | {item['ITEM_NAME']} | 주기 {cycle}",
                 f"통계표 {code}, 품목 {ic}, 단위 {item['UNIT_NAME']}, 가중치 {item.get('WEIGHT')}",NOTES['ecos'],
                 f"최신 {last['period']}: {last['dims']['current_value']}, 전년 동기 대비 {last['value']}% (계산값)"]
        for p,v in sorted(points.items()):
            lines.append(f"{item['ITEM_NAME']} | {cycle} | {p}: {v} ({item['UNIT_NAME']})")
        self.document('ecos',f'{code}:{ic}:{cycle}',f"반려동물 물가 | {item['ITEM_NAME']} | {cycle}",
            '\n'.join(lines),url,{'dataset':f'ecos:{code}', 'item_code':ic, 'cycle':cycle,
                'unit':item['UNIT_NAME'],'period_start':start,'period_end':end,'request':params,
                'latest_yoy_pct':last['value'], 'weight':item.get('WEIGHT')})
        return len(rows)

    def collect_naver(self):
        for batch,groups in self.cfg['naver_batches'].items():
            for segment,filters in self.cfg['naver_segments'].items():
                self.job('naver',f'{batch}:{segment}',
                         lambda b=batch,g=groups,s=segment,f=filters: self.collect_naver_request(b,g,s,f))

    def collect_shopping(self):
        category=self.cfg['shopping_category']
        for segment,filters in self.cfg['shopping_segments'].items():
            self.job('naver',f'쇼핑분야:{segment}',lambda s=segment,f=filters:
                self.collect_naver_request('쇼핑분야',{category['name']:[category['id']]},s,f,kind='shopping_category'))
        for batch,config in self.cfg['shopping_batches'].items():
            groups={word:[word] for word in config['keywords']}
            for segment,filters in self.cfg['shopping_segments'].items():
                self.job('naver',f'쇼핑키워드:{batch}:{segment}',lambda b=batch,g=groups,s=segment,f=filters,c=config['category']:
                    self.collect_naver_request(b,g,s,f,kind='shopping_keyword',category=c))

    def collect_naver_request(self,batch,groups,segment,filters,kind='search',category=None):
        body = {'startDate':month_start(self.end,self.cfg['naver_months']).isoformat(),
            'endDate':self.end.isoformat(),'timeUnit':'month',**filters}
        if kind=='search':
            body['keywordGroups']=[{'groupName':name,'keywords':words} for name,words in groups.items()]
            endpoint='/search-trend/v1/search'
            dataset='pet_search_trend'
            url='https://datalab.naver.com/keyword/trendSearch.naver'
            metric='검색 관심도'
        else:
            allowed_ages={'10','20','30','40','50','60'}
            if any(age not in allowed_ages for age in filters.get('ages',[])):
                raise ValueError('Invalid shopping age codes')
            url='https://datalab.naver.com/shoppingInsight/sCategory.naver'
            metric='쇼핑 클릭 추이'
            if kind=='shopping_category':
                body['category']=[{'name':name,'param':words} for name,words in groups.items()]
                endpoint='/shopping/v1/categories';dataset='pet_shopping_category'
                if len(groups)>3:raise ValueError('Shopping category limit is 3')
            elif kind=='shopping_keyword':
                if any(len(words)!=1 for words in groups.values()):
                    raise ValueError('Shopping keyword param must contain exactly one keyword')
                body.update(category=category,keyword=[{'name':name,'param':words} for name,words in groups.items()])
                endpoint='/shopping/v1/category/keywords';dataset='pet_shopping_keyword'
            else:raise ValueError('Unknown NAVER request type')
        if not 1 <= len(groups) <= 5:
            raise ValueError('NAVER accepts at most 5 keyword groups')
        sig = stable_hash(body if kind=='search' else {'endpoint':endpoint,'body':body})[:16]
        if self.offline:
            data=self.replay('naver',sig,body)
        else:
            r = self.request('POST','https://naverapihub.apigw.ntruss.com'+endpoint,
                headers={'X-NCP-APIGW-API-KEY-ID':self.key('NAVER_CLIENT_ID'),
                         'X-NCP-APIGW-API-KEY':self.key('NAVER_CLIENT_SECRET')},json=body)
            data = r.json()
        if not data.get('results'):
            raise RuntimeError('NAVER returned no results')
        if {r['title'] for r in data['results']} != set(groups):
            raise RuntimeError('NAVER returned incomplete groups')
        if not self.offline:
            self.raw('naver',sig,body,data)
        captured=self.captured.get(('naver',sig),now_iso())
        rows=[]
        for result in data['results']:
            name = result['title']
            points = result.get('data',[])
            months=[p['period'][:7] for p in points]
            if len(months)!=len(set(months)) or any(p<body['startDate'][:7] or p>body['endDate'][:7] for p in months):
                raise RuntimeError('NAVER returned duplicate or out-of-range monthly points')
            for point in points:
                value=number(point.get('ratio'))
                if value is None or not 0 <= value <= 100:
                    raise RuntimeError('NAVER invalid relative index')
                rows.append({'source':'naver','dataset':dataset,'series_key':name,
                    'query_sig':sig,'period':point['period'],'value':value,'unit':'요청 내 상대지수(최대=100)',
                    'dims':{'batch':batch,'segment':segment,'keywords':groups[name],
                            'filters':filters,'request':body,'url':url,'metric':metric,
                            'api_endpoint':endpoint,'collected_at':captured,
                            'period_start':body['startDate'],'period_end':body['endDate']}})
            latest = max(points,key=lambda p:p['period']) if points else None
            peak = max(points,key=lambda p:p['ratio']) if points else None
            # Sparse API responses are NOT zeroes. Use calendar windows, and only compute
            # a yearly comparison if BOTH twelve-month windows are complete.
            by_month={p['period'][:7]:p['ratio'] for p in points}
            recent_start=month_start(self.end,12).isoformat()[:7]
            previous_start=month_start(self.end,24).isoformat()[:7]
            recent_values=[v for p,v in by_month.items() if recent_start<=p<=self.end.isoformat()[:7]]
            previous_values=[v for p,v in by_month.items() if previous_start<=p<recent_start]
            recent=sum(recent_values)/12 if len(recent_values)==12 else None
            prev=sum(previous_values)/12 if len(previous_values)==12 else None
            expected=[]
            for offset in range(self.cfg['naver_months'],0,-1):
                expected.append(month_start(self.end,offset).isoformat()[:7])
            missing=[p for p in expected if p not in by_month]
            title=f'펫테크 {metric} | {batch} | {segment} | {name}'
            lines=[title,NOTES['naver'],f'query_sig={sig}',f'검색어: {json.dumps(groups[name],ensure_ascii=False)}',
                f'조회필터: {json.dumps(filters,ensure_ascii=False)}',
                (f"최신 {latest['period']}: {latest['ratio']}; 최고점 {peak['period']}: {peak['ratio']}" if latest else '반환된 지수 없음. 검색/클릭이 0이라는 의미로 대체하지 않는다.'),
                f'최근 12개월 평균 {recent}, 직전 12개월 평균 {prev}, 평균 변화율 {pct(recent,prev)}% (계산값)',
                f'요청 {len(expected)}개월 중 {len(points)}개월 반환. 미반환 월 {missing}. 미반환을 0으로 대체하지 않았으며, 12개월이 모두 있을 때만 연간 평균과 변화율을 계산한다.']
            lines.extend(f"{name} | {segment} | query_sig={sig} | {p['period']}: {p['ratio']} 상대지수" for p in points)
            self.document('naver',f'{sig}:{name}',title,'\n'.join(lines),
                url,
                {'dataset':dataset,'query_sig':sig,'batch':batch,'segment':segment,'metric':metric,
                 'api_endpoint':endpoint,'category':body.get('category'),
                 'keywords':groups[name],'filters':filters,'request':body,
                 'period_start':body['startDate'],'period_end':body['endDate'],
                 'returned_months':len(points),'expected_months':len(expected),'missing_months':missing,
                 'recent_12m_avg':recent,'previous_12m_avg':prev,'avg_change_pct':pct(recent,prev)})
        self.db.upsert_observations(rows)
        self.db.conn.execute('UPDATE observations SET retrieved_at=? WHERE source=? AND dataset=? AND query_sig=?',
            (captured,'naver',dataset,sig))
        return len(rows)

    def export(self):
        # Migrate earlier documents using their original raw response timestamps.
        for row in self.db.conn.execute('SELECT * FROM documents').fetchall():
            meta=json.loads(row['meta_json'] or '{}')
            if 'collected_at_kst' not in meta:
                self.document(row['source'],row['original_id'],row['title'],row['body'],row['url'],meta)
        self.db.conn.commit()
        export = self.output / 'exports'
        export.mkdir(parents=True,exist_ok=True)
        for table in ('documents','observations'):
            with (export/f'{table}.jsonl').open('w',encoding='utf-8') as handle:
                for row in self.db.conn.execute(f'SELECT * FROM {table} ORDER BY rowid'):
                    row=dict(row)
                    for col in ('meta_json','dims_json'):
                        if col in row: row[col.removesuffix('_json')]=json.loads(row.pop(col) or '{}')
                    handle.write(json.dumps(row,ensure_ascii=False)+'\n')
        with (export/'observations.csv').open('w',encoding='utf-8-sig',newline='') as handle:
            writer=csv.writer(handle)
            writer.writerow(['source','dataset','series_key','query_sig','period','value','unit','dimensions','retrieved_at'])
            for r in self.db.conn.execute('SELECT * FROM observations ORDER BY source,dataset,series_key,query_sig,period'):
                writer.writerow([r[k] for k in ['source','dataset','series_key','query_sig','period','value','unit','dims_json','retrieved_at']])
        if hasattr(self.db,'export_vectors'):
            embedding_export=self.db.export_vectors(export)
        else:
            self.export_legacy_vectors(export)
            embedding_export=None
        summary=self.summary()
        if embedding_export:summary['embedding_export']=embedding_export
        prior_manifest=self.output/'manifest.json'
        prior_results=json.loads(prior_manifest.read_text(encoding='utf-8')).get('results',[]) if prior_manifest.exists() else []
        dump(self.output/'manifest.json',{'generated_at':now_iso(),'as_of':self.as_of.isoformat(),
            'scope':('Integrated pet statistics, CSV and PDF evidence' if 'statistics_db' in self.cfg else
                     '2025 pet survey + ECOS pet CPI + NAVER pet keyword trends; excludes 2016 report'),
            'database':str(self.output/'knowledge.db'),'results':self.results or prior_results,'counts':summary,
            'notes':NOTES,**pinecone_status(self.output)})
        return summary

    def export_legacy_vectors(self,export):
        with (export/'pinecone_chunks.jsonl').open('w',encoding='utf-8') as handle:
            rows=self.db.conn.execute('SELECT c.*,d.source,d.doc_type,d.title,d.url,d.retrieved_at,d.license,d.meta_json FROM chunks c JOIN documents d USING(doc_id) ORDER BY c.chunk_id')
            for r in rows:
                meta=json.loads(r['meta_json'])
                # Carry document context on EVERY vector, even when the original header is in another chunk.
                context=f"{r['title']}\n출처: {r['source']} | {r['url']}\n데이터 기간: {meta['period_start']} ~ {meta['period_end']}\n수집일(KST): {meta['collected_at_kst']}\n주의: {meta['note']}\n조회조건: {json.dumps(meta,ensure_ascii=False)}"
                record={'id':hashlib.sha1(r['chunk_id'].encode()).hexdigest(),
                    'chunk_id':r['chunk_id'],'doc_id':r['doc_id'],'text':context+'\n'+r['text'],
                    'metadata':{'domain':'pettech','source':r['source'],'doc_type':r['doc_type'],
                        'title':r['title'],'url':r['url'],'retrieved_at':r['retrieved_at'],
                        'collected_at':meta['collected_at'],'collected_at_kst':meta['collected_at_kst'],
                        'period_start':meta['period_start'],'period_end':meta['period_end'],
                        'license':r['license'],'chunk_id':r['chunk_id'],'doc_id':r['doc_id'],
                        'context_json':json.dumps(meta,ensure_ascii=False)}}
                for key in ('source_file','source_sha256','pdf_page','publication_year','historical_source'):
                    if meta.get(key) is not None:
                        record['metadata'][key]=meta[key]
                handle.write(json.dumps(record,ensure_ascii=False)+'\n')

    def summary(self):
        return {'by_source':[dict(r) for r in self.db.conn.execute(
            'SELECT source,COUNT(*) observations,MIN(period) first_period,MAX(period) last_period FROM observations GROUP BY source')],
            'documents':self.db.conn.execute('SELECT COUNT(*) FROM documents').fetchone()[0],
            'chunks':self.db.conn.execute('SELECT COUNT(*) FROM chunks').fetchone()[0],
            'latest_runs':[dict(r) for r in self.db.run_summary()]}

    def collect(self, only):
        for name in only:
            self.job('naver' if name=='shopping' else name,'collect_'+name,{'kosis':self.collect_kosis,'ecos':self.collect_ecos,
                                    'naver':self.collect_naver,'shopping':self.collect_shopping}[name])
        summary=self.export()
        print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
        return 2 if any(r['status']=='error' for r in self.results) else 0


def build_mcp(c):
    """Expose the isolated local corpus through four statistical retrieval tools."""
    from .knowledge import Knowledge
    try:
        from mcp.server.mcpserver import MCPServer as FastMCP
    except ImportError:
        from mcp.server.fastmcp import FastMCP
    from .rag_index import RagStore
    if isinstance(c.db,RagStore):
        class RagKnowledge(Knowledge):
            def search_knowledge(self,query: str,sources: list[str]|None=None,doc_types: list[str]|None=None,
                                 limit: int=8,min_year: int|None=None,include_historical: bool=False)->list[dict]:
                return self.store.search(query,sources=sources,doc_types=doc_types,limit=limit,
                    min_year=min_year,include_historical=include_historical)
        k=RagKnowledge(SimpleNamespace(store=c.db))
    else:k=Knowledge(SimpleNamespace(store=c.db))
    server=FastMCP('bizrag-pettech',instructions='펫테크 통계 근거. 출처·기간·단위·query_sig·조사대상을 확인하고 답변에 출처를 표시한다. NAVER는 절대 검색량이 아니다.')
    for fn in (k.inventory,k.search_knowledge,k.get_series,k.find_records):
        server.tool()(fn)
    return server


def main(argv=None):
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config',type=Path,default=ROOT/'config/pettech.yaml')
    ap.add_argument('--env-file',type=Path,default=ROOT/'new.env')
    ap.add_argument('--as-of',type=date.fromisoformat,default=None)
    sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('collect');p.add_argument('--only',nargs='+',choices=['kosis','ecos','naver','shopping'],default=['kosis','ecos','naver','shopping']);p.add_argument('--offline',action='store_true',help='Rebuild from saved raw responses without calling APIs')
    p=sub.add_parser('search');p.add_argument('query');p.add_argument('--limit',type=int,default=5)
    sub.add_parser('status');sub.add_parser('export');sub.add_parser('mcp')
    args=ap.parse_args(argv)
    c=Collector(args.config,args.env_file,args.as_of,getattr(args,'offline',False))
    if 'statistics_db' in c.cfg:
        from .rag_index import RagStore
        c.db.close();c.db=RagStore(c.output/'knowledge.db')
    try:
        if args.command=='collect':return c.collect(args.only)
        if args.command=='search':result=c.db.search(args.query,limit=args.limit)
        elif args.command=='status':result=c.summary()
        elif args.command=='export':result=c.export()
        else:
            build_mcp(c).run()
            return 0
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    finally:c.close()


if __name__=='__main__':
    raise SystemExit(main())
