"""문서로 확인된 창업진흥원 7개 API의 원문 보존·참고자료 수집기.

새 제공처는 Dataset과 API client를 등록한다. 외부 문서 자동 다운로드는 하지 않는다.
"""
import argparse
import csv
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from uuid import uuid4

from api_catalog import Catalog
from _api_catalog_core import load_env, parse_api_date, stamp

BASE_URL = 'https://apis.data.go.kr/B552735/kisedKstartupService01/'

@dataclass(frozen=True)
class Dataset:
    name: str
    label: str
    operation: str
    title_field: str
    body_fields: tuple
    service: str = 'kstartup'
    base_url: str = BASE_URL
    key_parameter: str = 'serviceKey'
    key_env: str = 'DATA_GO_KR_SERVICE_KEY'
    filters: tuple = ()

DATASETS = {
    'announcements': Dataset('announcements', '지원사업 공고', 'getAnnouncementInformation01', 'biz_pbanc_nm', ('pbanc_ctnt', 'aply_trgt_ctnt', 'aply_trgt', 'biz_enyy', 'biz_trgt_age', 'prfn_matr', 'aply_excl_trgt_ctnt', 'aply_mthd_onli_rcpt_istc', 'aply_mthd_vst_rcpt_istc', 'aply_mthd_pssr_rcpt_istc', 'aply_mthd_fax_rcpt_istc', 'aply_mthd_eml_rcpt_istc', 'aply_mthd_etc_istc')),
    'businesses': Dataset('businesses', '통합공고 지원사업 소개', 'getBusinessInformation01', 'supt_biz_titl_nm', ('supt_biz_intrd_info', 'biz_supt_trgt_info', 'biz_supt_bdgt_info', 'biz_supt_ctnt', 'supt_biz_chrct')),
    'contents': Dataset('contents', '창업관련 콘텐츠', 'getContentInformation01', 'titl_nm', ()),
    'statistics': Dataset('statistics', '창업관련 통계보고서', 'getStatisticalInformation01', 'titl_nm', ('ctnt',)),
    'centers': Dataset('centers', '창업공간 센터 목록', 'getCenterList', 'cntr_nm', ('cntr_intrd_type_nm','cntr_type_nm','buld_nm','regin_clss','addr'), 'space', 'https://apis.data.go.kr/B552735/kisedSlpService/', 'serviceKey', 'KISEDSLP_SERVICE_KEY', ('cntr_nm::LIKE','regin_clss::LIKE')),
    'spaces': Dataset('spaces', '등록센터 공간 목록', 'getCenterSpaceList', 'spce_nm', ('cntr_nm','spce_type_nm','seat_type_nm','seat_clss','excuse_ar','cmnus_ar','rent','guam','rsvt_psbl_clss','addr'), 'space', 'https://apis.data.go.kr/B552735/kisedSlpService/', 'serviceKey', 'KISEDSLP_SERVICE_KEY', ('spce_id::EQ','spce_nm::LIKE','cntr_nm::LIKE','rsvt_psbl_clss::EQ','rent::GTE','rent::LTE','guam::GTE','guam::LTE','addr::LIKE')),
    'education': Dataset('education', '창업에듀 강좌', 'getEducationInformation', 'lctr_nm', ('lctr_istc','kywrd','play_time','lctr_lclss_cd','lctr_mclss_cd','lctr_sclss_cd'), 'education', 'https://apis.data.go.kr/B552735/kisedEduService/', 'ServiceKey', 'KISEDEDU_SERVICE_KEY', ('lctr_lclss_cd::EQ','lctr_mclss_cd::EQ','lctr_sclss_cd::EQ','lctr_nm::LIKE','lctr_istc::LIKE','kywrd::LIKE')),
}

