# bizrag — 사업 아이디어 평가 에이전트용 RAG 수집기

무료 공공·민간 API를 **소스별 주기(월·주·일·검색 시)** 에 맞춰 수집해 하나의 지식 DB(`data/knowledge.db`)에 쌓고,
에이전트(Claude 등)가 **MCP 도구**로 조회하게 하는 프로젝트입니다.

```
[주기 수집 sync]  ──┐
  월: KOSIS·한국은행·법령·World Bank·네이버 쇼핑분야·소비자 피해구제
  주: 생필품 가격·뉴스심리지수 ├──▶  knowledge.db  ◀── 에이전트 (MCP 도구)
  일: inbox CSV       │      ├ 문서(RAG): 법령 조문·특허 초록·통계표 카탈로그·소비자 불만 요약·경제지표 요약
[검색 시 수집]  ─────┘      ├ 시계열: 네이버 지수·KOSIS·한국은행·World Bank·피해구제 건수
  네이버 트렌드·쇼핑키워드      └ 원자료: 가격표·피해구제·해외진출기업·CSV
  KIPRIS·법령·KOSIS 표   (결과를 DB에 저장 + 캐시 → 쓸수록 DB가 자람)
```

## 1. 할 일은 3단계

### ① 키 발급 (무료, 필요한 것만)

