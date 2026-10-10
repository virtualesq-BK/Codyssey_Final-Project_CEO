# 공고별 지원양식 수집·DB 전달

## 범위

API 목록 수집은 기존 api_catalog.py를 그대로 사용합니다. 새 attachment_catalog.py는 K-Startup 상세 페이지의 실제 다운로드 링크를 따라 원본과 문서 구조를 저장합니다. 다른 기관의 상세 페이지용 어댑터는 아직 구현하지 않았습니다.

파일명은 식별자가 아닙니다. 공고 pbancSn + 첨부 다운로드 ID로 관계를 유지하고, 파일 바이트의 SHA-256으로 변경을 구분합니다. 제목은 역할 분류의 보조 정보입니다. 안내문·지원양식·매뉴얼이 정확히 세 파일로 구성된다고 가정하지 않고 첨부 전체를 수집합니다. 이미지 등도 원본은 보관하되 양식으로 처리하지 않습니다.

공고/양식 분류와 문항 후보 생성은 규칙 기반이며 AI를 호출하지 않습니다. 이름과 내용으로 판별하기 어려운 문서는 unknown으로 두고 사람이 역할과 문항을 확인합니다. 자동 문항 추출이 모든 양식의 의미를 해석하지는 않습니다.

## 설치와 인증키

Python 3.10 이상. 아래 명령은 프로젝트 폴더에서 실행합니다.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[documents]"
Copy-Item .env.example .env
```

API 인증키는 나중에 .env의 DATA_GO_KR_SERVICE_KEY에 넣으면 됩니다. 공개 상세 페이지를 지정한 첨부 수집은 이 키 없이 실행할 수 있습니다. HWP 텍스트 추출은 선택적으로 `pip install -e ".[hwp]"`가 필요하며 hwp5txt 실행파일이 PATH에 있어야 합니다. HWP 텍스트 추출만으로 표의 입력 위치나 페이지 배치가 확보되지는 않습니다. 구형 DOC 변환은 별도로 설치된 LibreOffice의 soffice 실행파일이 PATH에 있어야 합니다.

## 최초 수집과 하루 한 번 갱신

```powershell
.\.venv\Scripts\python.exe api_catalog.py sync
.\.venv\Scripts\python.exe api_catalog.py refresh-status
.\.venv\Scripts\python.exe attachment_catalog.py crawl-current --limit 20 --max-files 20
.\.venv\Scripts\python.exe attachment_catalog.py list
```

이 순서를 Windows 작업 스케줄러 또는 cron에 하루 한 번 등록합니다. 이 패키지는 스케줄을 실제 등록하지 않습니다. 작업 디렉터리를 프로젝트 폴더로 지정하고 프로젝트 가상환경의 Python을 사용해야 합니다. API 키가 없으면 sync는 실행할 수 없습니다.

현재 DB에서 모집중/마감임박이고 모집 시작일이 지난 공고를 선택합니다. 확인한 지 오래된 공고부터 처리하며 기본값은 실행당 20개입니다. 첫 수집 때 대상이 20개보다 많으면 limit을 늘리거나 여러 번 실행합니다. 과거 전체 이력을 수집하지 않습니다. 마감된 기존 원본은 보존하지만 crawl-current 대상으로는 선택하지 않습니다.

공고 본문 변경만 감지해서 첨부를 생략하면 동일 링크의 파일 교체를 놓칠 수 있으므로, 선택된 공고의 파일은 다시 다운로드한 뒤 해시를 비교합니다. 같은 파일은 문서 추출/버전 생성을 반복하지 않습니다. 다운로드 트래픽은 발생합니다. 신규·변경 양식의 문항 검토 결과는 버전마다 별도로 관리합니다.

DB 기본값은 data/api_catalog.sqlite3, 파일 저장 위치는 data/attachments입니다. 원본 파일은 DB BLOB 대신 디스크에 저장하고 DB는 경로·해시·관계·추출 JSON을 저장합니다. DB와 data/attachments를 함께 백업하고 전달해야 합니다. 원격 서비스에서는 경로를 오브젝트 스토리지 키로 바꾸는 확장이 필요합니다.

## 특정 공고 테스트

```powershell
.\.venv\Scripts\python.exe attachment_catalog.py crawl --url "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=179309"
.\.venv\Scripts\python.exe attachment_catalog.py export 179309 --output data\handoff\179309.json --include-pending
```

crawl은 명시적으로 지정한 공고를 처리하므로 마감된 예제도 수집합니다. crawl-current의 현재 모집 필터와 다릅니다. 예제 페이지는 확인 시 마감 공고 페이지로 이동했고, 이를 같은 공고 ID의 안전한 페이지 이동으로 처리했습니다.

2026-10-08 실제 확인: 첨부 5개 모두 수집 성공. 모집 공고문 HWPX와 PDF, 지원신청서 HWP, 포스터 JPG와 TXT입니다. 이 공고는 DOCX 양식을 제공하지 않았습니다. HWP 신청서는 이 실행 환경에서 needs_conversion이며 자동 입력 준비 완료가 아닙니다. 스캔 PDF의 OCR, 압축 첨부 내 양식 검색, 외부 기관 사이트, 로그인 파일은 구현하지 않았습니다. 구조 변경/접근 제한은 오류로 기록하여 재확인할 수 있게 합니다.

## DB와 출력 담당자 전달 규격

| 테이블 | 저장 대상 |
| --- | --- |
| api_announcements | 기존 API 원문과 모집 정보 |
| source_pages | 공고 ID, 상세 URL, HTML 스냅샷, 확인 시간, 수집 상태 |
| attachments | 공고별 첨부 ID, 다운로드 링크, 표시명, 역할 수정, 현재 버전, 변환 원본 관계 |
| attachment_versions | 원본 경로·해시·형식, 추출 블록, XML 위치, 경고, 파서 버전 |
| form_templates | 문항/작성 안내/분량 제한 후보, 검토자, 문항 검토와 입력 위치 검증 상태 |

DOCX/HWPX는 문단·표 셀과 빈 셀을 포함한 블록을 추출합니다. 블록의 location에 XML 파일명과 XPath, 가능한 표 위치 정보를 남깁니다. 원본 자체는 변경하지 않으므로 수집 단계에서 원본 서식을 잃지 않습니다. 병합 셀, 도형, 중첩 표 등 복잡한 구성은 경고와 원본을 함께 검토해야 합니다. DOC는 DOCX로 변환한 사본을 제공하며 원본과의 서식 비교가 필요합니다. PDF는 참고용 페이지 텍스트를 추출하며 Word 입력 위치로 취급하지 않습니다.

문항 후보의 label, guidance, max_chars, max_pages, count_spaces, evidence를 확인합니다. 원문에 없는 제한은 추정하지 않고 null로 둡니다. answer_block_ids는 문항 제목이 아니라 실제 답변을 넣을 블록 ID 목록이어야 합니다. 자동 후보에서는 이 값을 비워 둡니다.

```powershell
# 필요 시 첨부 역할 수정: notice/form/manual/other/unknown
.\.venv\Scripts\python.exe attachment_catalog.py role ATTACHMENT_ID form

