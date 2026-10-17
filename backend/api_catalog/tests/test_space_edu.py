import json,tempfile,unittest,urllib.parse
from pathlib import Path
from unittest.mock import patch
from reference_catalog import ReferenceCatalog,ApiClient,DATASETS,unpack,export
from test_references import Fake

CENTER={'cntr_id':10,'buld_id':20,'cntr_nm':'예제 창업센터','buld_nm':'예제 건물','regin_clss':'세종특별자치시','addr':'세종시 예제 주소','latde':36.5,'lgtde':127.3,'spce_cnt':2,'hmpg':'https://example.org/center'}
SPACE={'spce_id':30,'cntr_id':10,'buld_id':20,'spce_nm':'예제 보육실','cntr_nm':'예제 창업센터','rent':0,'guam':'1,000,000','rsvt_psbl_clss':'UNKNOWN','addr':'세종시 예제 주소'}
EDU={'lctr_nm':'예제 창업교육','lctr_istc':'사업계획 작성 방법','kywrd':'창업, 사업계획','lctr_pg_url':'https://example.org/lecture?id=40','play_time':'00:20:00','lctr_lclss_cd':'TEST','reg_dt':'2026-01-01','mdfcn_dt':'2026-10-01'}

class SpaceEduTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.db=ReferenceCatalog(Path(self.tmp.name)/'db.sqlite')
 def tearDown(self):self.db.close();self.tmp.cleanup()
 def test_nested_data_and_match_count(self):
  rows,count=unpack({'data':{'data':[SPACE]},'totalCount':999,'matchCount':1})
  self.assertEqual(rows,[SPACE]);self.assertEqual(count,1)
  result=self.db.sync('spaces',Fake([{'data':{'data':[SPACE]},'totalCount':999,'matchCount':1}]))
  self.assertEqual(result['status'],'success');self.assertEqual(result['pages'],1)
 def test_space_before_center_link_and_multiple_buildings(self):
  self.db.upsert('spaces',SPACE);self.assertEqual(list(self.db.records('spaces'))[0]['related_centers'],[])
  self.db.upsert('centers',CENTER);self.db.upsert('centers',dict(CENTER,buld_id=21))
  row=list(self.db.records('spaces'))[0];self.assertEqual(len(row['related_centers']),1)
  self.assertIn('rent\n0',row['body_text']);self.assertEqual(row['attributes']['rent'],0);self.assertEqual(row['attributes']['deposit'],1000000)
  self.assertEqual(row['attributes']['reservation_code'],'UNKNOWN')
  self.assertEqual(len(list(self.db.records('centers'))),2)
 def test_lecture_identity_title_change_and_original(self):
  self.db.upsert('education',EDU);old=list(self.db.records('education'))[0]
  self.db.upsert('education',dict(EDU,lctr_nm='변경된 강좌'))
  new=list(self.db.records('education'))[0]
  self.assertEqual(new['id'],old['id']);self.assertEqual(new['source'],'education');self.assertEqual(new['source_modified_at'],'2026-10-01')
  self.assertEqual(new['attributes']['play_time'],'00:20:00')
 def test_missing_id_not_guessed(self):
  for ds,row,key in [('centers',CENTER,'cntr_id'),('spaces',SPACE,'spce_id'),('education',EDU,'lctr_pg_url')]:
   row=dict(row);row.pop(key)
   with self.assertRaises(ValueError):self.db.upsert(ds,row)
 def test_key_case_endpoint_and_filters(self):
  captured=[]
  class Response:
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self,*args):return b'{"data":[],"totalCount":0}'
  def fakeopen(request,**kwargs):captured.append(request.full_url);return Response()
  with patch('reference_catalog.urllib.request.urlopen',fakeopen),patch('reference_catalog.time.sleep'):
   ApiClient('testkey',filters={'cond[rent::LTE]':'500000'}).fetch(DATASETS['spaces'],1)
   ApiClient('testkey').fetch(DATASETS['education'],1)
  params=urllib.parse.parse_qs(urllib.parse.urlsplit(captured[0]).query)
  self.assertIn('/kisedSlpService/getCenterSpaceList',captured[0]);self.assertEqual(params['cond[rent::LTE]'],['500000']);self.assertIn('serviceKey',params)
  params=urllib.parse.parse_qs(urllib.parse.urlsplit(captured[1]).query)
  self.assertIn('/kisedEduService/getEducationInformation',captured[1]);self.assertIn('ServiceKey',params);self.assertNotIn('serviceKey',params)
 def test_old_records_and_export_after_reopen(self):
  from test_references import EXAMPLES
  self.db.upsert('contents',EXAMPLES['contents']);self.db.close()
  self.db=ReferenceCatalog(Path(self.tmp.name)/'db.sqlite')
  for ds,row in [('centers',CENTER),('spaces',SPACE),('education',EDU)]:self.db.upsert(ds,row)
  p=Path(self.tmp.name)/'out.jsonl';export(self.db,p)
  rows=[json.loads(line) for line in p.read_text().splitlines()]
  self.assertEqual(len(rows),4);self.assertEqual(next(r for r in rows if r['dataset']=='spaces')['raw'],SPACE)

if __name__=='__main__':unittest.main()
