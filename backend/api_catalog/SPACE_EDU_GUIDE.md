# 창업공간·창업에듀 추가 — v1.3.0

기존 공고/사업소개/콘텐츠/통계에 centers, spaces, education을 추가했습니다. 실제 동영상이나 교재 원문은 다운로드하지 않습니다. 원문 JSON 전체, 조회용 텍스트, 서비스별 상세 컬럼과 출처를 전달합니다.

## 명세 근거

사용자가 제공한 endpoint/요청변수와 아래 공식 공공데이터포털 페이지의 내장 Swagger 응답 명세를 대조했습니다. 확인일 2026-10-08. api_specs/slp.swagger.json 및 edu.swagger.json에 확인한 공개 명세를 함께 보관했습니다.

- 창업공간: https://www.data.go.kr/data/15125365/openapi.do
- 창업에듀: https://www.data.go.kr/data/15125358/openapi.do

공간 응답의 spce_id/cntr_id/buld_id, 임대료 rent/보증금 guam/예약 구분 rsvt_psbl_clss와 주소/위경도를 저장합니다. 교육 응답에는 별도 강좌 ID가 명시되지 않아 lctr_pg_url을 식별키로 씁니다. 강좌 설명 lctr_istc, 키워드 kywrd, 대중소분류, 재생시간 play_time, 등록일 reg_dt/수정일 mdfcn_dt를 저장합니다. 분류 코드를 임의의 한국어 명칭으로 바꾸지 않습니다.

## 인증키와 활용신청

.env에 공통 DATA_GO_KR_SERVICE_KEY를 입력하거나 서비스별 키를 설정합니다.

```dotenv
DATA_GO_KR_SERVICE_KEY=
KISEDSLP_SERVICE_KEY=
KISEDEDU_SERVICE_KEY=
```

서비스별 키가 비어 있으면 공통 키를 사용합니다. 동일 키를 써도 공간/교육 각각의 활용신청이 필요합니다. 공간 요청은 serviceKey, 교육은 ServiceKey로 자동 전송하며 returnType=json을 명시합니다. 키가 없거나 권한이 없는 서비스가 있더라도 다른 서비스는 수집을 계속 시도합니다.

## 실행

프로젝트 폴더에서 실행합니다. 설치 명령은 REFERENCE_GUIDE.md를 참조하세요.

```powershell
# 기존 4개 + 신규 3개 = 전체 7개
python reference_catalog.py sync --dataset all

# 서비스별 실행
python reference_catalog.py sync --service kstartup
python reference_catalog.py sync --service space
python reference_catalog.py sync --service education

# 기능별 실행
python reference_catalog.py sync --dataset centers
python reference_catalog.py sync --dataset spaces
python reference_catalog.py sync --dataset education

# 필터 수집: 단일 dataset에만 사용 가능
python reference_catalog.py sync --dataset centers --filter "regin_clss::LIKE=세종"
python reference_catalog.py sync --dataset spaces --filter "addr::LIKE=세종" --filter "rent::LTE=500000"
python reference_catalog.py sync --dataset education --filter "lctr_nm::LIKE=사업계획"

# 사용 가능한 endpoint/필터 확인
python reference_catalog.py datasets
```

전체 수집은 공간/교육에 필터를 붙이지 않으며, 공고만 현재 모집 필터를 유지합니다. 필터 수집 결과를 전체 목록이라고 해석하면 안 됩니다. totalCount가 전체 DB 건수이고 matchCount가 필터에 맞는 건수일 수 있으므로 둘 다 있으면 matchCount를 순회 종료 기준으로 우선 사용합니다. 명세의 data.data 배열과 기존 data 배열을 모두 해석합니다. 서버가 필터를 실제로 적용하는지는 인증 실호출 후 확인해야 합니다. 예약가능여부 값의 의미 및 임대료/보증금의 통화·기간 단위는 제공 자료에서 확정하지 못해 원문 코드/값으로 전달합니다. 예약 여부를 Y/N으로 추측하거나 rent를 자동으로 월 임대료라고 표시하지 않습니다.

## 팀원용 자료

```powershell
python reference_catalog.py list --dataset spaces --query "세종"
python reference_catalog.py export --dataset spaces --format jsonl --output data\handoff\spaces.jsonl
python reference_catalog.py export --dataset education --format csv --output data\handoff\education.csv
python reference_catalog.py export --format chunks --output data\handoff\all_chunks.jsonl --current
```

새 데이터의 JSONL attributes에는 조회용 상세 컬럼이 있습니다. CSV attributes_json도 같은 값을 담습니다. 원문 raw의 모든 추가 필드는 그대로 보존합니다. source는 기존 kstartup에 더해 space/education으로 구분합니다. api_endpoint는 키가 없는 공개 endpoint 출처이고 detail_url/source_url은 기관 홈페이지 또는 강좌 링크입니다. 기관 홈페이지를 공간 레코드의 실제 상세 페이지라고 가정하면 안 됩니다.

## DB 관계

- reference_centers: 센터 ID+건물 ID, 지역/주소/위경도/공간 수.
- reference_spaces: 공간 ID, 센터 ID/건물 ID, 주소/위경도/임대료/보증금/예약 코드.
- reference_education: 강좌 URL, 대중소분류, 키워드, 재생시간.

기존 reference_records와 reference_versions를 공유하므로 7종 모두 동일한 변경 감지·원문 보존·내보내기를 사용합니다. 기존 DB를 그대로 열면 새 테이블이 자동 추가됩니다. 센터 ID만으로 건물을 합치지 않고 센터+건물 조합을 구분합니다. 공간 JSONL의 related_centers는 해당 센터·건물의 DB record ID를 연결합니다. 공간부터 수집했거나 해당 센터가 아직 DB에 없으면 빈 배열이고, 센터를 나중에 수집하면 내보낼 때 연결됩니다. 관계를 만들기 위해 센터 이름을 추측해 연결하지 않습니다.

강좌/센터/공간의 식별키가 없으면 잘못 합치는 대신 해당 수집을 실패로 기록하고 raw 페이지 응답은 남깁니다. 강좌 페이지 URL이 바뀌면 별도 강좌로 저장될 수 있습니다. 실시간 재고나 예약 가능 상태는 마지막 수집 시점 값이므로 최종 이용·예약 시 원문에서 확인하세요.

## 키 없이 확인

```powershell
python reference_catalog.py --database data\demo.sqlite3 import-json --dataset centers sample\centers.json
python reference_catalog.py --database data\demo.sqlite3 import-json --dataset spaces sample\spaces.json
python reference_catalog.py --database data\demo.sqlite3 import-json --dataset education sample\education.json
python reference_catalog.py --database data\demo.sqlite3 summary
```

sample은 공식 필드 구조에 맞춘 가상 데이터이며 실제 센터/강좌가 아닙니다. 공식 명세 확인 및 테스트 31개 통과. 인증키를 쓰는 실제 데이터 수집은 아직 검증하지 못했습니다.
