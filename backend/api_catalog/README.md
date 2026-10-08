# K-Startup 공고·참고자료 DB (v1.3.0)

먼저 [REFERENCE_GUIDE.md](REFERENCE_GUIDE.md)를 읽어 주세요. API 7종 전체 수집, 팀원용 내보내기, 인증키 설정과 향후 API 확장 방법이 정리되어 있습니다.

# K-Startup API 공고 DB

기존 api_catalog.py는 K-Startup API 원본을 SQLite에 저장합니다.
이번 확장본에는 상세 페이지 첨부 수집·원본 버전 관리·양식 구조 추출을 위한
attachment_catalog.py를 추가했습니다. 인증키는 .env에 나중에 입력할 수 있습니다.

**첨부 수집과 양식 DB 사용법은 [ATTACHMENTS_GUIDE.md](ATTACHMENTS_GUIDE.md)를 먼저 읽어 주세요.**
원본 API 수집 코드는 유지했고, 완성 문서 생성은 출력 담당자가 연결하는 범위입니다.

## 분류 기준

- 마감일까지 4일 이상: `모집중`
- D-3부터 D-Day까지: `마감임박(D-3)`
- 마감일 경과: `마감`

## 실행

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
Copy-Item .env.example .env
# .env에 DATA_GO_KR_SERVICE_KEY 입력

# API 전체 수집 및 갱신
.\.venv\Scripts\python.exe api_catalog.py sync

# 저장 결과 조회
.\.venv\Scripts\python.exe api_catalog.py list
.\.venv\Scripts\python.exe api_catalog.py list --status "마감임박(D-3)"

# API 호출 없이 날짜 분류만 갱신
.\.venv\Scripts\python.exe api_catalog.py refresh-status

# 보관한 API JSON 가져오기
.\.venv\Scripts\python.exe api_catalog.py import-json sample\sample_announcement.json

# 테스트
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

DB 기본 경로는 `data/api_catalog.sqlite3`입니다. 모든 API 원본 필드는
`raw_json`에 그대로 보존되고 자주 조회하는 필드는 별도 컬럼에도 저장됩니다.

## 선택 의존성 설치

기본 API 수집과 SQLite 저장은 Python 표준 라이브러리만으로 실행됩니다. 첨부 문서까지 처리하려면 필요한 형식에 맞춰 선택 의존성을 설치합니다.

```powershell
# PDF 텍스트 추출
.\.venv\Scripts\python.exe -m pip install -e ".[documents]"

# 구형 HWP 평문 추출
.\.venv\Scripts\python.exe -m pip install -e ".[hwp]"

# PDF와 HWP 지원을 한 번에 설치
.\.venv\Scripts\python.exe -m pip install -e ".[documents,hwp]"
```

- `documents`: `pdfplumber`를 설치합니다. PDF는 페이지별 참고 텍스트로 추출되며 자동 입력 위치로 취급하지 않습니다.
- `hwp`: `pyhwp`, `six`와 `hwp5txt`를 설치합니다. HWP는 평문을 추출하지만 표·빈 셀·정확한 입력 위치는 보존하지 못하므로 `needs_mapping` 상태가 됩니다.
- DOCX와 HWPX: 추가 패키지 없이 XML 문단·표 셀·빈 셀과 원문 위치를 추출합니다.
- 구형 DOC: LibreOffice가 별도로 필요합니다. Windows에서는 LibreOffice를 설치하고 `soffice.exe`가 `PATH`에 있어야 합니다. 설치 후 새 터미널에서 `soffice --version`으로 확인합니다.

Windows에서 JSON/JSONL 한글 테스트가 기본 CP949 인코딩의 영향을 받는 경우 UTF-8 모드로 실행합니다.

```powershell
$env:PYTHONUTF8="1"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

의존성 설치 확인:

```powershell
.\.venv\Scripts\python.exe -c "import pdfplumber; print(pdfplumber.__version__)"
.\.venv\Scripts\hwp5txt.exe --help
soffice --version  # 구형 DOC 변환을 사용할 때만 필요
```
