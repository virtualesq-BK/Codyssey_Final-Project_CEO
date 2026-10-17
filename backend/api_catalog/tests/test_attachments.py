import io,json,tempfile,unittest,zipfile
from pathlib import Path
from attachment_catalog import attachment_links,page_redirect,AttachmentCatalog
from forms_documents import extract_docx,extract_hwpx

HTML='''<div class="board_file"><ul><li class="clear"><a class="file_bg" title="[첨부파일] 무작위 이름.docx">무작위 이름.docx</a><div><ul><li><a href="javascript:void(0)" onclick="fnPdfView('ABC')">바로보기</a></li><li><a href="/afile/fileDownload/ABC" name="downloadBtn">다운로드</a></li></ul></div></li></ul></div>'''
URL='https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=123'

def docx(text='1. 사업 아이디어를 설명하세요.'):
    xml=f'''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:tbl><w:tr><w:tc><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:tc><w:tc><w:p/></w:tc></w:tr></w:tbl></w:body></w:document>'''
    b=io.BytesIO()
    # 동일한 내용의 테스트 파일은 실행 시각과 관계없이 동일한 바이트를 생성한다.
    with zipfile.ZipFile(b,'w') as z:
        z.writestr(zipfile.ZipInfo('word/document.xml', date_time=(2026,1,1,0,0,0)),xml)
    return b.getvalue()

class Fake:
    def __init__(self):self.body=docx();self.html=HTML;self.error=False
    def get(self,url,limit=None):
        if '/afile/' in url:
            if self.error:raise ValueError('download failed')
            return self.body,{'Content-Type':'application/octet-stream'},url
        return self.html.encode(),{},url

class AttachmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.fake=Fake();self.db=AttachmentCatalog(Path(self.tmp.name)/'db.sqlite',Path(self.tmp.name)/'files',self.fake)
    def tearDown(self):self.db.close();self.tmp.cleanup()
    def test_name_independent_link_and_filename_pair(self):
        links=attachment_links(HTML,URL);self.assertEqual(len(links),1);self.assertEqual(links[0]['file_id'],'ABC');self.assertEqual(links[0]['filename'],'무작위 이름.docx')
        self.assertEqual(attachment_links(HTML.replace('무작위 이름.docx','아무 제목'),URL)[0]['file_id'],'ABC')
    def test_safe_observed_redirect(self):
        html="var fullUrl = '/web/contents/bizpbanc-deadline.do?schM=view&pbancSn=123';"
        self.assertIn('deadline',page_redirect(html,URL,'123'));self.assertIsNone(page_redirect(html,URL,'124'))
        self.assertIsNone(page_redirect("var fullUrl='https://evil.test/?pbancSn=123';",URL,'123'))
    def test_original_versions_and_unchanged(self):
        first=self.db.crawl('123',URL)[0];again=self.db.crawl('123',URL)[0]
        self.assertEqual(first['version_id'],again['version_id']);self.assertEqual(again['change'],'unchanged')
        self.fake.body=docx('2. 변경된 문항입니다.');third=self.db.crawl('123',URL)[0]
        self.assertNotEqual(first['version_id'],third['version_id']);self.assertEqual(len(self.db.rows('SELECT * FROM attachment_versions')),2)
        self.fake.body=docx();self.assertEqual(self.db.crawl('123',URL)[0]['version_id'],first['version_id'])
    def test_docx_empty_cell_xpath(self):
        p=Path(self.tmp.name)/'file.docx';p.write_bytes(docx());blocks,warnings,state=extract_docx(p)
        self.assertEqual(len(blocks),2);self.assertEqual(blocks[1]['text'],'');self.assertIn('w:tc[2]',blocks[1]['location']['xpath'])
    def test_hwpx_text_and_empty_cells(self):
        p=Path(self.tmp.name)/'file.hwpx'
        text='''<sec xmlns:hp="urn:hp"><hp:p><hp:run><hp:t>표 앞 제목</hp:t><hp:tbl><hp:tr><hp:tc><hp:cellAddr rowAddr="0" colAddr="0"/><hp:cellSpan rowSpan="1" colSpan="1"/><hp:subList><hp:p><hp:run><hp:t>1. 문항</hp:t></hp:run></hp:p></hp:subList></hp:tc><hp:tc><hp:cellAddr rowAddr="0" colAddr="1"/><hp:subList><hp:p/></hp:subList></hp:tc></hp:tr></hp:tbl></hp:run></hp:p></sec>'''
        with zipfile.ZipFile(p,'w') as z:z.writestr('Contents/section0.xml',text)
        blocks,warnings,state=extract_hwpx(p);self.assertEqual(blocks[0]['text'],'표 앞 제목');self.assertEqual(blocks[-1]['text'],'');self.assertEqual(blocks[-1]['location']['cell_addr']['colAddr'],'1')
    def test_failure_does_not_remove_old_file(self):
        self.db.crawl('123',URL);self.fake.error=True;self.db.crawl('123',URL)
        row=self.db.rows('SELECT * FROM attachments')[0];self.assertIsNotNone(row['current_version_id']);self.assertEqual(row['active'],1);self.assertEqual(row['status'],'failed')
    def test_html_download_rejected(self):
        self.fake.body=b'<html>login</html>';out=self.db.crawl('123',URL);self.assertIn('error',out[0]);self.assertEqual(self.db.rows('SELECT * FROM attachment_versions'),[])
    def test_reviewed_mapping_contract(self):
        self.db.crawl('123',URL);aid=self.db.rows('SELECT * FROM attachments')[0]['id'];self.db.override_role(aid,'form')
        self.assertFalse(self.db.export('123')['attachments'][0]['ready_for_generation'])
        exported=self.db.export('123',True)['attachments'][0];fields=exported['fields'];self.assertTrue(fields)
        fields[0]['answer_block_ids']=['b00002'];p=Path(self.tmp.name)/'review.json';p.write_text(json.dumps(dict(fields=fields,mapping_validated=True)))
        self.db.review(exported['template_id'],p,'tester');self.assertTrue(self.db.export('123')['attachments'][0]['ready_for_generation'])
    def test_invalid_answer_mapping_rejected(self):
        self.db.crawl('123',URL);exported=self.db.export('123',True)['attachments'][0];fields=exported['fields'];fields[0]['answer_block_ids']=['missing'];p=Path(self.tmp.name)/'review.json';p.write_text(json.dumps(dict(fields=fields,mapping_validated=True)))
        with self.assertRaises(ValueError):self.db.review(exported['template_id'],p,'tester')
    def test_hwp_cannot_be_called_generation_ready(self):
        self.fake.body=bytes.fromhex('d0cf11e0a1b11ae1')+b'fake';self.fake.html=HTML.replace('무작위 이름.docx','신청서.hwp');self.db.crawl('123',URL)
        self.assertFalse(self.db.export('123')['attachments'][0]['ready_for_generation'])

if __name__=='__main__':unittest.main()