DOMAIN_SCHEMA = '''
CREATE TABLE IF NOT EXISTS reference_centers (
 record_id TEXT PRIMARY KEY REFERENCES reference_records(id),
 center_id TEXT NOT NULL, building_id TEXT NOT NULL, address TEXT,
 region TEXT, latitude REAL, longitude REAL, space_count INTEGER
);
CREATE INDEX IF NOT EXISTS idx_ref_centers_id ON reference_centers(center_id,building_id);
CREATE TABLE IF NOT EXISTS reference_spaces (
 record_id TEXT PRIMARY KEY REFERENCES reference_records(id),
 space_id TEXT NOT NULL, center_id TEXT, building_id TEXT, address TEXT,
 latitude REAL, longitude REAL, rent REAL, deposit REAL, reservation_code TEXT
);
CREATE INDEX IF NOT EXISTS idx_ref_spaces_center ON reference_spaces(center_id,building_id);
CREATE TABLE IF NOT EXISTS reference_education (
 record_id TEXT PRIMARY KEY REFERENCES reference_records(id),
 lecture_url TEXT NOT NULL, large_category TEXT, middle_category TEXT,
 small_category TEXT, keywords TEXT, play_time TEXT
);
'''

SCHEMA = '''
CREATE TABLE IF NOT EXISTS reference_records (
 id TEXT PRIMARY KEY, source TEXT NOT NULL, dataset TEXT NOT NULL, source_key TEXT NOT NULL,
 identity_kind TEXT NOT NULL, title TEXT NOT NULL, body_text TEXT NOT NULL,
 category TEXT, detail_url TEXT, file_name TEXT, published_at TEXT, source_modified_at TEXT,
 business_year TEXT, starts_on TEXT, ends_on TEXT, open_flag TEXT,
 raw_json TEXT NOT NULL, content_hash TEXT NOT NULL,
 first_seen_at TEXT NOT NULL, changed_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
 UNIQUE(source,dataset,source_key)
);
CREATE INDEX IF NOT EXISTS idx_reference_dataset ON reference_records(dataset,title);
CREATE TABLE IF NOT EXISTS reference_versions (
 id TEXT PRIMARY KEY, record_id TEXT NOT NULL REFERENCES reference_records(id),
 content_hash TEXT NOT NULL, raw_json TEXT NOT NULL, observed_at TEXT NOT NULL,
 UNIQUE(record_id,content_hash)
);
CREATE TABLE IF NOT EXISTS reference_sync_runs (
 id TEXT PRIMARY KEY, dataset TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT,
 status TEXT NOT NULL, pages INTEGER NOT NULL DEFAULT 0, records_read INTEGER NOT NULL DEFAULT 0,
 stats_json TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS reference_sync_pages (
 run_id TEXT NOT NULL REFERENCES reference_sync_runs(id), page INTEGER NOT NULL,
 response_json TEXT NOT NULL, fetched_at TEXT NOT NULL, PRIMARY KEY(run_id,page)
);
'''

class ApiError(RuntimeError):
    pass

class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.hidden += 1
        if tag in ('p', 'br', 'div', 'li', 'tr'): self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.hidden = max(0, self.hidden - 1)
        if tag in ('p', 'div', 'li', 'tr'): self.parts.append('\n')
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)

def plain_text(value):
    parser = TextOnly()
    parser.feed(str(value if value is not None else ''))
    return '\n'.join(re.sub(r'\s+', ' ', s).strip() for s in ''.join(parser.parts).splitlines() if s.strip())

def canonical(raw):
    return json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def normalize(raw):
    # 원문은 별도 저장. 문서의 대소문자/철자 차이는 조회용 사본에만 적용.
    r = {str(k).lower(): v for k, v in raw.items()}
    if 'aply_excl_trgt_ctnt' not in r and 'aply_exclt_trgt_ctnt' in r:
        r['aply_excl_trgt_ctnt'] = r['aply_exclt_trgt_ctnt']
    return r

def normalize_url(value):
    text = str(value if value is not None else '').strip()
    if text.startswith('www.'): text = 'https://' + text
    text = text.replace('/web/contents/web/contents/', '/web/contents/')
    parts = urllib.parse.urlsplit(text)
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        return ''
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ''))