| 소스 | 발급처 | 비고 |
|---|---|---|
| 네이버 | [NCP 콘솔 > NAVER API HUB](https://console.ncloud.com) | 2026년 개발자센터에서 **NAVER API HUB(네이버 클라우드)로 이관**됨. API HUB 이용 신청 → 앱 등록 → **검색어 트렌드·쇼핑인사이트** 추가 → 앱의 Client ID/Secret을 `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET`에 입력 (계정 IAM 키 아님). 쇼핑 검색 API는 이관되지 않아 지원하지 않음 |
| KOSIS | [kosis.kr/openapi](https://kosis.kr/openapi/) | 회원가입 → 활용신청 → 즉시 발급 |
| 한국은행 | [ecos.bok.or.kr/api](https://ecos.bok.or.kr/api/) | 회원가입 → 인증키 신청 → 즉시 발급. `BOK_API_KEY` |
| 법령 | [open.law.go.kr](https://open.law.go.kr) | OPEN API 신청. `LAW_OC`=가입 이메일 @ 앞부분. 신청서에 **이 PC의 공인 IP** 등록 필요 |
| KIPRIS Plus | [plus.kipris.or.kr](https://plus.kipris.or.kr) | 특허·실용 공개/등록공보 상품 무료 이용신청 |
| 공공데이터포털 | [data.go.kr](https://www.data.go.kr) | 마이페이지의 일반 인증키(Decoding). 그리고 아래 데이터셋마다 **[활용신청]** 클릭 |
| World Bank | — | 키 불필요 |

공공데이터포털에서 활용신청할 데이터셋(주소의 숫자가 ID):
- `3040720` 한국소비자원 소비자 피해구제 정보 (분기별, 자동변환 API 확인됨)
- `15083256` 한국소비자원 생필품 및 서비스 가격 정보
- `15034787` KOTRA 해외진출기업

### ② 설치 + 키 점검
- **Windows**: `setup_and_check.bat` 더블클릭 → 메모장에 키 입력·저장 → 점검 결과 확인
- **Mac/Linux**: `bash setup_and_check.sh` (첫 실행 후 `.env` 편집, 다시 실행)

```
✅ 네이버 검색어트렌드·쇼핑인사이트  검색어트렌드 OK, 쇼핑인사이트 OK
❌ 국가법령정보 (법제처)          법제처가 사용자 검증을 거부
   └ open.law.go.kr > 마이페이지에서 승인 여부와 등록한 IP가 지금 PC와 같은지 확인
⬜ KIPRIS Plus 특허              KIPRIS_API_KEY 미입력
```
❌가 나오면 아래 줄의 안내대로 고치고 다시 실행하면 됩니다.

### ③ 수집·조회 확인
```bash
python -m bizrag sync                 # 최초 수집 (주기가 된 것만 실행)
python -m bizrag try 텀블러            # 검색 시 수집 시험 (네이버·KOSIS·법령·특허)
python -m bizrag search "헬스장 계약해제"  # 쌓인 문서 검색
python -m bizrag status               # 소스별 마지막 수집·다음 예정·DB 현황
```
가상환경을 쓴다면 먼저 `.venv\Scripts\activate`(Windows) 또는 `source .venv/bin/activate`.

## 2. 매일 자동 수집 걸어두기
`sync`는 각 작업의 마지막 성공 시각을 보고 주기가 된 것만 호출하므로, **하루 1번만** 예약하면 됩니다.
- Windows 작업 스케줄러: 기본 작업 만들기 → 매일 → 프로그램 `daily_sync.bat` (로그: `logs/sync.log`)
- Mac/Linux crontab: `30 6 * * * cd /경로/bizrag && .venv/bin/python -m bizrag sync >> logs/sync.log 2>&1`

실패한 작업은 성공으로 기록되지 않아 다음날 자동 재시도됩니다.

## 3. 에이전트에 연결 (Claude Desktop 예시)
`claude_desktop_config.json`의 `mcpServers`에 추가:
```json
"bizrag": {
  "command": "C:\\경로\\bizrag\\.venv\\Scripts\\python.exe",
  "args": ["C:\\경로\\bizrag\\run_mcp.py"]
}
```
제공 도구: `inventory`, `search_knowledge`, `get_series`, `find_records`(저장된 지식 조회) /
`naver_search_trend`, `naver_shopping_keywords`, `kosis_find_tables`, `kosis_fetch_table`,
`bok_find_tables`, `bok_table_items`, `bok_fetch_table`,
`law_search`, `law_add`, `patent_search`, `worldbank_indicator`(필요 시 수집 → DB 누적) / `source_status`

## 4. 수집 주기 설계

| 주기 | 작업 | 저장 형태 |
|---|---|---|
| 월 | 네이버 쇼핑 1분류 클릭 추이 + 분야별 연령·성별 | 시계열 |
| 월 | KOSIS 감시 검색어 → 통계표 카탈로그 | 문서 (에이전트가 표를 찾는 목차) |
| 월 | KOSIS 감시 표 + **에이전트가 조회했던 표** 갱신 | 시계열 |
| 월 | 감시 법령 개정 확인 → 바뀐 법령만 조문 재적재 (`law_add`로 추가한 법령 포함) | 문서(조문 단위) |
| 주 | 한국은행: 소비자동향조사(CSI)·기업경기조사(BSI, 전체·세부업종)·기업경영분석(분기·연간)·가계 목적별 최종소비지출(명목·실질)·뉴스심리지수(일간 → 주간 평균) — **새 공표가 있을 때만 증분 수집** | 시계열 + 분류별 요약 문서 |
| 월 | 한국은행 ECOS 통계표 카탈로그 (바뀐 표만 재색인) | 문서 (에이전트가 표를 찾는 목차) |
| 월 | World Bank 10개국 × 8개 지표 | 시계열 |
| 월 | 소비자 피해구제 **새 분기만** 적재 → 품목×청구이유 집계 | 시계열 + 품목별 불만 요약 문서 |
| 주 | 생필품 가격 새 버전 확인 | 원자료 |
| 일 | `inbox/` CSV 적재 (국가데이터처 온라인 가격정보 등 수동 자료) | 원자료 |
| 검색 시 | 네이버 검색어 트렌드(캐시 7일), 쇼핑 키워드(7일), 특허(30일), 법령 검색(30일), KOSIS 표(7일) | 결과를 DB에 저장 |

설정은 모두 `config/sources.yaml`에서 바꿉니다 (감시 검색어·법령·국가·지표·데이터셋 추가).

## 5. 데이터 해석 원칙 (에이전트 지침에도 포함)
- 네이버 지수는 **조회 조건 안의 상대값**. `query_sig`가 같은 값끼리만 비교. 검색 관심도 ≠ 구매 의사
- 특허 검색은 유사 기술 후보일 뿐, 침해·독점 판단 근거 아님
- 법령은 원문 그대로 저장(해석은 별도). 시행일자 메타데이터 확인
- 피해구제 건수 증가는 판매량 증가 영향일 수 있음
- 한국은행 CSI·BSI·뉴스심리지수는 100 기준 심리지표(실제 매출·소비액 아님). 뉴스심리지수 주간 값은 수집기가 일간 값을 평균한 것
- 기업경영분석은 업종 **평균**(분기는 외감기업, 연간은 전수 법인) — 소상공인·개인사업자 수익성과 다를 수 있음
- 가계 목적별 소비지출(원계열)은 계절성이 커서 직전 분기보다 **전년동기 대비**로 볼 것

### 한국은행 데이터 구조
| 항목 | 통계코드 | 주기 | 요약 문서 단위 |
|---|---|---|---|
| 소비자동향조사 | 511Y002 | 월 | 분류별 (전체·성별·연령·소득·지역) |
| 기업경기조사 실적/전망 | 512Y013 / 512Y014 | 월 | 업종 그룹별 (전산업·제조업·서비스업·대/중소기업…) |
| 업종별 기업경기조사 실적/전망 | 512Y007 / 512Y008 | 월 | 세부 업종별 46개 |
| 뉴스심리지수 | 523Y001 | 일 → 주간 평균 | 1개 |
| 기업경영분석(분기) 성장성/손익 | 502Y001 / 502Y002 | 분기 | 업종별 |
| 기업경영분석(연간) 성장성/손익 | 501Y005 / 501Y006 | 연 | 세부 업종별 (규모: 종합·대·중견·중소·중·소기업) |
| 가계 목적별 최종소비지출 명목/실질 | 200Y142 / 200Y143 | 분기 | 1개 (목적 17개) |

시계열은 `get_series(dataset="bok:<통계코드>")`, `query_sig`는 주기(`M`·`Q`·`A`·`D`, 주간 평균은 `W`).

**갱신 확인 → 증분 수집** (매번 전체를 받지 않음)
1. 표마다 ECOS 항목 목록(가벼운 호출 1번)으로 **최신 공표 시점**을 확인
2. DB에 이미 그 시점까지 있으면 받지 않고 기존 시계열·요약 문서(RAG)를 그대로 사용 → `status`에 "새 공표 없음"
3. 새 공표가 있으면 **마지막 저장 시점의 몇 시점 전부터만** 받음 (잠정치 수정 반영: 월 3·분기 4·연 2·일 7) → 해당 표의 요약 문서만 갱신
4. 최초 실행이거나 `history`를 늘린 경우에만 전체 기간 수집
5. 에이전트의 `bok_fetch_table`도 DB가 최신이면 API 대신 DB로 답함

실측(13개 작업): 전체 수집 약 90초 → 새 공표가 없을 때 약 20초(데이터 다운로드 0건). 주기(7일)가 안 된 작업은 `sync`가 호출 없이 건너뜀.
다른 ECOS 표를 정기 수집하려면 `sources.yaml > bok > tables`에 추가합니다 (`bok_table_items`로 분류 코드 확인).

## 6. 아직 사람이 확인해야 하는 것
- **KOTRA 해외시장뉴스**: 활용신청 후 상세페이지의 요청주소를 `sources.yaml > datagokr_rest`에 넣고 `enabled: true`
- **소비자상담 품목별 현황 / 표준답변**: data.go.kr에서 데이터셋 ID 확인 → `python -m bizrag discover <ID>`로 필드 확인 → `sources.yaml`에 ID 입력
- **국가데이터처 온라인 수집 가격 정보**: 자동 API 미확인 → CSV를 `inbox/online_price/`에 넣기

## 7. 구조
```
bizrag/
  store.py          SQLite 저장소 (문서·청크 색인 / 시계열 / 원자료 / 버전 / 캐시 / 실행 기록)
  textindex.py      한국어 2-gram 색인 (2글자 단어·조사 대응)
  app.py            설정 로드, 주기 판단 sync
  knowledge.py      에이전트 조회 도구 (MCP·CLI 공용)
  mcp_server.py     MCP 서버
  connectors/       naver · kosis · bok(한국은행) · law · kipris · worldbank · datagokr(파일데이터/REST) · inbox
config/sources.yaml 소스별 주기·감시 목록
tests/              모의 응답 테스트 (python -m unittest discover -s tests)
```
검색은 별도 키가 필요 없는 SQLite 전문검색입니다. 문서가 수만 건을 넘어 의미 검색이 필요해지면 `chunks` 테이블에
임베딩 열을 추가하는 방식으로 확장할 수 있습니다.

## 8. Pinecone Vector DB (pinecone.io) RAG 연동

`feature/B-rag-market`의 수집기가 모은 문서(법령 조문, 특허 초록, 한국은행/소비자원 요약 등)를
**Pinecone Serverless Vector DB**에 임베딩하여 시맨틱(의미 기반) 검색 및 하이브리드 검색을 수행할 수 있습니다.

### ① 키 및 환경변수 설정 (`.env`)
```bash
# Pinecone API 키 (https://app.pinecone.io)
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=bizrag-market
PINECONE_NAMESPACE=bizrag
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

# 임베딩 프로바이더 (openai 또는 gemini)
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=your_openai_api_key
```

### ② 의존성 설치
```bash
pip install -r requirements.txt
```

### ③ Pinecone 인덱스 생성 및 동기화
```bash
# 1. Pinecone Serverless 인덱스 확인/자동 생성
python -m bizrag pinecone-init

# 2. 수집기로 수집된 SQLite 문서를 Pinecone에 일괄 임베딩 & 업서트
python -m bizrag pinecone-sync

# 3. Pinecone 시맨틱 검색 테스트
python -m bizrag pinecone-search "헬스장 중도해지 위약금"

# 4. 하이브리드 검색 (BM25 + Pinecone RRF 앙상블)
python -m bizrag search "헬스장 계약해제" --mode hybrid
```

### ④ Python 코드 및 에이전트 연동 예시
```python
from bizrag.knowledge import Knowledge

k = Knowledge()

# 하이브리드 검색 (키워드 + 시맨틱)
docs = k.search_knowledge("온라인 쇼핑몰 환불 규정", mode="hybrid", limit=5)
for doc in docs:
    print(f"[{doc['source']}] {doc['title']} (score: {doc.get('hybrid_score')})")
    print(doc['text'])
```
