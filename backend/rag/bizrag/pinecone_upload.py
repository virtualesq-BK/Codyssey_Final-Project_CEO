"""Resumable local embedding and isolated Pinecone upload of the pet corpus."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np
import yaml
from dotenv import dotenv_values
from .pettech import ROOT,dump
from .store import now_iso,stable_hash


def obj(value):
    if isinstance(value,dict):return value
    if hasattr(value,'to_dict'):return value.to_dict()
    if hasattr(value,'model_dump'):return value.model_dump()
    return vars(value)


def signature(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()


class Upload:
    def __init__(self):
        self.cfg=yaml.safe_load((ROOT/'config/pettech_vector.yaml').read_text(encoding='utf-8'))
        self.env={**dotenv_values(ROOT/'new.env'),**{k:v for k,v in os.environ.items() if k.isupper()}}
        self.root=ROOT/self.cfg['corpus']
        self.payload=self.root/'exports/pinecone_chunks.jsonl'
        self.source_hash=hashlib.sha256(self.payload.read_bytes()).hexdigest()
        with self.payload.open(encoding='utf-8') as handle:self.rows=[json.loads(line) for line in handle]
        if not self.rows or len(self.rows)!=len({r['id'] for r in self.rows}):raise ValueError('Empty or duplicate vector input')
        self.model=self.env.get('EMBEDDING_MODEL','sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        self.provider=self.env.get('EMBEDDING_PROVIDER','fastembed').lower()
        if self.provider not in ('fastembed','local','openai'):raise ValueError('Unsupported embedding provider')
        if self.provider=='openai' and not self.env.get('OPENAI_API_KEY'):raise ValueError('OPENAI_API_KEY missing')
        self.index_name=self.env.get('PINECONE_INDEX_NAME','bizrag-market')
        self.namespace=self.cfg['namespace']
        self.dim=int(self.cfg['dimension'])
        self.conn=sqlite3.connect(self.root/'embeddings.sqlite3')
        self.conn.executescript('''
        CREATE TABLE IF NOT EXISTS vectors(id TEXT PRIMARY KEY,model TEXT,text_hash TEXT,dimension INTEGER,embedding BLOB,created_at TEXT);
        CREATE TABLE IF NOT EXISTS uploaded(index_name TEXT,namespace TEXT,id TEXT,payload_hash TEXT,at TEXT,PRIMARY KEY(index_name,namespace,id));
        ''')
        self._model=None;self._pc=None

    def close(self):
        self.conn.close()
        if self._pc is not None and hasattr(self._pc,'close'):self._pc.close()

    @property
    def pc(self):
        if self._pc is None:
            from pinecone import Pinecone
            key=self.env.get('PINECONE_API_KEY')
            if not key:raise ValueError('PINECONE_API_KEY missing')
            self._pc=Pinecone(api_key=key,timeout=60)
        return self._pc

    def inspect(self):
        names=[r.name for r in self.pc.indexes.list()]
        result={'index':self.index_name,'namespace':self.namespace,'model':self.model,'expected_dimension':self.dim,'chunks':len(self.rows),'available_indexes':names}
        if self.index_name in names:
            desc=self.pc.indexes.describe(self.index_name)
            result['index_dimension']=desc.dimension
            result['metric']=str(desc.metric)
            result['status']=obj(desc.status)
            index=self.pc.index(host=desc.host)
            result['namespaces']=obj(index.describe_index_stats()).get('namespaces',{})
        print(json.dumps(result,ensure_ascii=False,default=str),flush=True)
        return result

    def embed(self):
        if self.provider!='openai':
            from fastembed import TextEmbedding
            supported={r['model']:r['dim'] for r in TextEmbedding.list_supported_models()}
            if supported.get(self.model)!=self.dim:raise ValueError('Configured model dimension is not supported')
        pending=[]
        for row in self.rows:
            cached=self.conn.execute('SELECT model,text_hash,dimension FROM vectors WHERE id=?',(row['id'],)).fetchone()
            if cached!=(self.model,signature(row['text']),self.dim):pending.append(row)
        print(json.dumps({'stage':'embedding','total':len(self.rows),'cached':len(self.rows)-len(pending),'remaining':len(pending)}),flush=True)
        if pending:
            if self.provider=='openai':
                from openai import OpenAI
                model=OpenAI(api_key=self.env['OPENAI_API_KEY'],
                    base_url=self.env.get('OPENAI_BASE_URL') or 'https://api.openai.com/v1',
                    timeout=90,max_retries=5)
            else:
                model=TextEmbedding(model_name=self.model,cache_dir=str(ROOT/'data/pettech/models'),
                    threads=self.cfg['embedding_threads'],providers=['CPUExecutionProvider'])
            step=int(self.cfg['batch_size'])
            for offset in range(0,len(pending),step):
                batch=pending[offset:offset+step]
                if self.provider=='openai':
                    response=model.embeddings.create(model=self.model,input=[r['text'] for r in batch],
                        dimensions=self.dim,encoding_format='float')
                    ordered=sorted(response.data,key=lambda item:item.index)
                    if [item.index for item in ordered]!=list(range(len(batch))):raise ValueError('Embedding response index mismatch')
                    embeddings=[item.embedding for item in ordered]
                else:
                    embeddings=list(model.embed([r['text'] for r in batch],batch_size=step))
                if len(embeddings)!=len(batch):raise ValueError('Embedding response length mismatch')
                for row,embedding in zip(batch,embeddings):
                    vector=np.asarray(embedding,dtype=np.float32)
                    if vector.shape!=(self.dim,) or not np.isfinite(vector).all() or np.linalg.norm(vector)==0:
                        raise ValueError('Invalid embedding vector')
                    self.conn.execute('INSERT OR REPLACE INTO vectors VALUES(?,?,?,?,?,?)',
                        (row['id'],self.model,signature(row['text']),self.dim,vector.tobytes(),now_iso()))
                self.conn.commit()
                done=min(offset+step,len(pending))
                if offset==0 or done%512==0 or done==len(pending):
                    print(json.dumps({'stage':'embedding','done':len(self.rows)-len(pending)+done,'total':len(self.rows)}),flush=True)
        for row in self.rows:
            vector=np.asarray(self.vector(row),dtype=np.float32)
            if vector.shape!=(self.dim,) or not np.isfinite(vector).all() or np.linalg.norm(vector)==0:
                raise ValueError('Cached embedding validation failed')
        report={'vectors':len(self.rows),'dimension':self.dim,'model':self.model,
            'provider':self.provider,'verified_at':now_iso(),'corpus_sha256':self.source_hash,
            'all_vectors_verified':True,'local_vectors':'embeddings.sqlite3'}
        dump(self.root/'embedding_report.json',report)
        print(json.dumps(report),flush=True)
        if pending and self.provider=='openai':model.close()
        return report

    def index(self):
        names=[r.name for r in self.pc.indexes.list()]
        if self.index_name in names:
            desc=self.pc.indexes.describe(self.index_name)
            if desc.dimension!=self.dim:
                # Preserve the existing index; use a separate index matching this model.
                self.index_name=f'bizrag-pettech-{self.dim}'
                if self.index_name in names:
                    desc=self.pc.indexes.describe(self.index_name)
                    if desc.dimension!=self.dim:raise ValueError('Dedicated pet index has incompatible dimensions')
        if self.index_name not in names:
            from pinecone import ServerlessSpec
            self.pc.indexes.create(name=self.index_name,dimension=self.dim,metric='cosine',
                spec=ServerlessSpec(cloud=self.env.get('PINECONE_CLOUD','aws'),region=self.env.get('PINECONE_REGION','us-east-1')))
        for _ in range(60):
            desc=self.pc.indexes.describe(self.index_name)
            if desc.status.ready:break
            time.sleep(2)
        else:raise RuntimeError('Index readiness timeout')
        if desc.dimension!=self.dim:raise ValueError('Index dimension mismatch')
        return self.pc.index(host=desc.host)

    def vector(self,row):
        cached=self.conn.execute('SELECT model,text_hash,dimension,embedding FROM vectors WHERE id=?',(row['id'],)).fetchone()
        if not cached or cached[:3]!=(self.model,signature(row['text']),self.dim):raise ValueError('Embedding cache is incomplete or stale')
        return np.frombuffer(cached[3],dtype=np.float32).tolist()

    def upload(self):
        if hashlib.sha256(self.payload.read_bytes()).hexdigest()!=self.source_hash:raise ValueError('Corpus changed during embedding; rerun upload')
        index=self.index()
        stats=obj(index.describe_index_stats())
        before=stats.get('namespaces',{}).get(self.namespace,{})
        before=obj(before).get('vector_count',0) if before else 0
        owned=self.conn.execute('SELECT COUNT(*) FROM uploaded WHERE index_name=? AND namespace=?',(self.index_name,self.namespace)).fetchone()[0]
        if before and not owned:
            # Never overwrite a pre-existing, unowned namespace.
            self.namespace='pettech-'+self.source_hash[:8]
        pending=[]
        for row in self.rows:
            self.vector(row)
            meta={**row['metadata'],'embedding_model':self.model,'embedding_dimension':self.dim}
            if len(json.dumps(meta,ensure_ascii=False).encode())>39000:raise ValueError('Metadata exceeds size limit')
            digest=stable_hash([signature(row['text']),meta,self.model])
            prior=self.conn.execute('SELECT payload_hash FROM uploaded WHERE index_name=? AND namespace=? AND id=?',
                (self.index_name,self.namespace,row['id'])).fetchone()
            if not prior or prior[0]!=digest:pending.append((row,meta,digest))
        print(json.dumps({'stage':'upload','index':self.index_name,'namespace':self.namespace,'pending':len(pending),'total':len(self.rows)}),flush=True)
        step=int(self.cfg['batch_size'])
        for offset in range(0,len(pending),step):
            batch=pending[offset:offset+step]
            vectors=[{'id':row['id'],'values':self.vector(row),'metadata':meta} for row,meta,digest in batch]
            response=obj(index.upsert(vectors=vectors,namespace=self.namespace))
            if response.get('upserted_count')!=len(batch):raise RuntimeError('Partial Pinecone upsert; rerun to retry')
            self.conn.executemany('INSERT OR REPLACE INTO uploaded VALUES(?,?,?,?,?)',
                [(self.index_name,self.namespace,row['id'],digest,now_iso()) for row,meta,digest in batch])
            self.conn.commit()
            done=min(offset+step,len(pending))
            if offset==0 or done%512==0 or done==len(pending):print(json.dumps({'stage':'upload','done':done,'total':len(pending)}),flush=True)
        # Remove only vectors recorded as owned by this uploader, never other namespaces/data.
        desired={r['id'] for r in self.rows}
        stale=[r[0] for r in self.conn.execute('SELECT id FROM uploaded WHERE index_name=? AND namespace=?',(self.index_name,self.namespace)) if r[0] not in desired]
        for offset in range(0,len(stale),100):
            batch=stale[offset:offset+100];index.delete(ids=batch,namespace=self.namespace)
            self.conn.executemany('DELETE FROM uploaded WHERE index_name=? AND namespace=? AND id=?',[(self.index_name,self.namespace,vid) for vid in batch]);self.conn.commit()
        return self.verify(index)

    def verify(self,index):
        expected={r['id'] for r in self.rows}
        for attempt in range(24):
            stats=obj(index.describe_index_stats())
            namespace=stats.get('namespaces',{}).get(self.namespace,{})
            count=obj(namespace).get('vector_count',0) if namespace else 0
            if count==len(expected):break
            time.sleep(5)
        else:raise RuntimeError('Pinecone count verification timed out; rerun to verify')
        actual=set()
        for page in index.list(namespace=self.namespace):
            actual.update(item if isinstance(item,str) else obj(item)['id'] for item in page)
        if actual!=expected:raise RuntimeError('Pinecone vector IDs do not match corpus')
        samples=[self.rows[i] for i in sorted({0,len(self.rows)//4,len(self.rows)//2,3*len(self.rows)//4,len(self.rows)-1})]
        fetched=obj(index.fetch(ids=[r['id'] for r in samples],namespace=self.namespace))['vectors']
        for row in samples:
            record=obj(fetched[row['id']]);values=record['values'];meta=record['metadata']
            if len(values)!=self.dim or meta.get('chunk_id')!=row['chunk_id']:raise RuntimeError('Fetched vector verification failed')
        query=obj(index.query(vector=self.vector(samples[0]),namespace=self.namespace,top_k=3,include_metadata=True))
        matches=[obj(m) for m in query.get('matches',[])]
        if not matches or matches[0]['score']<.99:raise RuntimeError('Vector similarity smoke test failed')
        report={'verified_at':now_iso(),'status':'verified','index':self.index_name,'namespace':self.namespace,
            'model':self.model,'dimension':self.dim,'vectors':len(expected),'all_ids_verified':True,
            'sample_fetches':len(samples),'sample_query_top_score':matches[0]['score'],'corpus_sha256':self.source_hash,
            'local_vectors':'embeddings.sqlite3','pinecone_uploaded':True}
        dump(self.root/'pinecone_upload.json',report)
        manifest_path=self.root/'manifest.json'
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest.update(pinecone_uploaded=True,pinecone=report)
        dump(manifest_path,manifest)
        print(json.dumps(report,ensure_ascii=False),flush=True)
        return report


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['inspect','embed','upload','sync'])
    args=parser.parse_args();task=Upload()
    try:
        if args.command=='inspect':task.inspect()
        elif args.command=='embed':task.embed()
        elif args.command=='upload':task.upload()
        else:task.inspect();task.embed();task.upload()
    except Exception as exc:
        message=(f'API request failed (HTTP {exc.status_code}, code={getattr(exc,"code",None)})'
            if hasattr(exc,'status_code') else str(exc))
        for key in ('PINECONE_API_KEY','OPENAI_API_KEY'):
            if task.env.get(key):message=message.replace(task.env[key],'[REDACTED]')
        print(json.dumps({'status':'error','type':type(exc).__name__,'message':message[:700]},ensure_ascii=False),flush=True)
        return 2
    finally:task.close()
    return 0

if __name__=='__main__':raise SystemExit(main())