def identity(dataset, r):
    if dataset in ('centers','spaces','education'):
        if dataset == 'centers':
            if r.get('cntr_id') in (None,''): raise ValueError('센터 ID 누락')
            return canonical([str(r['cntr_id']),str(r.get('buld_id') if r.get('buld_id') is not None else '')]), 'center_building_id'
        if dataset == 'spaces':
            if r.get('spce_id') in (None,''): raise ValueError('공간 ID 누락')
            return str(r['spce_id']), 'spce_id'
        url = normalize_url(r.get('lctr_pg_url'))
        if not url: raise ValueError('강좌 페이지 URL 누락: 식별키 추정 대신 원문 페이지 로그 확인 필요')
        return url, 'lecture_url'
    if dataset == 'announcements' and r.get('pbanc_sn') not in (None, ''):
        return str(r['pbanc_sn']), 'pbanc_sn'
    url = normalize_url(r.get('detl_pg_url'))
    if dataset in ('contents', 'statistics') and url:
        parts = urllib.parse.urlsplit(url)
        params = urllib.parse.parse_qs(parts.query)
        params.pop('schM', None)
        query = urllib.parse.urlencode(sorted((k,v) for k, vals in params.items() for v in vals))
        return parts.hostname.lower() + parts.path + '?' + query, 'detail_url'
    if dataset == 'businesses':
        values = [r.get('biz_yr'), r.get('biz_category_cd'), r.get('supt_biz_titl_nm')]
        return sha256(canonical(values).encode()).hexdigest(), 'year_category_title'
    values = [r.get(DATASETS[dataset].title_field), r.get('fstm_reg_dt'), r.get('clss_cd')]
    return sha256(canonical(values).encode()).hexdigest(), 'fallback_title_date'

def today_kst():
    return datetime.now(timezone(timedelta(hours=9))).date()

def is_current(r, as_of=None):
    if str(r.get('rcrt_prgs_yn', '')).upper() == 'N': return False
    now = as_of or today_kst()
    for key, future in [('pbanc_rcpt_bgng_dt', True), ('pbanc_rcpt_end_dt', False)]:
        if r.get(key):
            try:
                day = parse_api_date(r[key])
                if (future and day > now) or (not future and day < now): return False
            except ValueError:
                return str(r.get('rcrt_prgs_yn', '')).upper() == 'Y'
    return bool(r.get('pbanc_rcpt_end_dt')) or str(r.get('rcrt_prgs_yn', '')).upper() == 'Y'

def xml_value(node):
    if not list(node): return node.text or ''
    result = {}
    for child in node:
        key = child.tag.rsplit('}', 1)[-1]
        value = xml_value(child)
        if key in result:
            if not isinstance(result[key], list): result[key] = [result[key]]
            result[key].append(value)
        else: result[key] = value
    return result

def decode_payload(data):
    text = data.decode('utf-8-sig').strip()
    if text.startswith('<'):
        if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper(): raise ApiError('허용되지 않은 XML 선언')
        try:
            root = ET.fromstring(text)
            return {root.tag.rsplit('}',1)[-1]: xml_value(root)}
        except ET.ParseError: raise ApiError('API XML 응답 해석 실패') from None
    try: return json.loads(text)
    except (ValueError, UnicodeError): raise ApiError('API JSON 응답 해석 실패') from None

def unpack(payload):
    if not isinstance(payload, dict): raise ApiError('지원하지 않는 API 응답 구조')
    response = payload.get('response') or {}
    header = response.get('header') or payload.get('OpenAPI_ServiceResponse', {}).get('cmmMsgHeader') or {}
    code = header.get('resultCode', header.get('returnReasonCode', payload.get('resultCode')))
    if code is not None and str(code) not in ('00', '0', 'NORMAL_SERVICE'):
        raise ApiError('API 오류 코드: ' + re.sub('[^A-Za-z0-9_-]', '', str(code))[:80])
    body = response.get('body') or payload
    if not isinstance(body, dict): raise ApiError('API body 구조 오류')
    if 'data' in body: rows = body['data']
    elif 'items' in body:
        items = body['items']
        rows = items.get('item', []) if isinstance(items, dict) else items
    elif 'item' in body: rows = body['item']
    else: raise ApiError('응답에 data/items/item이 없음. 빈 목록으로 처리하지 않음')
    # 공식 공간/교육 Swagger는 data.data 배열도 명시한다.
    if isinstance(rows, dict) and 'data' in rows: rows = rows['data']
    if isinstance(rows, dict) and 'item' in rows: rows = rows['item']
    if rows in (None, ''): rows = []
    if isinstance(rows, dict): rows = [rows]
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows): raise ApiError('API 레코드 구조 오류')
    total = body.get('matchCount', body.get('totalCount', payload.get('totalCount')))
    try: total = int(total) if total not in (None, '') else None
    except (ValueError, TypeError): raise ApiError('API totalCount 오류') from None
    return rows, total

