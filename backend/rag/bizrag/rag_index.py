"""Token-bounded evidence chunks, local retrieval and vector change tracking."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from .store import Store, now_iso, stable_hash
from .textindex import to_index_text

VERSION='evidence-v2-token128'

def evidence(body,meta):
    if meta.get('source')=='local_pdf' or meta.get('pdf_page'):
        body=body.split('\n\n',1)[-1]
        # Restore prose flow using the text layer; leave obvious table rows/headings separate.
        lines=body.splitlines(); out=[];buf=[]
        for line in lines:
            line=line.strip()
            if not line:
                if buf:out.append(' '.join(buf));buf=[]
            elif re.match(r'^(?:\d+[.)]|[ⅠⅡⅢⅣⅤ]+[.]|Table\s|Fig\s|표\s|그림\s|References)',line,re.I) or re.search(r'\d\s+\d',line):
                if buf:out.append(' '.join(buf));buf=[]
                out.append(line)
            else:buf.append(line)
        if buf:out.append(' '.join(buf))
        return '\n'.join(out)
    remove=('데이터 기간:','수집일(KST):','로컬 반입일(KST):','조회필터:','query_sig=')
    note=meta.get('note','')
    return '\n'.join(l for l in body.splitlines() if l.strip() and l.strip()!=note and not l.startswith(remove))

def aliases(title):
    if 'Customer satisfaction in the pet food' in title:
        return '사료 구독 고객 만족 건강 성분 영양 포장 서비스 품질 지속 의도'
    return ''

class RagStore(Store):
    def __init__(self,path,tokenizer_path=None):
        super().__init__(path)
        from tokenizers import Tokenizer
        tokenizer_path=tokenizer_path or Path(__file__).resolve().parents[1]/'data/pettech/tokenizer.json'
        self.tokenizer=Tokenizer.from_file(str(tokenizer_path))
        self.tokenizer.no_truncation();self.tokenizer.no_padding()
        self.conn.executescript('''
        CREATE TABLE IF NOT EXISTS rag_documents(doc_id TEXT PRIMARY KEY,evidence_hash TEXT,version TEXT,indexed_at TEXT);
        CREATE TABLE IF NOT EXISTS vector_changes(vector_id TEXT PRIMARY KEY,operation TEXT,changed_at TEXT);
        ''')

    def tokens(self,text):return self.tokenizer.encode(text,add_special_tokens=False)

    def short_title(self,title):
        prefix=aliases(title) or title
        enc=self.tokens(prefix)
        return prefix[:enc.offsets[23][1]] if len(enc.ids)>24 else prefix

    def pieces(self,text,title):
        prefix=self.short_title(title)+'\n'
        budget=128-len(self.tokenizer.encode(prefix).ids)-4
        enc=self.tokens(text)
        offsets=enc.offsets
        start=0
        while start<len(offsets):
            end=min(start+budget,len(offsets))
            char_start=offsets[start][0];char_end=offsets[end-1][1]
            # Prefer sentence/newline boundaries in the latter half of the token window.
            segment=text[char_start:char_end]
            boundaries=[m.end() for m in re.finditer(r'(?:[.!?。]\s+|\n)',segment)]
            suitable=[b for b in boundaries if b>len(segment)*.55]
            if suitable and end<len(offsets):
                char_end=char_start+suitable[-1]
                while end>start+1 and offsets[end-1][1]>char_end:end-=1
                char_end=offsets[end-1][1]
            piece=text[char_start:char_end].strip()
            # Verify the final input, including special tokens and title, never truncates evidence.
            while piece and len(self.tokenizer.encode(prefix+piece).ids)>128:
                end-=1;char_end=offsets[end-1][1];piece=text[char_start:char_end].strip()
            if piece:yield piece
            if end>=len(offsets):break
            start=max(start+1,end-12)

    def delete_document(self,doc_id):
        for row in self.conn.execute('SELECT chunk_id FROM chunks WHERE doc_id=?',(doc_id,)).fetchall():
            self.conn.execute('DELETE FROM chunks_fts WHERE chunk_id=?',(row[0],))
            self.change(row[0],'delete')
        self.conn.execute('DELETE FROM chunks WHERE doc_id=?',(doc_id,))
        self.conn.execute('DELETE FROM documents WHERE doc_id=?',(doc_id,))
        self.conn.execute('DELETE FROM rag_documents WHERE doc_id=?',(doc_id,))

    def change(self,chunk_id,operation):
        vid=hashlib.sha1(chunk_id.encode()).hexdigest()
        self.conn.execute('INSERT OR REPLACE INTO vector_changes VALUES(?,?,?)',(vid,operation,now_iso()))

    def reindex(self,doc_id,force=False):
        row=self.conn.execute('SELECT * FROM documents WHERE doc_id=?',(doc_id,)).fetchone()
        meta=json.loads(row['meta_json'] or '{}')
        text=evidence(row['body'],meta)
        digest=stable_hash([row['title'],text,aliases(row['title'])])
        prior=self.conn.execute('SELECT evidence_hash,version FROM rag_documents WHERE doc_id=?',(doc_id,)).fetchone()
        if not force and prior and tuple(prior)==(digest,VERSION):return False
        previous={r[0] for r in self.conn.execute('SELECT chunk_id FROM chunks WHERE doc_id=?',(doc_id,))}
        for cid in previous:self.conn.execute('DELETE FROM chunks_fts WHERE chunk_id=?',(cid,))
        self.conn.execute('DELETE FROM chunks WHERE doc_id=?',(doc_id,))
        current=set();occurrences={}
        for seq,piece in enumerate(self.pieces(text,row['title'])):
            # Content IDs keep unchanged chunks stable even if an earlier paragraph is inserted.
            occurrence=occurrences.get(piece,0);occurrences[piece]=occurrence+1
            cid=f'{doc_id}#{stable_hash([piece,occurrence])[:16]}'
            current.add(cid)
            self.conn.execute('INSERT INTO chunks VALUES(?,?,?,?)',(cid,doc_id,seq,piece))
            self.conn.execute('INSERT INTO chunks_fts VALUES(?,?)',(cid,to_index_text(row['title']+' '+aliases(row['title'])+'\n'+piece)))
        for cid in previous-current:self.change(cid,'delete')
        for cid in current-previous:self.change(cid,'upsert')
        self.conn.execute('INSERT OR REPLACE INTO rag_documents VALUES(?,?,?,?)',(doc_id,digest,VERSION,now_iso()))
        return True

    def upsert_document(self,**kw):
        doc_id=f"{kw['source']}:{kw['doc_type']}:{kw['original_id']}"
        old_meta=self.conn.execute('SELECT meta_json FROM documents WHERE doc_id=?',(doc_id,)).fetchone()
        # Store the original evidence and updated metadata; reindex only semantic changes.
        old_chunks=[dict(r) for r in self.conn.execute('SELECT * FROM chunks WHERE doc_id=?',(doc_id,))]
        old_index=self.conn.execute('SELECT * FROM rag_documents WHERE doc_id=?',(doc_id,)).fetchone()
        changed=super().upsert_document(**kw)
        self.conn.execute('UPDATE documents SET meta_json=?,url=?,license=?,published_at=? WHERE doc_id=?',
            (json.dumps(kw.get('meta') or {},ensure_ascii=False),kw.get('url'),kw.get('license'),kw.get('published_at'),doc_id))
        # super may have rebuilt legacy chunks; restore our prior chunks so vector tombstones are accurate.
        if changed and old_index:
            for r in self.conn.execute('SELECT chunk_id FROM chunks WHERE doc_id=?',(doc_id,)).fetchall():
                self.conn.execute('DELETE FROM chunks_fts WHERE chunk_id=?',(r[0],))
            self.conn.execute('DELETE FROM chunks WHERE doc_id=?',(doc_id,))
            for r in old_chunks:
                self.conn.execute('INSERT INTO chunks VALUES(?,?,?,?)',(r['chunk_id'],doc_id,r['seq'],r['text']))
                self.conn.execute('INSERT INTO chunks_fts VALUES(?,?)',(r['chunk_id'],to_index_text(kw['title']+' '+aliases(kw['title'])+'\n'+r['text'])))
        reindexed=self.reindex(doc_id)
        if not reindexed and old_meta and json.loads(old_meta[0] or '{}')!=(kw.get('meta') or {}):
            for row in self.conn.execute('SELECT chunk_id FROM chunks WHERE doc_id=?',(doc_id,)).fetchall():
                vid=hashlib.sha1(row[0].encode()).hexdigest()
                pending=self.conn.execute('SELECT operation FROM vector_changes WHERE vector_id=?',(vid,)).fetchone()
                if not pending or pending[0]!='upsert':self.change(row[0],'metadata')
        return reindexed

    def search(self,query,*,sources=None,doc_types=None,limit=8,min_year=None,include_historical=False):
        normalized=query
        if re.search(r'1인|혼자\s*사|1명',query):normalized+=' 가구원수 1명'
        if '양육비' in query:normalized+=' 양육비용 월평균양육비'
        if '양육' in query and re.search(r'비율|여부',query):normalized+=' 현재 반려동물 양육 여부'
        if re.search(r'사료|펫푸드',query) and re.search(r'구독|만족',query):
            normalized+=' pet food subscription customer satisfaction ingredients packaging healthfulness'
        hits=super().search(normalized,sources=sources,doc_types=doc_types,limit=250)
        requested_years=re.findall(r'\b(20\d{2})\b',query)
        if requested_years and min_year is None:min_year=int(max(requested_years))
        cost='양육비' in query or '월평균양육비' in query
        ownership='양육' in query and bool(re.search(r'비율|여부',query))
        one=bool(re.search(r'1인|가구원수\s*1명',normalized))
        scored=[]
        for h in hits:
            m=h['meta'];title=h['title'];score=h['score']
            raw_year=str(m.get('publication_year') or m.get('period_end') or m.get('period') or '')
            year=int(raw_year[:4]) if re.match(r'^\d{4}',raw_year) else None
            if min_year and (year is None or year<min_year):continue
            if m.get('historical_source') and not include_historical and '2016' not in query:continue
            if (cost or ownership) and not sources and h['source']!='kosis':continue
            if cost and h['source']=='kosis' and '양육비용' not in title:continue
            if ownership and h['source']=='kosis' and '현재 반려동물 양육 여부' not in title:continue
            if one and h['source']=='kosis' and '가구원수 > 1명' not in title:continue
            if (cost or ownership) and not one and title.endswith(' | 전체'):score+=30
            if cost and '_전체' in title:score+=12
            if re.search(r'전체|전국',query) and title.endswith(' | 전체'):score+=15
            if '구독' in query and '사료' in query and 'Customer satisfaction' in title:score+=30
            if '동물병원' in query and '동물병원' in title:score+=15
            if '동물미용업' in query and '동물미용업' in title:score+=15
            if '전국' in query and '전국 및 지역별' in title:score+=15
            score+=sum(2 for word in query.split() if word in h['text'])
            h['retrieval_score']=round(score,4)
            scored.append(h)
        scored.sort(key=lambda h:h['retrieval_score'],reverse=True)
        # Avoid many chunks from a single page drowning out independent supporting evidence.
        counts={};result=[]
        for h in scored:
            if counts.get(h['doc_id'],0)>=2:continue
            counts[h['doc_id']]=counts.get(h['doc_id'],0)+1
            result.append(h)
            if len(result)>=limit:break
        return result

    def export_vectors(self,folder):
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
        target=folder/'pinecone_chunks.jsonl';temp=target.with_suffix('.jsonl.tmp')
        count=0;max_tokens=0
        with temp.open('w',encoding='utf-8') as handle:
            for r in self.conn.execute('SELECT c.*,d.title,d.source,d.doc_type,d.url,d.retrieved_at,d.license,d.meta_json FROM chunks c JOIN documents d USING(doc_id) ORDER BY c.chunk_id'):
                meta=json.loads(r['meta_json'])
                text=self.short_title(r['title'])+'\n'+r['text']
                tokens=len(self.tokenizer.encode(text).ids)
                if tokens>128:raise ValueError('Embedding input exceeds token limit')
                max_tokens=max(max_tokens,tokens)
                metadata={'domain':'pettech','doc_id':r['doc_id'],'chunk_id':r['chunk_id'],'title':r['title'],
                    'source':r['source'],'doc_type':r['doc_type'],'url':r['url'] or '',
                    'collected_at':meta.get('collected_at',r['retrieved_at']),
                    'collected_at_kst':meta.get('collected_at_kst',''),
                    'period_start':meta.get('period_start','미상'),'period_end':meta.get('period_end','미상'),
                    'license':r['license'] or '', 'note':meta.get('note',''),'chunk_version':VERSION,
                    'text':r['text'],
                    'context_json':json.dumps(meta,ensure_ascii=False)}
                for key in ('source_file','source_sha256','pdf_page','publication_year','historical_source','province','district','query_sig'):
                    if meta.get(key) is not None:metadata[key]=meta[key]
                record={'id':hashlib.sha1(r['chunk_id'].encode()).hexdigest(),'chunk_id':r['chunk_id'],'doc_id':r['doc_id'],
                    'text':text,'embedding_tokens':tokens,'metadata':metadata,
                    'context_text':f"{r['title']}\n출처: {r['url']}\n기간: {metadata['period_start']} ~ {metadata['period_end']}\n수집/반입일(KST): {metadata['collected_at_kst']}\n{meta.get('note','')}\n{r['text']}"}
                handle.write(json.dumps(record,ensure_ascii=False)+'\n');count+=1
        temp.replace(target)
        changes=[dict(r) for r in self.conn.execute('SELECT * FROM vector_changes ORDER BY vector_id')]
        (folder/'vector_changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
        return {'chunks':count,'max_embedding_tokens':max_tokens,'chunk_version':VERSION}
