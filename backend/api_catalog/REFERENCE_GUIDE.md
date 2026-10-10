# 팀 참고자료 수집 — 창업진흥원 API 7종 (v1.3.0)

기존 K-Startup 4종에 창업공간 센터·공간 및 창업에듀 교육정보를 추가하여 총 7종 API를 수집합니다. 기업마당은 포함하지 않았습니다. 새 서비스는 [SPACE_EDU_GUIDE.md](SPACE_EDU_GUIDE.md)를 함께 읽어 주세요. 기존 API 공고 수집 명령과 첨부/양식 명령은 유지했습니다.

## 무엇을 수집하나

| dataset | 공식 기능 | 기본 수집 범위 |
| --- | --- | --- |
| announcements | getAnnouncementInformation01 | 현재 모집 중인 공고 |
| businesses | getBusinessInformation01 | API에서 조회되는 사업소개 전체 연도 |
| contents | getContentInformation01 | 공지/정책·규제/우수사례/이슈·동향 전체 |
| statistics | getStatisticalInformation01 | API에서 조회되는 통계보고서 정보 전체 |
| centers | getCenterList | 창업공간 센터 목록 전체 |
| spaces | getCenterSpaceList | 센터에 등록된 공간 전체 |
| education | getEducationInformation | 창업에듀 강좌 정보 전체 |

전체는 API가 실제 반환하는 레코드 범위입니다. 웹사이트 전체나 모든 첨부 원문을 뜻하지 않습니다. perPage 및 page로 빈 페이지 또는 totalCount까지 순회합니다. 안전 상한은 기능당 100페이지이며 상한에 닿으면 실패로 기록하고 이미 받은 자료는 보존합니다. --max-pages를 늘려 다시 실행할 수 있습니다. 최초 참고자료 수집은 여러 연도에 걸칠 수 있습니다. 공고는 과거 전체 수집을 피하는 기존 선택을 유지합니다.

## 설치·인증키·전체 실행

프로젝트 폴더에서 Python 3.10 이상을 사용합니다. 참고자료 수집에는 추가 Python 패키지가 필요 없습니다.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
Copy-Item .env.example .env
# 나중에 .env의 DATA_GO_KR_SERVICE_KEY에 본인의 키 입력

.\.venv\Scripts\python.exe reference_catalog.py datasets
.\.venv\Scripts\python.exe reference_catalog.py sync --dataset all
.\.venv\Scripts\python.exe reference_catalog.py summary
```

인증키는 요청에만 쓰고 코드·DB·로그에 기록하지 않습니다. 공개 파일 다운로드와 달리 실제 API sync에는 인증키와 해당 서비스 활용신청이 필요합니다. 이 제작 환경에서는 키가 없어 실제 인증 API 호출을 실행하지 않았습니다.

DB 기본값은 기존과 같은 data/api_catalog.sqlite3입니다. .env의 API_CATALOG_DB가 있으면 새 수집기도 그 경로를 사용합니다. 선택한 DB를 기존 첨부 명령과 공유할 때는 attachment_catalog.py --database 해당경로 명령 순서로 지정하세요.

```powershell
# 기능을 하나씩 재수집하거나 실패한 기능만 재실행
.\.venv\Scripts\python.exe reference_catalog.py sync --dataset businesses
.\.venv\Scripts\python.exe reference_catalog.py sync --dataset contents --max-pages 300
.\.venv\Scripts\python.exe reference_catalog.py sync --dataset statistics
```

공고 필터 요청은 기존 코드와 같은 cond[rcrt_prgs_yn::EQ]=Y가 기본입니다. 제공 설계서에는 일반 필드명도 설명되어 있으므로 인증 실응답에서 이를 요구한다면 --filter-style plain으로 실행합니다. 모집 여부·시작일·종료일은 클라이언트에서도 재확인합니다. 문서의 Rcrt_prgs_yn 대소문자 차이는 조회용 사본에서 정규화하고 원문 JSON은 수정하지 않습니다. API가 서버 필터를 무시하면 클라이언트 필터링은 가능하지만 호출량은 늘어납니다.

사업소개/콘텐츠/통계는 변경분 전용 API가 문서에 없으므로 목록을 다시 조회하고 레코드 해시로 새 자료와 변경을 구분합니다. API 본문이 바뀌지 않아도 last_seen_at은 갱신됩니다. 첨부 파일 내용이 바뀌었는지는 이 API 해시로 판단할 수 없습니다.

## 팀원에게 전달

```powershell
# 모든 API 원문과 조회용 컬럼. 한 줄에 자료 하나
.\.venv\Scripts\python.exe reference_catalog.py export --format jsonl --output data\handoff\references.jsonl --current

