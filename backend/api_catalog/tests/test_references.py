import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from reference_catalog import ReferenceCatalog, DATASETS, ApiClient, ApiError, decode_payload, unpack, is_current, export, normalize

EXAMPLES = {
 'announcements': {'pbanc_sn':'777','biz_pbanc_nm':'지원사업','pbanc_rcpt_bgng_dt':'20260101','pbanc_rcpt_end_dt':'20991231','Rcrt_prgs_yn':'Y','pbanc_ctnt':'<p>설명</p>','custom':{'preserve':True}},
 'businesses': {'biz_yr':'2026','biz_category_cd':'cmrczn_tab1','supt_biz_titl_nm':'창업 지원사업','biz_supt_bdgt_info':'1억원','supt_biz_intrd_info':'<p>사업 소개</p>'},
 'contents': {'titl_nm':'창업 공지','clss_cd':'notice_matr','detl_pg_url':'www.k-startup.go.kr/web/contents/webNotice_MATR.do?id=1&schM=view','file_nm':'안내.pdf','fstm_reg_dt':'2026-01-01'},
 'statistics': {'titl_nm':'창업 통계','ctnt':'<p>통계 본문</p><script>hidden</script>','detl_pg_url':'www.k-startup.go.kr/web/contents/webFND_STATS_RSCH_DATA.do?id=1&schM=view','last_mdfcn_dt':'2026-01-01','file_nm':'보고서.pdf'},
}

class Fake:
 def __init__(self,pages):self.pages=pages;self.calls=[]
 def fetch(self,dataset,page,current_only=True):
  self.calls.append((dataset.name,page,current_only))
  value=self.pages[page-1]
  if isinstance(value,Exception):raise value
  return value

class ReferencesTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name);self.db=ReferenceCatalog(self.path/'db.sqlite')
 def tearDown(self):self.db.close();self.tmp.cleanup()
 def test_all_datasets_preserve_fields(self):
  for name,raw in EXAMPLES.items():self.assertEqual(self.db.upsert(name,raw),'new')
  rows=list(self.db.records());self.assertEqual(len(rows),4)
  for r in rows:self.assertEqual(r['raw'],EXAMPLES[r['dataset']])
  stat=next(r for r in rows if r['dataset']=='statistics');self.assertNotIn('hidden',stat['body_text']);self.assertIn('통계 본문',stat['body_text'])
 def test_update_revert_and_stable_key(self):
  raw=dict(EXAMPLES['contents']);self.db.upsert('contents',raw);old=list(self.db.records())[0]
  self.assertEqual(self.db.upsert('contents',raw),'unchanged');self.assertEqual(list(self.db.records())[0]['changed_at'],old['changed_at'])
  raw['titl_nm']='변경 제목';self.assertEqual(self.db.upsert('contents',raw),'updated')
  self.assertEqual(list(self.db.records())[0]['id'],old['id'])
  self.db.upsert('contents',EXAMPLES['contents']);self.assertEqual(self.db.conn.execute('SELECT COUNT(*) FROM reference_versions').fetchone()[0],2)
 def test_pagination_and_raw_page(self):
  a=dict(EXAMPLES['contents']);b=dict(a,detl_pg_url='https://www.k-startup.go.kr/x?id=2')
  client=Fake([{'data':[a],'totalCount':2},{'data':[b],'totalCount':2}])
  out=self.db.sync('contents',client);self.assertEqual(out['status'],'success');self.assertEqual(out['new'],2)
  self.assertEqual(self.db.conn.execute('SELECT COUNT(*) FROM reference_sync_pages').fetchone()[0],2)
 def test_repeated_page_is_failed_not_success(self):
  p={'data':[EXAMPLES['contents']]};out=self.db.sync('contents',Fake([p,p]),max_pages=2)
  self.assertEqual(out['status'],'failed');self.assertIn('반복',out['error']);self.assertEqual(len(list(self.db.records())),1)
 def test_error_response_does_not_mean_empty(self):
  with self.assertRaises(ApiError):unpack({'response':{'header':{'resultCode':'22'},'body':{'items':''}}})
  with self.assertRaises(ApiError):unpack({'error':'failure'})
 def test_xml_and_singleton_rows(self):
  xml=b'<response><header><resultCode>00</resultCode></header><body><items><item><titl_nm>Title</titl_nm></item></items><totalCount>1</totalCount></body></response>'
  rows,total=unpack(decode_payload(xml));self.assertEqual(total,1);self.assertEqual(rows[0]['titl_nm'],'Title')
  with self.assertRaises(ApiError):decode_payload(b'<!DOCTYPE x><x/>')
 def test_current_filter_and_projection(self):
  raw=dict(EXAMPLES['announcements']);closed=dict(raw,pbanc_sn='778',pbanc_rcpt_end_dt='20000101')
  out=self.db.sync('announcements',Fake([{'data':[raw,closed],'totalCount':2}]))
  self.assertEqual(out['skipped'],1);self.assertEqual(len(list(self.db.records())),1)
  row=self.db.conn.execute('SELECT * FROM api_announcements').fetchone();self.assertEqual(row['source_id'],'777');self.assertEqual(row['open_flag'],'Y')
  self.assertFalse(is_current(dict(normalize(raw),pbanc_rcpt_bgng_dt='20990101'),date(2026,1,1)))
 def test_failed_other_dataset_preserves_success(self):
  a=self.db.sync('businesses',Fake([{'data':[EXAMPLES['businesses']],'totalCount':1}]))
  b=self.db.sync('statistics',Fake([ApiError('API HTTP 429')]))
  self.assertEqual(a['status'],'success');self.assertEqual(b['status'],'failed');self.assertEqual(len(list(self.db.records())),1)
 def test_export_csv_jsonl_and_chunks_provenance(self):
  self.db.upsert('statistics',EXAMPLES['statistics'])
  for fmt in ('jsonl','csv','chunks'):
   path=self.path/('out.'+fmt);result=export(self.db,path,fmt=fmt);self.assertEqual(result['rows'],1)
  obj=json.loads((self.path/'out.jsonl').read_text());self.assertEqual(obj['raw'],EXAMPLES['statistics'])
  chunk=json.loads((self.path/'out.chunks').read_text());self.assertTrue(chunk['source_url'].startswith('https://'));self.assertIn('첨부 원문 미포함',chunk['coverage'])
 def test_short_page_without_total_continues_until_empty(self):
  out=self.db.sync('contents',Fake([{'data':[EXAMPLES['contents']]},{'data':[]}]))
  self.assertEqual(out['pages'],2);self.assertEqual(out['status'],'success')
 def test_page_limit_is_explicit_failure(self):
  out=self.db.sync('contents',Fake([{'data':[EXAMPLES['contents']]}]),max_pages=1)
  self.assertEqual(out['status'],'failed');self.assertIn('상한',out['error'])
 def test_same_business_name_separate_years(self):
  raw=EXAMPLES['businesses'];self.db.upsert('businesses',raw);self.db.upsert('businesses',dict(raw,biz_yr='2025'))
  self.assertEqual(len(list(self.db.records())),2)

if __name__=='__main__':unittest.main()
