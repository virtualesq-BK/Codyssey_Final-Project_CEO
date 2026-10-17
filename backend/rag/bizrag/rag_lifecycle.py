"""Asset identity, immutable revisions and transactional replacement of local evidence."""
import json
import sqlite3
from pathlib import Path
from .store import now_iso,stable_hash

SCHEMA='''
CREATE TABLE IF NOT EXISTS source_assets(asset_id TEXT PRIMARY KEY,name TEXT,sha256 TEXT,status TEXT,last_seen TEXT);
CREATE TABLE IF NOT EXISTS asset_versions(asset_id TEXT,sha256 TEXT,path TEXT,imported_at TEXT,PRIMARY KEY(asset_id,sha256));
CREATE TABLE IF NOT EXISTS asset_documents(asset_id TEXT,doc_id TEXT,PRIMARY KEY(asset_id,doc_id));
CREATE TABLE IF NOT EXISTS asset_events(id INTEGER PRIMARY KEY,asset_id TEXT,event TEXT,old_hash TEXT,new_hash TEXT,at TEXT);
CREATE TABLE IF NOT EXISTS refresh_state(source TEXT PRIMARY KEY,last_checked TEXT,last_success TEXT,next_check TEXT,status TEXT,error TEXT);
CREATE TABLE IF NOT EXISTS rag_sync_state(name TEXT PRIMARY KEY,signature TEXT);
'''

