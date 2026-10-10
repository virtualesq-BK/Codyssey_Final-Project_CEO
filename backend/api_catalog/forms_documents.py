"""원본은 수정하지 않으며 XML 위치/셀/빈칸을 보존한다."""
import io
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

PARSER_VERSION='forms-blocks-v1'
MAX_XML=20*1024*1024

def bundled_tool(name):
    """Find a console script on PATH or next to the active Python executable."""
    found=shutil.which(name) or shutil.which(name+'.exe')
    if found:return found
    candidate=Path(sys.executable).parent/(name+'.exe' if sys.platform=='win32' else name)
    return str(candidate) if candidate.is_file() else None


def xml(data):
    if len(data)>MAX_XML or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise ValueError('크기 초과 또는 DTD/ENTITY 포함 XML')
    return ET.fromstring(data)

def tag(node):return node.tag.rsplit('}',1)[-1]

def classify(name,blocks):
    text='\n'.join(b['text'] for b in blocks[:40])[:5000]
    candidates=[]
    checks=[('manual',r'매뉴얼|메뉴얼|사용자 가이드|신청 가이드'),('form',r'신청서|사업계획서|작성양식|작성 양식|지원양식|지원 양식|서식'),('notice',r'공고문|모집 공고|모집공고|안내문'),('other',r'포스터|홍보물')]
    for role,pattern in checks:
        score=(3 if re.search(pattern,name) else 0)+(2 if re.search(pattern,text) else 0)
        if score:candidates.append((score,role))
    candidates.sort(reverse=True)
    if not candidates or (len(candidates)>1 and candidates[0][0]==candidates[1][0]):return 'unknown'
    return candidates[0][1]

def zip_read(z,name):
    info=z.getinfo(name)
    if info.file_size>MAX_XML:raise ValueError('XML 압축 해제 크기 상한 초과')
    return z.read(name)

def detect(data):
    if data.startswith(b'%PDF'):return 'pdf'
    if data.startswith(b'PK'):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names=z.namelist()
                if 'word/document.xml' in names:return 'docx'
                if any(re.fullmatch(r'Contents/section\d+\.xml',n) for n in names):return 'hwpx'
        except zipfile.BadZipFile:pass
        return 'zip'
    if data.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):return 'ole'
    if data.startswith(b'\x89PNG'):return 'png'
    if data.startswith(b'\xff\xd8\xff'):return 'jpg'
    if b'<html' in data[:3000].lower() or b'<!doctype html' in data[:3000].lower():return 'html'
    return 'unknown'

def extract_docx(path):
    with zipfile.ZipFile(path) as z:
        root=xml(zip_read(z,'word/document.xml'));warnings=[]
        if any(n.startswith(('word/footnotes','word/endnotes')) for n in z.namelist()):warnings.append('각주/미주 별도 확인 필요')
    blocks=[]
    def add(node,kind,location):
        texts=[]
        first_para=True
        for n in node.iter():
            if tag(n)=='p':
                if not first_para:texts.append('\n')
                first_para=False
            if tag(n)=='t':texts.append(n.text or '')
            elif tag(n) in ('br','cr'):texts.append('\n')
            elif tag(n)=='tab':texts.append('\t')
        blocks.append(dict(id=f'b{len(blocks)+1:05d}',kind=kind,text=''.join(texts),location=location))
    body=next(n for n in root if tag(n)=='body')
    for index,n in enumerate(body):
        base=f'/w:document/w:body/*[{index+1}]'
        if tag(n)=='p':add(n,'paragraph',dict(xml_part='word/document.xml',xpath=base))
        elif tag(n)=='tbl':
            rows=[v for v in n if tag(v)=='tr']
            for ri,row in enumerate(rows):
                grid=0
                for ci,cell in enumerate(v for v in row if tag(v)=='tc'):
                    prop=next((v for v in cell if tag(v)=='tcPr'),None)
                    span=next((v for v in prop if tag(v)=='gridSpan'),None) if prop is not None else None
                    merge=next((v for v in prop if tag(v)=='vMerge'),None) if prop is not None else None
                    width=int(next(iter(span.attrib.values()))) if span is not None else 1
                    add(cell,'cell',dict(xml_part='word/document.xml',xpath=f'{base}/w:tr[{ri+1}]/w:tc[{ci+1}]',table_index=index,row=ri,column=grid,colspan=width,vmerge=dict(merge.attrib) if merge is not None else None));grid+=width
                    if any(tag(v)=='tbl' for v in cell.iter()):warnings.append('중첩표 셀 위치 수동 확인 필요')
    if any(tag(n) in ('drawing','pict','txbxContent') for n in root.iter()):warnings.append('이미지/도형/텍스트상자 내 문항 수동 확인 필요')
    return blocks,sorted(set(warnings)),'xml_candidate'