class ApiClient:
    def __init__(self, key, page_size=100, filter_style='cond', filters=None):
        self.key = urllib.parse.unquote(key.strip())
        self.page_size = page_size
        self.filter_style = filter_style
        self.filters = filters or {}
    def fetch(self, dataset, page, current_only=True):
        params = dict(page=page, perPage=self.page_size, returnType='json')
        params[dataset.key_parameter] = self.key
        params.update(self.filters)
        if dataset.name == 'announcements' and current_only:
            params['cond[rcrt_prgs_yn::EQ]' if self.filter_style == 'cond' else 'rcrt_prgs_yn'] = 'Y'
        url = dataset.base_url + dataset.operation + '?' + urllib.parse.urlencode(params)
        for attempt in range(3):
            time.sleep(.4)
            try:
                request = urllib.request.Request(url, headers={'User-Agent':'kstartup-reference-catalog/1.3'})
                with urllib.request.urlopen(request, timeout=30) as response:
                    content = response.read(10*1024*1024+1)
                if len(content)>10*1024*1024: raise ApiError('API 응답 10MB 상한 초과')
                return decode_payload(content)
            except urllib.error.HTTPError as exc:
                if exc.code not in (429,500,502,503,504) or attempt == 2: raise ApiError(f'API HTTP {exc.code}') from None
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt == 2: raise ApiError('API 네트워크 요청 실패') from None
            time.sleep(2**attempt)
        raise ApiError('API 재시도 실패')