class Assets:
    def __init__(self,store):
        self.store=store;self.conn=store.conn
        self.conn.executescript(SCHEMA)

    def bootstrap(self,manifest):
        if self.conn.execute('SELECT COUNT(*) FROM source_assets').fetchone()[0]:return
        for info in manifest.get('files',[]):
            name=info.get('asset_name',info['original_filename'])
            aid=stable_hash(name.casefold())[:16]
            self.conn.execute('INSERT INTO source_assets VALUES(?,?,?,?,?)',(aid,name,info['sha256'],'active',now_iso()))
            self.conn.execute('INSERT OR IGNORE INTO asset_versions VALUES(?,?,?,?)',(aid,info['sha256'],info['local_copy'],info['imported_at']))
            for row in self.conn.execute('SELECT doc_id,meta_json FROM documents WHERE source IN (?,?)',('local_pdf','local_csv')).fetchall():
                if json.loads(row['meta_json']).get('source_sha256')==info['sha256']:
                    self.conn.execute('INSERT OR IGNORE INTO asset_documents VALUES(?,?)',(aid,row['doc_id']))
        self.conn.commit()

    def classify(self,name,digest):
        aid=stable_hash(name.casefold())[:16]
        old=self.conn.execute('SELECT * FROM source_assets WHERE asset_id=?',(aid,)).fetchone()
        duplicate=self.conn.execute("SELECT * FROM source_assets WHERE sha256=? AND status IN ('active','missing')",(digest,)).fetchone()
        if old and old['sha256']==digest:return aid,'unchanged',old['sha256']
        if duplicate and duplicate['asset_id']!=aid:return aid,'duplicate',old['sha256'] if old else None
        if not old and self.conn.execute('SELECT 1 FROM asset_versions WHERE sha256=? LIMIT 1',(digest,)).fetchone():
            return aid,'duplicate',None
        return aid,'modified' if old else 'new',old['sha256'] if old else None

    def record(self,aid,name,digest,path,event,old_hash,doc_ids=()):
        self.conn.execute('INSERT INTO asset_events(asset_id,event,old_hash,new_hash,at) VALUES(?,?,?,?,?)',
            (aid,event,old_hash,digest,now_iso()))
        if event=='duplicate':return
        self.conn.execute('INSERT OR REPLACE INTO source_assets VALUES(?,?,?,?,?)',(aid,name,digest,'active',now_iso()))
        self.conn.execute('INSERT OR IGNORE INTO asset_versions VALUES(?,?,?,?)',(aid,digest,str(path),now_iso()))
        for doc_id in doc_ids:self.conn.execute('INSERT OR IGNORE INTO asset_documents VALUES(?,?)',(aid,doc_id))

    def remove_active(self,aid):
        ids=[r[0] for r in self.conn.execute('SELECT doc_id FROM asset_documents WHERE asset_id=?',(aid,))]
        datasets=set()
        for doc_id in ids:
            row=self.conn.execute('SELECT meta_json FROM documents WHERE doc_id=?',(doc_id,)).fetchone()
            if row:
                meta=json.loads(row[0])
                if meta.get('dataset'):datasets.add(meta['dataset'])
            self.store.delete_document(doc_id)
        self.conn.execute('DELETE FROM asset_documents WHERE asset_id=?',(aid,))
        for dataset in datasets:self.conn.execute("DELETE FROM records WHERE source='local_csv' AND dataset=?",(dataset,))

    def prepare_revision(self,aid):
        # Clear current CSV rows inside the caller's transaction, but retain documents so
        # unchanged evidence chunks can keep their IDs and avoid re-embedding.
        for row in self.conn.execute('SELECT d.meta_json FROM asset_documents a JOIN documents d USING(doc_id) WHERE a.asset_id=?',(aid,)).fetchall():
            dataset=json.loads(row[0]).get('dataset')
            if dataset:self.conn.execute("DELETE FROM records WHERE source='local_csv' AND dataset=?",(dataset,))

    def prune_revision(self,aid,current_ids):
        current=set(current_ids)
        for (doc_id,) in self.conn.execute('SELECT doc_id FROM asset_documents WHERE asset_id=?',(aid,)).fetchall():
            if doc_id not in current:self.store.delete_document(doc_id)
        self.conn.execute('DELETE FROM asset_documents WHERE asset_id=?',(aid,))

    def sync_statistics(self,path):
        source=sqlite3.connect(f'file:{Path(path).as_posix()}?mode=ro',uri=True)
        source.row_factory=sqlite3.Row
        changed=0;desired=set()
        try:
            signature=stable_hash({
                'docs':[tuple(r) for r in source.execute('SELECT doc_id,content_hash,meta_json,retrieved_at FROM documents ORDER BY doc_id')],
                'observations':[tuple(r) for r in source.execute('SELECT * FROM observations ORDER BY source,dataset,series_key,query_sig,period')],
                'records':[tuple(r) for r in source.execute('SELECT source,dataset,row_hash FROM records ORDER BY source,dataset,row_hash')]})
            prior=self.conn.execute("SELECT signature FROM rag_sync_state WHERE name='statistics'").fetchone()
            if prior and prior[0]==signature:return 0
            for row in source.execute('SELECT * FROM documents'):
                desired.add(row['doc_id'])
                changed+=self.store.upsert_document(source=row['source'],doc_type=row['doc_type'],original_id=row['original_id'],
                    title=row['title'],body=row['body'],url=row['url'],published_at=row['published_at'],license=row['license'],meta=json.loads(row['meta_json']))
                self.conn.execute('UPDATE documents SET retrieved_at=? WHERE doc_id=?',(row['retrieved_at'],row['doc_id']))
            for row in self.conn.execute("SELECT doc_id FROM documents WHERE source IN ('kosis','ecos','naver')").fetchall():
                if row[0] not in desired:self.store.delete_document(row[0])
            for table in ('observations','records','dataset_versions'):
                self.conn.execute(f"DELETE FROM {table} WHERE source IN ('kosis','ecos','naver')")
                cursor=source.execute(f'SELECT * FROM {table}')
                columns=[d[0] for d in cursor.description]
                self.conn.executemany(f"INSERT INTO {table}({','.join(columns)}) VALUES({','.join('?' for _ in columns)})",
                    (tuple(row) for row in cursor))
            self.conn.execute("INSERT OR REPLACE INTO rag_sync_state VALUES('statistics',?)",(signature,))
            return changed
        finally:source.close()