def extract_hwpx(path):
    blocks=[];warnings=[]
    with zipfile.ZipFile(path) as z:
        names=sorted((n for n in z.namelist() if re.fullmatch(r'Contents/section\d+\.xml',n)),key=lambda n:int(re.search(r'\d+',n)[0]))
        for part in names:
            root=xml(zip_read(z,part))
            if any(tag(v) in ('pic','ole','shape','rect') for v in root.iter()):warnings.append('HWPX 이미지/도형 내용 수동 확인 필요')
            def walk(node,xpath,in_cell=False):
                kind=tag(node)
                if kind=='tc':
                    texts=[]
                    for v in node.iter():
                        if tag(v)=='t':texts.append(v.text or '')
                        elif tag(v)=='p' and texts:texts.append('\n')
                    addr=next((dict(v.attrib) for v in node if tag(v)=='cellAddr'),{})
                    span=next((dict(v.attrib) for v in node if tag(v)=='cellSpan'),{})
                    blocks.append(dict(id=f'b{len(blocks)+1:05d}',kind='cell',text=''.join(texts),location=dict(xml_part=part,xpath=xpath,cell_addr=addr,cell_span=span)))
                    if sum(tag(v)=='tbl' for v in node.iter())>0:warnings.append('HWPX 중첩표는 셀 위치 수동 확인 필요')
                    return
                if kind=='p' and any(tag(v)=='tbl' for v in node.iter()):
                    def outer_text(n):
                        if tag(n)=='tbl':return ''
                        if tag(n)=='t':return n.text or ''
                        return ''.join(outer_text(c) for c in n)
                    surrounding=outer_text(node)
                    if surrounding.strip():blocks.append(dict(id=f'b{len(blocks)+1:05d}',kind='paragraph',text=surrounding,location=dict(xml_part=part,xpath=xpath)))
                if kind=='p' and not any(tag(v)=='tbl' for v in node.iter()):
                    blocks.append(dict(id=f'b{len(blocks)+1:05d}',kind='paragraph',text=''.join(v.text or '' for v in node.iter() if tag(v)=='t'),location=dict(xml_part=part,xpath=xpath)))
                    return
                if kind in ('pic','ole','shape','rect'):warnings.append('HWPX 이미지/도형 내용 수동 확인 필요')
                counts={}
                for child in node:
                    local=tag(child);counts[local]=counts.get(local,0)+1
                    walk(child,xpath+f'/*[local-name()="{local}"][{counts[local]}]')
            walk(root,'/*[1]')
    return blocks,sorted(set(warnings)),'xml_candidate'