class ReferenceCatalog:
    def __init__(self, path='data/api_catalog.sqlite3'):
        self.catalog = Catalog(path)
        self.conn = self.catalog.conn
        self.conn.execute('PRAGMA foreign_keys=ON')
        self.conn.executescript(SCHEMA)
        self.conn.executescript(DOMAIN_SCHEMA)
    def close(self): self.catalog.close()
    def upsert(self, dataset, raw):
        spec = DATASETS[dataset]
        r = normalize(raw)
        title = plain_text(r.get(spec.title_field))
        if not title: raise ValueError('제목 필드 누락: ' + spec.title_field)
        source_key, kind = identity(dataset, r)
        body = '\n\n'.join(f'{field}\n{plain_text(r[field])}' for field in spec.body_fields if r.get(field) not in (None,''))
        raw_json = canonical(raw)
        digest = sha256(raw_json.encode()).hexdigest()
        old = self.conn.execute('SELECT id,content_hash FROM reference_records WHERE source=? AND dataset=? AND source_key=?', (spec.service,dataset,source_key)).fetchone()
        rid = old['id'] if old else str(uuid4())
        now = stamp()
        values = (rid,spec.service,dataset,source_key,kind,title,body,r.get('biz_category_cd') or r.get('clss_cd') or r.get('supt_biz_clsfc') or r.get('spce_type_nm') or r.get('cntr_type_nm') or r.get('lctr_lclss_cd'),normalize_url(r.get('detl_pg_url') or r.get('lctr_pg_url') or r.get('hmpg')),r.get('file_nm'),r.get('fstm_reg_dt') or r.get('reg_dt'),r.get('last_mdfcn_dt') or r.get('mdfcn_dt'),str(r.get('biz_yr') or ''),r.get('pbanc_rcpt_bgng_dt'),r.get('pbanc_rcpt_end_dt'),r.get('rcrt_prgs_yn'),raw_json,digest,now,now,now)
        with self.conn:
            self.conn.execute('''INSERT INTO reference_records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(source,dataset,source_key) DO UPDATE SET
            title=excluded.title,body_text=excluded.body_text,category=excluded.category,
            detail_url=excluded.detail_url,file_name=excluded.file_name,published_at=excluded.published_at,
            source_modified_at=excluded.source_modified_at,business_year=excluded.business_year,
            starts_on=excluded.starts_on,ends_on=excluded.ends_on,open_flag=excluded.open_flag,
            raw_json=excluded.raw_json,content_hash=excluded.content_hash,
            changed_at=CASE WHEN reference_records.content_hash<>excluded.content_hash THEN excluded.changed_at ELSE reference_records.changed_at END,
            last_seen_at=excluded.last_seen_at''', values)
            self.conn.execute('INSERT OR IGNORE INTO reference_versions VALUES (?,?,?,?,?)', (str(uuid4()),rid,digest,raw_json,now))
            def numeric(value):
                try: return float(str(value).replace(',','')) if value not in (None,'') else None
                except (TypeError,ValueError): return None
            if dataset == 'centers':
                vals = (rid,str(r['cntr_id']),str(r.get('buld_id') if r.get('buld_id') is not None else ''),r.get('addr'),r.get('regin_clss'),numeric(r.get('latde')),numeric(r.get('lgtde')),numeric(r.get('spce_cnt')))
                self.conn.execute('INSERT OR REPLACE INTO reference_centers VALUES (?,?,?,?,?,?,?,?)',vals)
            elif dataset == 'spaces':
                vals = (rid,str(r['spce_id']),str(r.get('cntr_id') if r.get('cntr_id') is not None else ''),str(r.get('buld_id') if r.get('buld_id') is not None else ''),r.get('addr'),numeric(r.get('latde')),numeric(r.get('lgtde')),numeric(r.get('rent')),numeric(r.get('guam')),r.get('rsvt_psbl_clss'))
                self.conn.execute('INSERT OR REPLACE INTO reference_spaces VALUES (?,?,?,?,?,?,?,?,?,?)',vals)
            elif dataset == 'education':
                vals = (rid,normalize_url(r.get('lctr_pg_url')),r.get('lctr_lclss_cd'),r.get('lctr_mclss_cd'),r.get('lctr_sclss_cd'),r.get('kywrd'),r.get('play_time'))
                self.conn.execute('INSERT OR REPLACE INTO reference_education VALUES (?,?,?,?,?,?,?)',vals)
        return 'new' if not old else 'unchanged' if old['content_hash']==digest else 'updated'
    def sync(self, dataset, client, max_pages=100, current_only=True):
        run_id = str(uuid4())
        stats = dict(new=0,updated=0,unchanged=0,skipped=0,projection_errors=0)
        self.conn.execute('INSERT INTO reference_sync_runs(id,dataset,started_at,status) VALUES (?,?,?,?)', (run_id,dataset,stamp(),'running'))
        self.conn.commit()
        seen = set()
        read = 0
        pages = 0
        try:
            for page in range(1,max_pages+1):
                payload = client.fetch(DATASETS[dataset],page,current_only)
                rows,total = unpack(payload)
                self.conn.execute('INSERT INTO reference_sync_pages VALUES (?,?,?,?)',(run_id,page,canonical(payload),stamp()))
                self.conn.commit()
                pages = page
                fingerprint = sha256(canonical(rows).encode()).hexdigest()
                if rows and fingerprint in seen: raise ApiError('동일 페이지 반복 반환. 수집을 완료로 표시하지 않음')
                seen.add(fingerprint)
                for raw in rows:
                    r = normalize(raw)
                    if dataset == 'announcements' and current_only and not is_current(r):
                        stats['skipped'] += 1
                        continue
                    stats[self.upsert(dataset,raw)] += 1
                    if dataset == 'announcements':
                        try: self.catalog.upsert(r,today_kst())
                        except ValueError: stats['projection_errors'] += 1
                read += len(rows)
                if not rows or (total is not None and read>=total): break
            else: raise ApiError('페이지 상한 도달. --max-pages를 늘려 재실행 필요')
            status,error = 'success',None
        except Exception as exc:
            status = 'failed'
            error = str(exc) if isinstance(exc,(ApiError,ValueError)) else type(exc).__name__
        self.conn.execute('UPDATE reference_sync_runs SET finished_at=?,status=?,pages=?,records_read=?,stats_json=?,error=? WHERE id=?', (stamp(),status,pages,read,canonical(stats),error,run_id))
        self.conn.commit()
        return dict(dataset=dataset,run_id=run_id,status=status,pages=pages,records_read=read,**stats,error=error)
    def records(self, dataset='all', query=None, current=False):
        sql = 'SELECT * FROM reference_records WHERE 1=1'
        args = []
        if dataset != 'all': sql += ' AND dataset=?'; args.append(dataset)
        if query:
            sql += " AND (title LIKE ? ESCAPE '\\' OR body_text LIKE ? ESCAPE '\\')"
            term = '%' + query.replace('\\','\\\\').replace('%','\\%').replace('_','\\_') + '%'
            args.extend([term,term])
        for row in self.conn.execute(sql+' ORDER BY dataset,title,id',args):
            obj = dict(row)
            obj['raw'] = json.loads(obj.pop('raw_json'))
            obj['api_endpoint'] = DATASETS[obj['dataset']].base_url + DATASETS[obj['dataset']].operation
            if obj['dataset'] in ('centers','spaces','education'):
                table = {'centers':'reference_centers','spaces':'reference_spaces','education':'reference_education'}[obj['dataset']]
                detail = self.conn.execute(f'SELECT * FROM {table} WHERE record_id=?',(obj['id'],)).fetchone()
                obj['attributes'] = dict(detail) if detail else {}
                if obj['dataset']=='spaces' and detail:
                    linked = self.conn.execute('''SELECT c.record_id,r.title FROM reference_centers c JOIN reference_records r ON c.record_id=r.id WHERE c.center_id=? AND c.building_id=?''',(detail['center_id'],detail['building_id'])).fetchall()
                    obj['related_centers'] = [dict(c) for c in linked]
            if current and obj['dataset']=='announcements' and not is_current(normalize(obj['raw'])): continue
            yield obj
    def summary(self):
        return [dict(r) for r in self.conn.execute('SELECT dataset,COUNT(*) AS records,MAX(last_seen_at) AS last_seen_at FROM reference_records GROUP BY dataset')]

