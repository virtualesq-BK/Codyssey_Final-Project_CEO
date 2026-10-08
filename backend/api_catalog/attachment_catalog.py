"""API DB와 분리된 첨부 원본/양식 데이터 확장. 파일명을 키로 사용하지 않는다."""
import argparse
import json
import re
import sqlite3
from datetime import date
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit,parse_qs
from uuid import uuid4

from api_catalog import Catalog
from _api_catalog_core import stamp,parse_api_date
from forms_http import Client,FetchError
from forms_documents import extract,classify,detect,field_candidates,PARSER_VERSION

SCHEMA='''
CREATE TABLE IF NOT EXISTS source_pages (
 source_id TEXT PRIMARY KEY, requested_url TEXT NOT NULL, final_url TEXT,
 snapshot_path TEXT, page_hash TEXT, last_checked_at TEXT, status TEXT,
 error TEXT, discovered_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS attachments (
 id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES source_pages(source_id),
 external_file_id TEXT NOT NULL, download_url TEXT NOT NULL, filename TEXT NOT NULL,
 active INTEGER NOT NULL DEFAULT 1, first_seen_at TEXT NOT NULL,last_seen_at TEXT NOT NULL,
 role_override TEXT, current_version_id TEXT, status TEXT NOT NULL,error TEXT,
 derived_from_attachment_id TEXT REFERENCES attachments(id),
 UNIQUE(source_id,external_file_id)
);
CREATE TABLE IF NOT EXISTS attachment_versions (
 id TEXT PRIMARY KEY, attachment_id TEXT NOT NULL REFERENCES attachments(id),
 content_hash TEXT NOT NULL, filename TEXT NOT NULL, original_path TEXT NOT NULL,
 bytes INTEGER NOT NULL, format TEXT NOT NULL, mime_type TEXT,
 detected_role TEXT NOT NULL, extraction_state TEXT NOT NULL,
 blocks_json TEXT NOT NULL, warnings_json TEXT NOT NULL, parser_version TEXT NOT NULL,created_at TEXT NOT NULL,
 UNIQUE(attachment_id,content_hash,parser_version)
);
CREATE TABLE IF NOT EXISTS form_templates (
 id TEXT PRIMARY KEY, attachment_version_id TEXT NOT NULL UNIQUE REFERENCES attachment_versions(id),
 fields_json TEXT NOT NULL, review_status TEXT NOT NULL, reviewer TEXT, reviewed_at TEXT,
 mapping_status TEXT NOT NULL, reviewed_fields_path TEXT
);
'''

class Node:
    def __init__(self,tag='',attrs=None,parent=None):self.tag=tag;self.attrs=attrs or {};self.parent=parent;self.children=[]
    def text(self):return ''.join(c if isinstance(c,str) else c.text() for c in self.children)
    def nodes(self):
        yield self
        for c in self.children:
            if isinstance(c,Node):yield from c.nodes()

class DOM(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.root=Node('root');self.current=self.root
    def handle_starttag(self,tag,attrs):
        n=Node(tag,dict(attrs),self.current);self.current.children.append(n)
        if tag not in ('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'):self.current=n
    def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs);self.handle_endtag(tag)
    def handle_endtag(self,tag):
        n=self.current
        while n is not self.root:
            if n.tag==tag:self.current=n.parent;return
            n=n.parent
    def handle_data(self,data):self.current.children.append(data)


def attachment_links(html,page_url):
    dom=DOM();dom.feed(html);items={}
    for a in dom.root.nodes():
        if a.tag!='a':continue
        href=a.attrs.get('href','')
        match=re.search(r'/afile/fileDownload/([A-Za-z0-9_-]+)(?:[/?#]|$)',href)
        if not match:continue
        name='';parent=a.parent
        while parent and parent is not dom.root:
            labels=[n for n in parent.nodes() if n.tag=='a' and ('file_bg' in n.attrs.get('class','').split() or n.attrs.get('title','').startswith('[첨부파일]'))]
            if len(labels)==1:
                name=labels[0].text().strip() or labels[0].attrs.get('title','').removeprefix('[첨부파일]').strip();break
            parent=parent.parent
        if not name:name=a.attrs.get('download') or a.attrs.get('title') or 'unnamed_'+match[1]
        full=urljoin(page_url,href)
        if urlsplit(full).hostname!=urlsplit(page_url).hostname:continue
        items[match[1]]=dict(file_id=match[1],url=full,filename=unescape(name))
    return list(items.values())