def extract(path,filename):
    path=Path(path);data=path.read_bytes();fmt=detect(data)
    if fmt=='docx':return (*extract_docx(path),fmt)
    if fmt=='hwpx':return (*extract_hwpx(path),fmt)
    if fmt=='pdf':
        try:import pdfplumber
        except ImportError:return [],['PDF 텍스트 추출에는 pip install -e .[documents] 필요'],'needs_parser',fmt
        blocks=[];warnings=[]
        with pdfplumber.open(path) as d:
            if len(d.pages)>100:raise ValueError('PDF 100페이지 상한 초과')
            for pi,p in enumerate(d.pages,1):
                text=p.extract_text() or ''
                blocks.append(dict(id=f'b{len(blocks)+1:05d}',kind='page_text',text=text,location=dict(page=pi)))
                if len(text.strip())<20:warnings.append(f'{pi}페이지 텍스트 부족: OCR 필요')
        return blocks,warnings,'reference_only',fmt
    if fmt=='ole' and filename.lower().endswith('.hwp'):
        tool=bundled_tool('hwp5txt')
        if not tool:return [],['HWP 원본 보관 완료. pyhwp 설치 또는 HWPX/DOCX 변환본 등록 필요'],'needs_conversion','hwp'
        p=subprocess.run([tool,str(path.resolve())],capture_output=True,timeout=60)
        if p.returncode:raise ValueError('HWP 추출 실패: 암호/버전/손상 확인 필요')
        blocks=[dict(id=f'b{i+1:05d}',kind='converted_text',text=t,location=dict(converter='hwp5txt',line=i+1)) for i,t in enumerate(p.stdout.decode('utf-8').splitlines())]
        return blocks,['HWP 평문 변환: 표/빈칸/원본 삽입 위치는 미확정'],'needs_mapping','hwp'
    if fmt=='ole' and filename.lower().endswith('.doc'):
        tool=shutil.which('libreoffice') or shutil.which('soffice')
        if not tool:return [],['DOC 원본 보관 완료. LibreOffice 설치 또는 DOCX 변환본 필요'],'needs_conversion','doc'
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'input.doc';source.write_bytes(data)
            p=subprocess.run([tool,f'-env:UserInstallation={(Path(tmp)/"profile").as_uri()}','--headless','--convert-to','docx','--outdir',tmp,str(source)],capture_output=True,timeout=90)
            converted=Path(tmp)/'input.docx'
            if p.returncode or not converted.exists():raise ValueError('DOC 변환 실패')
            blocks,warnings,state=extract_docx(converted)
            converted_path=path.with_name(path.name+'.converted.docx');shutil.copy2(converted,converted_path)
            return blocks,warnings+['변환 DOCX 위치 기준. 원본 DOC와 서식/문항 비교 필요'],'converted_xml_candidate','doc'
    return [],['지원하지 않는 형식 또는 이미지/ZIP. 원본 보관 후 관리자 확인 필요'],'unsupported',fmt


def field_candidates(blocks):
    fields=[];current=None
    for b in blocks:
        for text in b['text'].splitlines():
            text=text.strip()
            if not text:continue
            if re.match(r'^(?:\d+[.)]|[①-⑳]|[ⅠⅡⅢⅣⅤ]|[가-힣][.)])\s*',text):
                current=dict(label=text,guidance=None,max_chars=None,count_spaces=None,max_pages=None,answer_block_ids=[],evidence=[dict(block_id=b['id'],quote=text)])
                fields.append(current)
            elif current and text.startswith(('※','작성요령','작성 안내','*')):
                current['guidance']=(current['guidance']+'\n' if current['guidance'] else '')+text
                current['evidence'].append(dict(block_id=b['id'],quote=text))
            if current and text.startswith(('※','작성요령','작성 안내','*')):
                chars=re.search(r'([\d,]+)\s*자\s*(?:이내|이하)',text);pages=re.search(r'(\d+)\s*(?:페이지|쪽)\s*(?:이내|이하)',text)
                if chars:current['max_chars']=int(chars[1].replace(',',''))
                if pages:current['max_pages']=int(pages[1])
                if '공백 포함' in text:current['count_spaces']=True
                if '공백 제외' in text:current['count_spaces']=False
    return fields
