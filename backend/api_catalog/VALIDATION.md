# 검증 기록 — v1.3.0

확인일: 2026-10-08 (한국 시간)

- 기존 테스트 포함 31개 테스트 통과.
- 7개 dataset 가상 샘플 CLI import 성공.
- JSONL/CSV/RAG chunks 각 7건 export 성공.
- 공간–센터 연결을 CLI export에서 확인.
- 공식 공간/교육 Swagger의 data.data 응답과 matchCount 종료 조건 테스트.
- 서비스별 endpoint/ServiceKey 대소문자/조건 필터 요청 생성 테스트.
- 기존 DB 다시 열기 및 신규 테이블/기존 레코드 보존 테스트.
- 임대료 0 값의 원문·상세 컬럼·RAG 텍스트 보존 확인.

공식 API 응답 명세는 api_specs에 보관했습니다. 실제 인증 API 호출은 키가 없어 수행하지 않았습니다. 샘플은 가상 자료입니다.

아래는 앞선 버전의 검증 기록입니다.

# 검증 기록 — v1.2.0

확인일: 2026-10-08 (한국 시간)

## 결과

- `python -m unittest discover -s tests -v`: 25개 테스트 통과.
- CLI `import-json`: announcements/businesses/contents/statistics 가상 샘플 각 1건 저장 성공.
- CLI `summary`: 4개 dataset 각 1건 조회 성공.
- CLI `export`: JSONL, CSV, chunks 각각 4건 내보내기 성공.
- CLI `list --query 창업`: 가상 샘플 3건 검색 성공.
- 기존 첨부/양식 및 API DB 테스트 통과.

## 확인한 실패 경로

API 오류를 정상 빈 목록으로 처리하지 않음, 반복 페이지 감지, 페이지 상한 도달 실패 표시, 일부 기능 실패 시 기존 자료 보존, JSON/XML 응답 구조, 현재 모집 필터, 원문 버전과 제목 변경 시 상세 URL 식별키 유지.

## 실제 환경 검증 범위

인증키가 제공되지 않아 이번 버전의 인증 API 실호출은 수행하지 않았습니다. 문서 명세와 가상 응답 기반 테스트입니다. 실제 첫 sync에서 response/data/items 구조 및 공고 필터 스타일을 확인해야 합니다.

앞선 v1.1.0에서는 공개 K-Startup 공고 179309의 첨부 5개 수집에 성공했습니다. 이는 공개 페이지/첨부 경로 테스트이며 4종 API 인증 호출의 검증과는 다릅니다. 원문 첨부파일은 코드 패키지에 포함하지 않았습니다.