# Excel에서 열 수 있는 UTF-8 BOM CSV
.\.venv\Scripts\python.exe reference_catalog.py export --format csv --output data\handoff\references.csv --current

# 검색/RAG 파이프라인용 1000자 단위 텍스트 + 출처
.\.venv\Scripts\python.exe reference_catalog.py export --format chunks --output data\handoff\reference_chunks.jsonl --current

# 조회/키워드 검색
.\.venv\Scripts\python.exe reference_catalog.py list --dataset statistics --limit 20
.\.venv\Scripts\python.exe reference_catalog.py list --query "창업" --limit 50
```

--current는 DB에 남은 마감 공고를 내보낼 때 제외하고 나머지 세 종류의 참고자료는 그대로 포함합니다. 이전 공고도 보관한 DB에서 이 옵션을 생략하면 마감 공고가 포함될 수 있습니다. 조회는 title/body_text의 부분 문자열 검색입니다. 임베딩 생성·벡터 DB 적재·AI 요약은 하지 않습니다.

JSONL은 record ID, dataset, 제목, API 본문 텍스트, 분류, 원문 URL, 파일명, 날짜, 해시, 확인시간, raw 전체를 포함합니다. CSV의 raw_json도 원문 전체이며 Excel이 수식으로 해석할 수 있는 문자열은 표시용으로 접두 작은따옴표를 붙입니다. 정확한 원문은 JSONL/raw와 DB를 기준으로 사용하세요.

RAG chunks의 source_url과 record_id/content_hash는 원문 추적용입니다. 내용은 API가 제공한 제목·본문·관련 메타데이터만 포함합니다. 특히 콘텐츠 API는 문서상 본문 응답이 없어 제목·분류·등록일·파일명 수준이고, 통계보고서 ctnt도 보고서 전체 본문이라는 보장이 없습니다. coverage에 '첨부 원문 미포함'을 표시합니다. file_nm은 링크가 아니므로 파일명을 다운로드 URL로 변환하거나 링크를 추정하지 않습니다.

## DB 테이블과 관계

- reference_records: 7종 데이터를 source와 dataset으로 구분한 현재 레코드. 원문 전체와 조회용 컬럼을 함께 보존합니다.
- reference_versions: 내용 해시별 원문 버전. 동일 내용의 중복 버전 생성은 생략합니다.
- reference_sync_runs: 기능별 시작/종료 시간, 성공/실패, 페이지 수, 신규/변경/중복/제외 건수.
- reference_sync_pages: 실행별 API 페이지 응답 원문(JSON 구조로 저장). 오류 분석용입니다.
- api_announcements: 기존 공고 조회·첨부 수집용 테이블. 새 수집기는 정상적인 공고를 여기에 함께 반영합니다.

공고 날짜/필수 ID가 이상하면 reference_records에는 받은 공고를 보존하되 기존 공고 테이블 반영이 실패할 수 있습니다. sync 결과 projection_errors를 확인하세요. 날짜와 모집 여부로 모집 중임을 확인할 수 없는 공고는 기본 sync에서 제외됩니다.

식별키: 공고는 pbanc_sn, 콘텐츠/통계는 상세 URL, 사업소개는 연도+분류+사업명입니다. 공식 안정 ID가 없는 사업소개에서 이름이 바뀌면 별도 레코드가 될 수 있습니다. fallback identity도 기록하여 검토할 수 있습니다. 목록에서 사라진 자료를 자동 삭제하거나 폐기된 것으로 판단하지 않습니다. 따라서 참고자료 DB는 마지막으로 확인된 자료를 축적하며 현재 게시 여부를 보증하지 않습니다. changed_at은 수집기에서 변경을 관측한 시각이고 source_modified_at은 API가 제공한 수정시각입니다.

부분 수집 중 실패해도 이미 저장한 데이터를 보존합니다. 한 기능이 실패해도 all 명령은 다음 기능을 계속 시도합니다. API 오류나 같은 페이지 반복 반환을 '정상 빈 목록'으로 처리하지 않습니다. 종료 코드: 정상 0, 입력/명령 오류 1, 일부 기능 수집 실패 2. 일부 실패 시 해당 dataset을 재실행하세요. 재실행은 1페이지부터 시작하며 중복은 해시로 처리합니다.

raw 페이지 로그는 실행마다 누적되므로 운영 중 보관 기간에 맞춰 정리 정책을 추가하세요. 이번 버전은 원문을 자동 삭제하지 않습니다. DB SQLite 파일은 공유 폴더에서 여러 프로세스로 동시에 수정하지 말고 수집 담당자 한 명이 관리한 뒤 export 파일을 팀원에게 전달하는 구성이 권장됩니다.

## 하루 한 번 실행

```powershell
.\.venv\Scripts\python.exe reference_catalog.py sync --dataset all
.\.venv\Scripts\python.exe reference_catalog.py export --format jsonl --output data\handoff\references.jsonl --current
```

위 명령을 작업 스케줄러/cron에 등록할 수 있습니다. 실제 스케줄 등록은 하지 않았습니다. API 공고 수집은 새 sync all에 포함되므로 기존 api_catalog.py sync를 같은 작업에서 중복 실행할 필요가 없습니다. 첨부 수집은 별도 명령이며 이 전체 API 수집 명령으로 실행되지 않습니다. 호출 한도는 각 기능의 활용신청 화면과 계정 상태를 기준으로 확인하세요.

## 키 없이 동작 확인

sample의 4개 JSON은 설명용 가상 데이터입니다. 실제 API 데이터가 아닙니다.

```powershell
.\.venv\Scripts\python.exe reference_catalog.py --database data\demo.sqlite3 import-json --dataset announcements sample\announcements.json
.\.venv\Scripts\python.exe reference_catalog.py --database data\demo.sqlite3 import-json --dataset businesses sample\businesses.json
.\.venv\Scripts\python.exe reference_catalog.py --database data\demo.sqlite3 import-json --dataset contents sample\contents.json
.\.venv\Scripts\python.exe reference_catalog.py --database data\demo.sqlite3 import-json --dataset statistics sample\statistics.json
.\.venv\Scripts\python.exe reference_catalog.py --database data\demo.sqlite3 summary
```

## 다음 API 추가 지점

Dataset/DATASETS에 제공처별 URL·인증키 변수명·필드·허용 필터를 명시합니다. 새로운 서비스는 응답 규격, 식별키, 관계와 상세 테이블을 함께 추가합니다. 다른 서비스를 단순히 URL만 바꿔 넣으면 안 됩니다.

## 검증

기존 테스트 포함 31개 테스트 통과. 4종 원문 보존, 변경/원복, 기능별 분리, 페이지 순회, XML/JSON 응답, 오류 응답, 반복 페이지와 페이지 상한 실패, 현재 모집 필터와 기존 DB 연동, JSONL/CSV/RAG 출처를 확인했습니다. 인증키 입력 후 실제 응답 구조와 필터 방식은 첫 실행에서 확인해야 합니다. 검증 기록은 VALIDATION.md에 있습니다.
