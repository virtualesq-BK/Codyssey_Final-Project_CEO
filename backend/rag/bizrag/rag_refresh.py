"""Refresh due statistical sources and incrementally merge local evidence."""
import argparse
import json
import sqlite3
from datetime import datetime,timedelta,timezone
from pathlib import Path
import yaml
from .pettech import Collector,ROOT,SEOUL
from .rag_index import RagStore
from .rag_lifecycle import Assets
from .store import now_iso

POLICY=ROOT/'config/pettech_refresh.yaml'
CONFIG=ROOT/'config/pettech_documents.yaml'

def due(last,days,now=None):
    now=now or datetime.now(timezone.utc)
    return last is None or now>=datetime.fromisoformat(last)+timedelta(days=days)

def initialize(store,policy,stats_path):
    Assets(store)
    con=sqlite3.connect(f'file:{Path(stats_path).as_posix()}?mode=ro',uri=True)
    try:
        for name,p in policy['sources'].items():
            if store.conn.execute('SELECT 1 FROM refresh_state WHERE source=?',(name,)).fetchone():continue
            if name=='local_files':
                row=store.conn.execute("SELECT MAX(retrieved_at) FROM documents WHERE source IN ('local_pdf','local_csv')").fetchone()
            elif name in ('naver','shopping'):
                dataset='pet_search_trend' if name=='naver' else 'pet_shopping%'
                row=con.execute("SELECT MAX(retrieved_at) FROM documents WHERE source='naver' AND json_extract(meta_json,'$.dataset') LIKE ?",(dataset,)).fetchone()
            else:row=con.execute('SELECT MAX(retrieved_at) FROM documents WHERE source=?',(name,)).fetchone()
            last=row[0] if row else None
            nxt=(datetime.fromisoformat(last)+timedelta(days=p['days'])).isoformat() if last else now_iso()
            store.conn.execute('INSERT INTO refresh_state VALUES(?,?,?,?,?,?)',(name,last,last,nxt,'ok' if last else 'pending',''))
        store.conn.commit()
    finally:con.close()

def mark(store,source,ok,policy,message=''):
    current=datetime.now(timezone.utc)
    step=timedelta(days=policy['sources'][source]['days']) if ok else timedelta(hours=policy['retry_hours'])
    store.conn.execute('UPDATE refresh_state SET last_checked=?,last_success=CASE WHEN ? THEN ? ELSE last_success END,next_check=?,status=?,error=? WHERE source=?',
        (current.isoformat(),ok,current.isoformat(),(current+step).isoformat(),'ok' if ok else 'error',message[:300],source))
    store.conn.commit()

def run(command='sync',force=False,only=None,config_path=CONFIG):
    cfg=yaml.safe_load(Path(config_path).read_text(encoding='utf-8'))
    policy=yaml.safe_load(POLICY.read_text(encoding='utf-8'))
    store=RagStore(ROOT/cfg['output']/'knowledge.db')
    try:
        initialize(store,policy,ROOT/cfg['statistics_db'])
        if command=='status':
            rows=[]
            for row in store.conn.execute('SELECT * FROM refresh_state ORDER BY source'):
                d=dict(row);d.update(policy['sources'][row['source']])
                d['next_check_kst']=datetime.fromisoformat(row['next_check']).astimezone(SEOUL).isoformat()
                rows.append(d)
            return {'refresh':rows,'assets':[dict(r) for r in store.conn.execute('SELECT name,status,last_seen FROM source_assets ORDER BY name')],
                'pending_vector_changes':dict(store.conn.execute('SELECT operation,COUNT(*) FROM vector_changes GROUP BY operation').fetchall())}
        results=[]
        for source in ('kosis','ecos','naver','shopping'):
            if only and source not in only:continue
            state=store.conn.execute('SELECT * FROM refresh_state WHERE source=?',(source,)).fetchone()
            if not force and datetime.now(timezone.utc)<datetime.fromisoformat(state['next_check']):
                results.append({'source':source,'status':'not_due','next_check':state['next_check']});continue
            collector=Collector()
            try:
                code=collector.collect([source])
                if code:raise RuntimeError('Source jobs failed; inspect data/pettech/knowledge.db fetch_runs')
                mark(store,source,True,policy);results.append({'source':source,'status':'ok'})
            except Exception as exc:
                # Avoid printing third-party exception URLs, which may include authentication.
                mark(store,source,False,policy,type(exc).__name__)
                results.append({'source':source,'status':'error','error_type':type(exc).__name__})
            finally:collector.close()
        store.close();store=None
        from .pet_documents import build
        try:build(config_path)
        except Exception:
            store=RagStore(ROOT/cfg['output']/'knowledge.db')
            mark(store,'local_files',False,policy,'Local corpus update failed; previous asset revisions retained')
            raise
        store=RagStore(ROOT/cfg['output']/'knowledge.db')
        mark(store,'local_files',True,policy)
        return {'results':results,'local_files':'hash_checked','integrated_database':str(store.path)}
    finally:
        if store is not None:store.close()

def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['sync','status'])
    parser.add_argument('--force',action='store_true')
    parser.add_argument('--only',nargs='+',choices=['kosis','ecos','naver','shopping','local_files'])
    args=parser.parse_args()
    result=run(args.command,args.force,args.only)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 2 if any(r['status']=='error' for r in result.get('results',[])) else 0

if __name__=='__main__':raise SystemExit(main())
