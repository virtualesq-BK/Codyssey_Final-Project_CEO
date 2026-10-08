# K-Startup API 공고 DB

K-Startup API가 직접 제공하는 공고 원본만 SQLite에 저장합니다. 상세 게시글,
첨부 파일, 문서 추출, AI 분석 기능은 포함하지 않습니다.

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