def export(catalog, path, dataset='all', fmt='jsonl', query=None, current=False):
    out = Path(path)
    out.parent.mkdir(parents=True,exist_ok=True)
    count = 0
    with out.open('w',encoding='utf-8-sig' if fmt=='csv' else 'utf-8',newline='') as f:
        columns = ['id','source','dataset','api_endpoint','title','body_text','category','detail_url','file_name','business_year','published_at','source_modified_at','starts_on','ends_on','open_flag','content_hash','last_seen_at','attributes_json','related_centers_json','raw_json']
        if fmt=='csv': writer = csv.DictWriter(f,fieldnames=columns); writer.writeheader()
        for obj in catalog.records(dataset,query,current):
            if fmt=='jsonl': f.write(json.dumps(obj,ensure_ascii=False)+'\n'); count += 1
            elif fmt=='csv':
                flat = {key: obj.get(key) for key in columns};flat['raw_json'] = canonical(obj['raw'])
                flat['attributes_json'] = canonical(obj.get('attributes',{}))
                flat['related_centers_json'] = canonical(obj.get('related_centers',[]))
                # Excel에서 외부 문자열이 수식으로 실행되지 않게 한다.
                flat = {k:("'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v) for k,v in flat.items()}
                writer.writerow(flat);count += 1
            else:
                metadata = '\n'.join(f'{key}: {obj[key]}' for key in ('category','business_year','published_at','starts_on','ends_on','file_name') if obj.get(key))
                text = obj['title']+'\n'+metadata+'\n\n'+obj['body_text']
                for i,start in enumerate(range(0,len(text),1000)):
                    chunk = dict(chunk_id=f"{obj['id']}:{obj['content_hash'][:12]}:{i}",record_id=obj['id'],dataset=obj['dataset'],title=obj['title'],text=text[start:start+1000],source_url=obj['detail_url'],api_endpoint=obj['api_endpoint'],content_hash=obj['content_hash'],last_seen_at=obj['last_seen_at'],coverage='API 제공 텍스트만 포함; 첨부 원문 미포함')
                    f.write(json.dumps(chunk,ensure_ascii=False)+'\n');count += 1
    return dict(output=str(out.resolve()),rows=count,format=fmt)

def main():
    load_env()
    parser = argparse.ArgumentParser(description='창업진흥원 7종 API와 팀 참고자료 DB')
    parser.add_argument('--database',default=os.environ.get('API_CATALOG_DB') or 'data/api_catalog.sqlite3')
    sub = parser.add_subparsers(dest='command',required=True)
    sub.add_parser('datasets')
    sync = sub.add_parser('sync')
    sync.add_argument('--dataset',choices=['all',*DATASETS],default='all')
    sync.add_argument('--service',choices=['all','kstartup','space','education'],default='all')
    sync.add_argument('--filter',action='append',default=[],help='필드::연산=값 (단일 dataset만)')
    sync.add_argument('--max-pages',type=int,default=100)
    sync.add_argument('--page-size',type=int,default=100)
    sync.add_argument('--filter-style',choices=['cond','plain'],default='cond')
    sync.add_argument('--include-closed',action='store_true')
    imp = sub.add_parser('import-json')
    imp.add_argument('--dataset',choices=list(DATASETS),required=True)
    imp.add_argument('file')
    sub.add_parser('summary')
    listing = sub.add_parser('list')
    listing.add_argument('--dataset',choices=['all',*DATASETS],default='all')
    listing.add_argument('--query');listing.add_argument('--limit',type=int,default=20)
    listing.add_argument('--current',action='store_true')
    exp = sub.add_parser('export')
    exp.add_argument('--dataset',choices=['all',*DATASETS],default='all')
    exp.add_argument('--format',choices=['jsonl','csv','chunks'],default='jsonl')
    exp.add_argument('--output',required=True);exp.add_argument('--query');exp.add_argument('--current',action='store_true')
    a = parser.parse_args()
    db = ReferenceCatalog(a.database)
    try:
        if a.command=='datasets': result = [vars(d) for d in DATASETS.values()]
        elif a.command=='sync':
            if a.max_pages<1 or not 1<=a.page_size<=100: raise ValueError('max-pages는 1 이상, page-size는 1~100')
            selected = [d for d in DATASETS if (a.dataset=='all' or d==a.dataset) and (a.service=='all' or DATASETS[d].service==a.service)]
            if not selected: raise ValueError('dataset과 service가 일치하지 않습니다.')
            filters = {}
            if a.filter:
                if len(selected)!=1: raise ValueError('--filter는 단일 dataset에만 적용 가능합니다.')
                for entry in a.filter:
                    field,sep,value = entry.partition('=')
                    if not sep or not value or field not in DATASETS[selected[0]].filters: raise ValueError('명세에 없거나 잘못된 필터. datasets 명령의 filters 확인')
                    filters['cond['+field+']'] = value
            result = []
            for d in selected:
                spec = DATASETS[d]
                key = os.environ.get(spec.key_env,'').strip() or os.environ.get('DATA_GO_KR_SERVICE_KEY','').strip()
                if not key:
                    result.append(dict(dataset=d,status='failed',error='인증키 없음: '+spec.key_env+' 또는 DATA_GO_KR_SERVICE_KEY'))
                    continue
                result.append(db.sync(d,ApiClient(key,a.page_size,a.filter_style,filters),a.max_pages,not a.include_closed))
            db.catalog.refresh(today_kst())
        elif a.command=='import-json':
            payload = json.loads(Path(a.file).read_text(encoding='utf-8-sig'))
            rows = payload if isinstance(payload,list) else unpack(payload)[0] if any(k in payload for k in ('data','response','items','item')) else [payload]
            result = dict(new=0,updated=0,unchanged=0)
            for raw in rows:
                result[db.upsert(a.dataset,raw)] += 1
                if a.dataset=='announcements':
                    try: db.catalog.upsert(normalize(raw),today_kst())
                    except ValueError: pass
        elif a.command=='summary': result = db.summary()
        elif a.command=='list':
            import itertools
            if a.limit<1: raise ValueError('limit는 1 이상')
            result = list(itertools.islice(db.records(a.dataset,a.query,a.current),a.limit))
        else: result = export(db,a.output,a.dataset,a.format,a.query,a.current)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 2 if isinstance(result,list) and any(r.get('status')=='failed' for r in result) else 0
    except Exception as exc:
        print(json.dumps(dict(error=str(exc) if isinstance(exc,(ValueError,ApiError)) else type(exc).__name__),ensure_ascii=False))
        return 1
    finally: db.close()

if __name__=='__main__': raise SystemExit(main())