# HWP를 별도 도구로 DOCX/HWPX로 변환한 후 사본 등록 (원본은 보존)
.\.venv\Scripts\python.exe attachment_catalog.py register-converted ATTACHMENT_ID "converted\지원신청서.docx"

# 후보 블록/문항 확인
.\.venv\Scripts\python.exe attachment_catalog.py export 179309 --output data\handoff\candidates.json --include-pending

# 원본과 비교해 작성한 검토 JSON 승인
.\.venv\Scripts\python.exe attachment_catalog.py review TEMPLATE_ID reviewed-fields.json --reviewer "검토자 이름"

# 검토된 문항을 출력 담당자에게 전달
.\.venv\Scripts\python.exe attachment_catalog.py export 179309 --output data\handoff\179309.json
```

reviewed-fields.json은 다음 구조로 작성하되 실제 export의 블록 ID와 정확한 원문을 사용합니다. 아래는 구조 예시입니다.

```json
{
  "mapping_validated": true,
  "fields": [
    {
      "label": "1. 사업 아이디어를 설명하세요.",
      "guidance": null,
      "max_chars": null,
      "max_pages": null,
      "count_spaces": null,
      "evidence": [{"block_id": "b00001", "quote": "1. 사업 아이디어를 설명하세요."}],
      "answer_block_ids": ["b00002"]
    }
  ]
}
```

문항 근거/분량 제한/블록 ID를 검증하며, XML 입력 위치가 없는 파일은 mapping_validated로 승인할 수 없습니다. 검토자는 실제 해당 셀이 답변 위치인지 확인해야 합니다. 이후 export에서 form 역할 + 승인된 문항 + 검증된 입력 위치가 있을 때만 ready_for_generation=true입니다. 이는 데이터 전달 준비 상태이며 최종 페이지 배치를 보장한다는 의미가 아닙니다.

출력 담당자는 working_template_path 사본을 열어 승인된 fields의 answer_block_ids 위치에 답변을 넣고 최종 렌더링을 확인합니다. 데이터 수집 담당자의 범위는 원본·문항·작성 제한·입력 위치와 근거 제공까지입니다. 답변 생성, 문서에 삽입, 페이지 넘침/서식 보정과 최종 출력은 이 코드에 포함하지 않았습니다.

## 검증

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

기존 API 테스트를 포함한 13개 테스트 통과. 이름 변경, 다운로드 링크 연결, 해시 버전/원복, 빈 셀 위치, 실패 시 이전 원본 보존, HTML 오류 응답, 문항 검토와 위치 검증, HWP 미준비 상태를 확인했습니다. 인증키 기반 API 실제 호출과 실제 HWP의 DOCX 변환·완성본 생성은 검증 범위 밖입니다.