def page_redirect(html,url,source_id):
    # Follow only the site's observed same-announcement GET route; never execute JavaScript.
    m=re.search(r"var\s+fullUrl\s*=\s*['\"]([^'\"]+)['\"]",html)
    if not m:return None
    target=urljoin(url,unescape(m[1]));parts=urlsplit(target)
    if parts.hostname!=urlsplit(url).hostname or not re.fullmatch(r'/web/contents/bizpbanc-[a-z-]+\.do',parts.path):return None
    if parse_qs(parts.query).get('pbancSn')!=[str(source_id)]:return None
    return target if target!=url else None


def fetch_page(client,url,source_id):
    seen=set()
    for _ in range(3):
        if url in seen:raise FetchError('페이지 이동 반복')
        seen.add(url);data,headers,final=client.get(url,limit=3*1024*1024)
        html=data.decode('utf-8-sig',errors='replace')
        next_url=page_redirect(html,final,source_id)
        if next_url:url=next_url;continue
        return data,html,final
    raise FetchError('페이지 이동 상한 초과')


class AttachmentCatalog:
    def __init__(self,db='data/api_catalog.sqlite3',storage='data/attachments',client=None):
        self.catalog=Catalog(db);self.conn=self.catalog.conn;self.conn.execute('PRAGMA foreign_keys=ON');self.conn.executescript(SCHEMA)
        self.storage=Path(storage).resolve();self.storage.mkdir(parents=True,exist_ok=True);self.client=client or Client()
    def close(self):self.catalog.close()
    def one(self,sql,args=()):
        r=self.conn.execute(sql,args).fetchone();return dict(r) if r else None
    def rows(self,sql,args=()):return [dict(r) for r in self.conn.execute(sql,args).fetchall()]
    def crawl(self,source_id,url,max_files=20):
        source_id=str(source_id)
        if not re.fullmatch(r'\d+',source_id):raise ValueError('K-Startup 공고 ID는 숫자여야 합니다.')
        self.conn.execute('INSERT INTO source_pages(source_id,requested_url,status) VALUES (?,?,?) ON CONFLICT(source_id) DO UPDATE SET requested_url=excluded.requested_url,status=excluded.status',(source_id,url,'running'));self.conn.commit()
        try:
            raw,html,final=fetch_page(self.client,url,source_id);items=attachment_links(html,final)
            snap=self.storage/'pages'/source_id/(sha256(raw).hexdigest()+'.html');snap.parent.mkdir(parents=True,exist_ok=True);snap.write_bytes(raw)
            self.conn.execute('UPDATE source_pages SET final_url=?,snapshot_path=?,page_hash=?,last_checked_at=?,discovered_count=? WHERE source_id=?',(final,str(snap),sha256(raw).hexdigest(),stamp(),len(items),source_id));self.conn.commit()
            if not items:raise FetchError('다운로드 링크 없음. 로그인/외부 페이지/구조 변경 여부 수동 확인 필요')
            if len(items)>max_files:raise FetchError('첨부 개수 상한 초과. --max-files 조정 필요')
            output=[];complete=True;ids=[]
            for item in items:
                row=self.one('SELECT * FROM attachments WHERE source_id=? AND external_file_id=?',(source_id,item['file_id']));aid=row['id'] if row else str(uuid4());ids.append(aid)
                if not row:
                    self.conn.execute('INSERT INTO attachments(id,source_id,external_file_id,download_url,filename,first_seen_at,last_seen_at,status) VALUES (?,?,?,?,?,?,?,?)',(aid,source_id,item['file_id'],item['url'],item['filename'],stamp(),stamp(),'pending'))
                else:self.conn.execute('UPDATE attachments SET filename=?,download_url=?,active=1,last_seen_at=? WHERE id=?',(item['filename'],item['url'],stamp(),aid))
                self.conn.commit()
                try:
                    content,headers,_=self.client.get(item['url'])
                    if detect(content)=='html':raise FetchError('다운로드 대신 HTML 반환: 접근 제한/로그인/오류 여부 확인 필요')
                    vid,change=self.register(aid,content,item['filename'],headers.get('Content-Type',''))
                    output.append(dict(attachment_id=aid,version_id=vid,filename=item['filename'],change=change))
                except Exception as exc:
                    complete=False;error=str(exc) if isinstance(exc,(FetchError,ValueError)) else type(exc).__name__
                    self.conn.execute("UPDATE attachments SET status='failed',error=? WHERE id=?",(error,aid));self.conn.commit();output.append(dict(attachment_id=aid,error=error))
            if complete:
                marks=','.join('?' for _ in ids);self.conn.execute(f"UPDATE attachments SET active=0 WHERE source_id=? AND external_file_id NOT LIKE 'derived-%' AND id NOT IN ({marks})",(source_id,*ids))
            self.conn.execute('UPDATE source_pages SET status=?,error=NULL WHERE source_id=?',('success' if complete else 'partial',source_id));self.conn.commit();return output
        except Exception as exc:
            error=str(exc) if isinstance(exc,(FetchError,ValueError)) else type(exc).__name__
            self.conn.execute("UPDATE source_pages SET status='failed',error=?,last_checked_at=? WHERE source_id=?",(error,stamp(),source_id));self.conn.commit();raise
    def register(self,aid,data,filename,mime=''):
        row=self.one('SELECT * FROM attachments WHERE id=?',(aid,))
        if not row:raise ValueError('첨부 ID 없음')
        if len(data)>25*1024*1024:raise ValueError('파일 25MB 상한 초과')
        fingerprint=sha256(data).hexdigest();old=self.one('SELECT * FROM attachment_versions WHERE attachment_id=? AND content_hash=? AND parser_version=?',(aid,fingerprint,PARSER_VERSION))
        if old:
            self.conn.execute("UPDATE attachments SET current_version_id=?,status='stored',error=NULL WHERE id=?",(old['id'],aid));self.conn.commit();return old['id'],'unchanged'
        fmt=detect(data);ext=Path(filename).suffix.lower()
        if fmt in ('docx','hwpx','pdf','zip','jpg','png'):ext='.'+fmt
        if ext not in ('.doc','.docx','.hwp','.hwpx','.pdf','.zip','.jpg','.png','.txt'):ext='.bin'
        path=self.storage/'originals'/row['source_id']/(fingerprint+ext);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        try:blocks,warnings,state,fmt=extract(path,filename)
        except Exception as exc:blocks,warnings,state=[],[str(exc) if isinstance(exc,ValueError) else type(exc).__name__],'failed'
        role=classify(filename,blocks);vid=str(uuid4());fields=field_candidates(blocks) if role in ('form','unknown') else []
        self.conn.execute('INSERT INTO attachment_versions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(vid,aid,fingerprint,filename,str(path),len(data),fmt,mime,role,state,json.dumps(blocks,ensure_ascii=False),json.dumps(warnings,ensure_ascii=False),PARSER_VERSION,stamp()))
        self.conn.execute('INSERT INTO form_templates VALUES (?,?,?,?,?,?,?,?)',(str(uuid4()),vid,json.dumps(fields,ensure_ascii=False),'pending',None,None,'unmapped',None))
        self.conn.execute("UPDATE attachments SET current_version_id=?,status='stored',error=NULL WHERE id=?",(vid,aid));self.conn.commit();return vid,'new_version'
    def current(self,limit=20,max_files=20):
        self.catalog.refresh();result=[]
        for row in self.rows("SELECT a.* FROM api_announcements a LEFT JOIN source_pages p ON a.source_id=p.source_id WHERE a.deadline_status IN ('모집중','마감임박(D-3)') AND COALESCE(a.open_flag,'Y')<>'N' ORDER BY COALESCE(p.last_checked_at,''),a.ends_on,a.source_id"):
            if row['starts_on'] and parse_api_date(row['starts_on'])>date.today():continue
            if len(result)>=limit:break
            url=row['detail_url'] or f"https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn={row['source_id']}"
            try:result.append(dict(source_id=row['source_id'],files=self.crawl(row['source_id'],url,max_files)))
            except Exception as exc:result.append(dict(source_id=row['source_id'],error=str(exc) if isinstance(exc,(ValueError,FetchError)) else type(exc).__name__))
        return result
    def export(self,source_id,include_pending=False):
        page=self.one('SELECT * FROM source_pages WHERE source_id=?',(str(source_id),))
        if not page:raise ValueError('수집된 상세 페이지 없음')
        files=self.rows('SELECT a.*,v.content_hash,v.original_path,v.format,v.detected_role,v.extraction_state,v.blocks_json,v.warnings_json,t.id AS template_id,t.fields_json,t.review_status,t.mapping_status FROM attachments a JOIN attachment_versions v ON a.current_version_id=v.id JOIN form_templates t ON t.attachment_version_id=v.id WHERE a.source_id=? AND a.active=1',(str(source_id),))
        for f in files:
            f['role']=f['role_override'] or f['detected_role'];f['blocks']=json.loads(f.pop('blocks_json'));f['warnings']=json.loads(f.pop('warnings_json'))
            fields=json.loads(f.pop('fields_json'));f['fields']=fields if include_pending or f['review_status']=='approved' else []
            f['working_template_path']=f['original_path']+'.converted.docx' if f['extraction_state']=='converted_xml_candidate' else f['original_path']
            f['ready_for_generation']=f['role']=='form' and f['review_status']=='approved' and f['mapping_status']=='validated' and bool(fields)
        return dict(schema_version='1.0',source_id=str(source_id),page=page,attachments=files,contract='원본 템플릿과 검증된 문항/위치를 전달. 최종 답변 삽입/서식 검증은 출력 담당자 역할')
    def review(self,template_id,file,reviewer):
        row=self.one('SELECT t.*,v.blocks_json,v.detected_role,v.extraction_state FROM form_templates t JOIN attachment_versions v ON t.attachment_version_id=v.id WHERE t.id=?',(template_id,))
        if not row:raise ValueError('템플릿 ID 없음')
        data=json.loads(Path(file).read_text(encoding='utf-8'));blocks={b['id']:b for b in json.loads(row['blocks_json'])};fields=data.get('fields')
        if not isinstance(fields,list) or not fields:raise ValueError('검토 JSON에 fields 배열이 필요합니다.')
        for f in fields:
            if not isinstance(f,dict) or not f.get('label') or not f.get('evidence'):raise ValueError('문항 label/evidence 필요')
            quotes=[]
            for e in f['evidence']:
                if e.get('block_id') not in blocks or not e.get('quote') or e['quote'] not in blocks[e['block_id']]['text']:raise ValueError('원문 근거 불일치')
                quotes.append(e['quote'])
            joined='\n'.join(quotes)
            if f['label'] not in joined or (f.get('guidance') and f['guidance'] not in joined):raise ValueError('문항/작성안내 근거 불일치')
            for key,unit in [('max_chars','자'),('max_pages','페이지|쪽')]:
                value=f.get(key)
                if value is not None and (type(value) is not int or value<=0 or value not in [int(n.replace(',','')) for n in re.findall(r'([\d,]+)\s*(?:'+unit+r')',joined)]):raise ValueError('분량 제한 근거 불일치')
            spaces=f.get('count_spaces')
            if spaces is not None and (type(spaces) is not bool or ('공백 포함' if spaces else '공백 제외') not in joined):raise ValueError('공백 기준 근거 불일치')
            ids=f.get('answer_block_ids',[])
            if not isinstance(ids,list) or any(b not in blocks for b in ids):raise ValueError('답변 위치 ID 오류')
            if data.get('mapping_validated'):
                if not ids:raise ValueError('위치 검증에는 각 문항의 answer_block_ids가 필요합니다.')
                if any('xpath' not in blocks[b]['location'] for b in ids):raise ValueError('XML 삽입 위치가 없는 문서는 validated로 표시할 수 없습니다.')
        if data.get('mapping_validated') and row['extraction_state'] not in ('xml_candidate','converted_xml_candidate'):raise ValueError('이 파일은 자동 삽입 가능한 위치 후보가 없습니다.')
        state='validated' if data.get('mapping_validated') else 'unmapped'
        saved=self.storage/'reviews'/(template_id+'.json');saved.parent.mkdir(exist_ok=True);saved.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        self.conn.execute("UPDATE form_templates SET fields_json=?,review_status='approved',reviewer=?,reviewed_at=?,mapping_status=?,reviewed_fields_path=? WHERE id=?",(json.dumps(fields,ensure_ascii=False),reviewer,stamp(),state,str(saved),template_id));self.conn.commit()
    def override_role(self,aid,role):
        if not self.one('SELECT id FROM attachments WHERE id=?',(aid,)):raise ValueError('첨부 ID 없음')
        self.conn.execute('UPDATE attachments SET role_override=? WHERE id=?',(role,aid));self.conn.commit()


def main():
    p=argparse.ArgumentParser(description='K-Startup 첨부 수집과 양식 DB 확장');p.add_argument('--database',default='data/api_catalog.sqlite3');p.add_argument('--storage',default='data/attachments')
    sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('crawl');s.add_argument('--url',required=True);s.add_argument('--max-files',type=int,default=20)
    s=sub.add_parser('crawl-current');s.add_argument('--limit',type=int,default=20);s.add_argument('--max-files',type=int,default=20)
    sub.add_parser('list')
    s=sub.add_parser('export');s.add_argument('source_id');s.add_argument('--output',required=True);s.add_argument('--include-pending',action='store_true')
    s=sub.add_parser('role');s.add_argument('attachment_id');s.add_argument('role',choices=['notice','form','manual','other','unknown'])
    s=sub.add_parser('register-converted');s.add_argument('attachment_id');s.add_argument('file')
    s=sub.add_parser('review');s.add_argument('template_id');s.add_argument('file');s.add_argument('--reviewer',required=True)
    a=p.parse_args();db=AttachmentCatalog(a.database,a.storage)
    try:
        if a.command=='crawl':
            sid=parse_qs(urlsplit(a.url).query).get('pbancSn',[None])[0]
            if not sid:raise ValueError('URL에 pbancSn 필요')
            result=db.crawl(sid,a.url,a.max_files)
        elif a.command=='crawl-current':result=db.current(a.limit,a.max_files)
        elif a.command=='list':result=db.rows('SELECT a.*,v.format,v.detected_role,v.extraction_state,t.id AS template_id,t.review_status,t.mapping_status FROM attachments a LEFT JOIN attachment_versions v ON a.current_version_id=v.id LEFT JOIN form_templates t ON t.attachment_version_id=v.id ORDER BY a.source_id,a.filename')
        elif a.command=='export':
            out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(db.export(a.source_id,a.include_pending),ensure_ascii=False,indent=2),encoding='utf-8');result=dict(output=str(out.resolve()))
        elif a.command=='role':db.override_role(a.attachment_id,a.role);result=dict(role=a.role)
        elif a.command=='register-converted':
            # Different format is a derived attachment, not replacement of the source file.
            original=db.one('SELECT * FROM attachments WHERE id=?',(a.attachment_id,))
            if not original:raise ValueError('원본 첨부 ID 없음')
            data=Path(a.file).read_bytes();aid=str(uuid4());filename=Path(a.file).name;token='derived-'+sha256((a.attachment_id+sha256(data).hexdigest()).encode()).hexdigest()
            old=db.one('SELECT id FROM attachments WHERE source_id=? AND external_file_id=?',(original['source_id'],token))
            if old:aid=old['id']
            else:db.conn.execute('INSERT INTO attachments(id,source_id,external_file_id,download_url,filename,first_seen_at,last_seen_at,status,role_override) VALUES (?,?,?,?,?,?,?,?,?)',(aid,original['source_id'],token,'derived:'+a.attachment_id,filename,stamp(),stamp(),'pending',original['role_override']));db.conn.execute('UPDATE attachments SET derived_from_attachment_id=? WHERE id=?',(a.attachment_id,aid));db.conn.commit()
            vid,change=db.register(aid,data,filename);result=dict(attachment_id=aid,version_id=vid,change=change,derived_from=a.attachment_id)
        elif a.command=='review':db.review(a.template_id,a.file,a.reviewer);result=dict(review_status='approved')
        print(json.dumps(result,ensure_ascii=False,indent=2));return 2 if isinstance(result,list) and any('error' in r for r in result) else 0
    except Exception as exc:
        print(json.dumps(dict(error=str(exc) if isinstance(exc,(ValueError,FetchError)) else type(exc).__name__),ensure_ascii=False));return 1
    finally:db.close()

if __name__=='__main__':raise SystemExit(main())
