# bizrag — 사업 아이디어 평가 에이전트용 RAG 수집기

무료 공공·민간 API를 **소스별 주기(월·주·일·검색 시)** 에 맞춰 수집해 하나의 지식 DB(`data/knowledge.db`)에 쌓고,
**Pinecone Serverless Vector DB**와 연동하여 에이전트(Claude 등)가 **MCP 도구**로 시맨틱 및 하이브리드 검색을 수행할 수 있게 하는 시장/사업성 검토 RAG 엔진입니다.

```
[주기 수집 sync]  ──┐
  월: KOSIS·한국은행·법령·World Bank·네이버 쇼핑분야·소비자 피해구제
  주: 생필품 가격·뉴스심리지수 ├──▶  knowledge.db (SQLite)  ◀── 에이전트 (MCP 도구)
  일: inbox CSV       │      ├ 문서(RAG): 통계표 요약·법령 조문·특허 초록·소비자 불만
[검색 시 수집]  ─────┘      │          └─▶ Pinecone Vector DB (12,199개 벡터)
  네이버 트렌드·쇼핑키워드      ├ 시계열 (18.1만건): 네이버 지수·KOSIS·한국은행·World Bank
  KIPRIS·법령·KOSIS 표       └ 원자료 (64.3만건): 생필품 가격표·피해구제·해외진출기업
```

---

## 1. 할 일은 3단계

### ① 키 발급 (무료, 필요한 것만)

| 소스 | 발급처 | 비고 |
|---|---|---|
| 네이버 | [NCP 콘솔 > NAVER API HUB](https://console.ncloud.com) | 2026년 개발자센터에서 **NAVER API HUB(네이버 클라우드)로 이관**됨. API HUB 이용 신청 → 앱 등록 → **검색어 트렌드·쇼핑인사이트** 추가 → 앱의 Client ID/Secret을 `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET`에 입력 (계정 IAM 키 아님). |
| KOSIS | [kosis.kr/openapi](https://kosis.kr/openapi/) | 회원가입 → 활용신청 → 즉시 발급 (`KOSIS_API_KEY`) |
| 한국은행 | [ecos.bok.or.kr/api](https://ecos.bok.or.kr/api/) | 회원가입 → 인증키 신청 → 즉시 발급 (`BOK_API_KEY`) |
| 법령 | [open.law.go.kr](https://open.law.go.kr) | OPEN API 신청. `LAW_OC`=가입 이메일 @ 앞부분. 신청서에 **이 PC의 공인 IP** 등록 필요 |
| KIPRIS Plus | [plus.kipris.or.kr](https://plus.kipris.or.kr) | 특허·실용 공개/등록공보 상품 무료 이용신청 (`KIPRIS_API_KEY`) |
| 공공데이터포털 | [data.go.kr](https://www.data.go.kr) | 마이페이지의 일반 인증키(Decoding). 그리고 아래 데이터셋마다 **[활용신청]** 클릭 |
| World Bank | — | 키 불필요 (Public Open API) |

공공데이터포털에서 활용신청할 데이터셋(주소의 숫자가 ID):
- `3040720` 한국소비자원 소비자 피해구제 정보 (분기별, 자동변환 API 확인됨)
- `15083256` 한국소비자원 생필품 및 서비스 가격 정보
- `15034787` KOTRA 해외진출기업

### ② 설치 + 키 점검
- **Windows**: `setup_and_check.bat` 더블클릭 → 메모장에 키 입력·저장 → 점검 결과 확인
- **Mac/Linux**: `bash setup_and_check.sh` (첫 실행 후 `.env` 편집, 다시 실행)

```
✅ 네이버 검색어트렌드·쇼핑인사이트  검색어트렌드 OK, 쇼핑인사이트 OK
✅ KOSIS 국가통계포털             통계표 검색 OK
✅ 한국은행 ECOS                  인증키 OK
✅ 공공데이터포털                 파일데이터 자동변환 API OK
```

### ③ 수집·조회 확인
```bash
python -m bizrag sync                 # 최초 수집 (주기가 된 것만 실행)
python -m bizrag try 텀블러            # 검색 시 수집 시험 (네이버·KOSIS·법령·특허)
python -m bizrag search "헬스장 계약해제"  # 쌓인 문서 검색 (기본 하이브리드)
python -m bizrag status               # 소스별 마지막 수집·다음 예정·DB 현황
```

---

## 2. 수집 데이터셋 및 사업보고서(TAM-SAM-SOM) 활용 목록 📊

bizrag 시스템은 사업보고서·사업계획서 검토, 시장 타당성 분석, 그리고 **TAM-SAM-SOM** 시장 규모 및 기대 매출 산출을 위해 총 7대 데이터 제공처로부터 데이터를 정기/온디맨드로 수집하여 로컬 지식 DB(`knowledge.db`) 및 **Pinecone Vector DB**에 적재합니다.

> [!NOTE]
> **현재 DB 적재 현황 (2026년 10월 최신 동기화 기준)**
> - **범용 RAG (bizrag 네임스페이스)**: 청크 **12,199개**, Pinecone `bizrag-market` 인덱스 업서트 완료
> - **펫테크 TAM/SAM/SOM RAG (pettech 네임스페이스)**: 청크 **13,929개**, Pinecone `bizrag-market` 업서트·검증 완료
>   - KOSIS 반려동물양육현황조사 2025 (25개 통계표, 4,858 관측값)
>   - ECOS 반려동물용품·관리비 소비자물가지수 (2020~2026.09, 348 관측값)
>   - NAVER 검색어트렌드·쇼핑인사이트 36개월 (9,350 관측값)
>   - WorldBank 글로벌 경제지표 8개 × 10개국 (1,187 관측값, TAM 추정용)
>   - KIPRIS 펫테크 특허 검색 10개 키워드
>   - TAM/SAM/SOM 종합 분석 문서 4건 (TAM·SAM·SOM·방법론)
> - **시계열 관측치 (`observations`)**: 총 **181,341건** (한국은행 11.6만건, KOSIS 5.6만건 등)
> - **원본 레코드 (`records`)**: 총 **643,023건** (생필품 가격, 소비자 피해구제 원자료 등)

---

### ① 통계청 국가데이터처 (KOSIS) 📊
- **발급/신청처**: [kosis.kr/openapi](https://kosis.kr/openapi/) (`KOSIS_API_KEY`)
- **특징**: 대한민국 전수 통계로, 전체 시장 규모(TAM)와 점포당 매출(SOM) 산출의 절대적 공신력 기준.
- **RAG 문서화 엔진 (`_write_table_docs`)**: 수집된 통계표를 업종별·분류별 요약 문서로 자동 변환하고, 매출액/사업체수 기반 점포(가맹점)당 평균 연매출액을 자동 산출하여 저장.

| 통계표 ID | 통계표 명칭 | 사업보고서/기획서 활용 목적 | 세부 수집 항목 및 지표 | 수집 규모 |
| :--- | :--- | :--- | :--- | :---: |
| **`DT_2KI2001`**<br>(경제총조사) | 산업세세분류별 총괄 | **[TAM 전체 시장 규모]**<br>사업계획서의 국내 시장 규모(조 원) 공식 입증 근거 | 한국표준산업분류(KSIC 5자리) 전 세부 업종별:<br>• 전국 연간 총매출액(백만원)<br>• 총 사업체수 (경쟁사 총수)<br>• 총 종사자수 (남/여) 및 인건비/비용구조 | **32,064건** |
| **`DT_FR0001N`**<br>(프랜차이즈통계) | 프랜차이즈 통계 (가맹점) | **[SOM 점포당 기대매출]**<br>1개 점포/매장당 현실적으로 기대 가능한 연매출 산출 | 편의점, 커피, 치킨, 제과, 한식, 미용 등 15대 업종별:<br>• 가맹점수, 종사자수, 연간 총매출액<br>• **[자동산출치] 가맹점당 연평균 매출액(억/만원)**<br>• 영업비용, 매출원가, 인건비, 임차료 | **5,472건** |
| **`DT_FR0007`**<br>(프랜차이즈통계) | 주요 업종별 가입비용 현황 | **[CAPEX / 초기 창업비용]**<br>오프라인 창업 시 표준 개설비용 및 투자금 검토 | 업종별 평균 초기 투자비용:<br>• 가맹비, 교육비, 보증금, 인테리어비 등 | **136건** |
| **`DT_1KE10071`**<br>(온라인쇼핑동향) | 온라인쇼핑몰 판매매체별/상품군별거래액 | **[이커머스/플랫폼 성장률]**<br>온라인 시장 연평균 성장률(CAGR) 및 모바일 침투율 검증 | 23개 품목별(음식서비스, e쿠폰, 식품, 화장품, 가전 등):<br>• 월별 총 거래액 (백만원)<br>• 모바일 쇼핑 거래액 vs PC 거래액 비중 추이 | **936건** |
| **`DT_1K52F01`**<br>(전국사업체조사) | 산업별 사업체수 및 종사자수 | **[SAM 유효 시장 & 경쟁사 수]**<br>특정 산업 내 실제 경쟁 공급자 수 파악 | 전국 세부 산업분류별:<br>• 총 사업체수 (경쟁 강도)<br>• 총 종사자수 및 대표자 성별 분포 | **15,942건** |
| **`DT_1K41013`**<br>(소매판매액) | 소매업태별 판매액지수 | **[유통 채널 전략 검토]**<br>어느 유통 채널이 성장하고 쇠퇴하는지 검증 | 백화점, 대형마트, 편의점, 슈퍼마켓, 무점포소매(온라인/홈쇼핑) 판매액지수 및 불변지수 | **552건** |
| **`DT_1J22001`**<br>(소비자물가지수) | 지출목적별 소비자물가지수 | **[원가/물가 리스크 점검]**<br>해당 품목의 원자재 및 소비자 가격 인상 추이 | 외식, 식료품, 주거, 교통 등 458개 세부 품목별 소비자물가지수 및 전년동월대비 등락률 | **6,972건** |

---

### ② 한국은행 경제통계시스템 (BOK ECOS) 🏛️
- **발급/신청처**: [ecos.bok.or.kr/api](https://ecos.bok.or.kr/api/) (`BOK_API_KEY`)
- **특징**: 국내 최고 공신력의 금융·기업 재무·거시경제 데이터. 새 공표 발생 시 자동 증분 갱신 및 RAG 요약 문서 생성.

| 통계표 코드 | 통계표 명칭 | 사업보고서/기획서 활용 목적 | 세부 수집 항목 및 지표 | 수집 주기 |
| :--- | :--- | :--- | :--- | :---: |
| **`501Y005`** (성장성)<br>**`501Y006`** (손익) | 기업경영분석 (연간 전수) | **[수익성 & 마진 벤치마크]**<br>해당 업종의 평균 마진율과 성장성 표준 벤치마크 | 비금융 영리법인 전수 기준 업종×기업규모별(대/중견/중소/소기업):<br>• 매출액증가율(%), 매출액영업이익률(%), 세전순이익률<br>• 원가율, 인건비비중, 손익분기점률, 이자보상비율 | 매년 (A)<br>(최근 8개년) |
| **`502Y001`** (성장성)<br>**`502Y002`** (손익) | 기업경영분석 (분기 외감) | **[최신 분기 수익성 추이]**<br>외부감사 대상 중대형 기업들의 최근 수익성 변동 | 외감기업 기준 업종별 분기 매출액증가율, 영업이익률, 부채비율 | 매분기 (Q)<br>(최근 20분기) |
| **`512Y007`** (실적)<br>**`512Y008`** (전망) | 업종별 기업경기조사 (BSI) | **[업계 체감 경기 검증]**<br>동일 업종 대표들이 체감하는 실질 업황 및 매출 전망 | 전자, 도소매, 숙박, 음식점, 정보통신 등 46개 세부 업종별:<br>• 업황 BSI, 매출 BSI, 채산성 BSI, 자금사정 BSI (100 기준) | 매월 (M)<br>(최근 36개월) |
| **`512Y013`** (실적)<br>**`512Y014`** (전망) | 기업경기조사 (BSI 총괄) | **[거시 산업 경기 동향]**<br>제조업/비제조업 전반의 경기 체감 흐름 | 전산업, 제조업, 비제조업, 대기업/중소기업별 BSI 지수 | 매월 (M)<br>(최근 60개월) |
| **`511Y002`** | 소비자동향조사 (CSI) | **[타겟 고객 지출 의향 검증]**<br>소비자들이 향후 돈을 더 쓸 것인지 검증 | • 지출항목별: 내구재, 의류, 외식, 여행, 교육, 의료, 주거비 전망<br>• 인구통계별: 40세 미만, 40~50대, 60대 이상, 소득구간별 세분화 | 매월 (M)<br>(최근 60개월) |
| **`200Y142`** (명목)<br>**`200Y143`** (실질) | 가계 목적별 최종소비지출 | **[TAM 가계 총 소비 지출액]**<br>전국 가계가 해당 카테고리에 쓰는 총 금액(조 원) | 국민계정 원계열 명목/실질 17대 품목별(음식료, 의류, 주거, 음식/숙박 등) 분기별 총 지출액(십억원) | 매분기 (Q)<br>(최근 24분기) |
| **`523Y001`** | 뉴스심리지수 (NSI) | **[거시 경제 분위기 & 여론]**<br>경제 전반의 긍정/부정 분위기 감지 | 일간 경제 기사 텍스트 감성을 계량화한 지수 (주간 평균 자동 산출) | 매주 (D→W)<br>(최근 800일) |

---

### ③ 공공데이터포털 (data.go.kr) & 한국소비자원 / KOTRA 🏛️
- **발급/신청처**: [data.go.kr](https://www.data.go.kr) (`DATAGOKR_API_KEY`)
- **특징**: 정부 파일데이터 자동변환 API를 통해 최신 공표 버전을 자동 추적 적재.

| 데이터셋 ID | 데이터셋 명칭 | 사업보고서/기획서 활용 목적 | 세부 수집 항목 및 집계 내용 | 수집 주기 |
| :--- | :--- | :--- | :--- | :---: |
| **`3040720`** | 한국소비자원 소비자 피해구제 정보 | **[시장 페인포인트 & 규제 리스크]**<br>기존 경쟁 제품/서비스에 대한 소비자 불만 분석 | 품목별(헬스장, 택배, 항공권, 통신 등) 접수 분기별 집계:<br>• 계약불이행, 청약철회 거부, 품질/AS 불만, 가격 요금 등 청구이유 비율<br>• 피해구제 처리결과(환급, 배상, 조정) 및 품목별 불만 요약 문서 | 분기 (월 점검)<br>(최근 4분기) |
| **`15083256`** | 한국소비자원 생필품 및 서비스 가격 정보 | **[원가 및 소비자가격 벤치마크]**<br>오프라인 유통 채널별 실제 판매 가격 조사 | 전국 대형마트, 백화점, 편의점, SSM별 가공식품·생필품 실시간 판매가격 원자료 (64만 건) | 매주 (W)<br>(최근 3회분) |
| **`15034787`** | KOTRA 해외진출기업 | **[글로벌 확장성 & 해외 진출 레퍼런스]**<br>해당 산업의 해외 진출 국가 및 기업 현황 파악 | 업종중분류×진출국가(미국, 베트남, 중국, 인도 등)별 해외 진출 한국 기업 명부 및 진출 형태 | 매월 (M)<br>(최근 1회분) |

---

### ④ 네이버 API HUB (NAVER DataLab & Shopping) 🛍️
- **발급/신청처**: [console.ncloud.com](https://console.ncloud.com) (`NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`)
- **특징**: 공급자 통계가 아닌 소비자의 실제 검색·구매 클릭 행동(Real Demand) 검증. 실시간 온디맨드 질의는 캐시(7일)로 보관.

| 엔드포인트 / 기능 | 데이터 명칭 | 사업보고서/기획서 활용 목적 | 세부 수집 항목 | 수집 주기 |
| :--- | :--- | :--- | :--- | :---: |
| **`datalab/shopping/categories`** | 쇼핑인사이트 분야별 트렌드 | **[소비자 구매 의도(Purchase Intent)]**<br>단순 조회가 아닌 실제 네이버 쇼핑 구매 클릭 선호도 | 패션의류, 화장품, 식품, 생활/건강, 디지털/가전 등 1분류 10대 카테고리별 클릭 추이 및 고객 성별/연령대 비중 | 매월 정기<br>(최근 36개월) |
| **`datalab/search`** | 검색어 트렌드 | **[아이디어 수요 검증 & 계절성]**<br>대중의 관심 추이, 성수기/비수기, 모바일 검색 비중 | 최대 5개 키워드 그룹 간 상대 검색량 비율(0~100), PC vs 모바일 비중, 성별/연령대별 비중 | 온디맨드 검색<br>(캐시 7일) |
| **`datalab/shopping/category/keywords`** | 쇼핑 키워드 트렌드 | **[경쟁 상품/브랜드 선호도]**<br>카테고리 내 경쟁 키워드 간 구매 클릭 비교 | 특정 세부 카테고리 내 핵심 키워드별 상대 클릭 지수 | 온디맨드 검색<br>(캐시 7일) |

---

### ⑤ 국가법령정보센터 (법제처) ⚖️
- **발급/신청처**: [open.law.go.kr](https://open.law.go.kr) (`LAW_OC`=가입 이메일 앞자리)
- **특징**: 사업 추진 시 직면하는 법적 규제, 인허가 요건, 소비자 보호 규정 전문을 조문 단위로 색인.

| 감시 법령 | 법령 분류 | 사업보고서 검토 시 활용 목적 |
| :--- | :--- | :--- |
| **소비자기본법** | 소비자 보호 | 사업자의 책무, 피해보상 기준, 소비자 분쟁조정 절차 검토 |
| **전자상거래 등에서의 소비자보호에 관한 법률** | 이커머스/플랫폼 | 통신판매업자 신고, 청약철회(7일), 반품/환불 의무 규정 |
| **표시·광고의 공정화에 관한 법률** | 마케팅/홍보 | 허위·과장 광고, 기만적 표시 방지 가이드라인 |
| **개인정보 보호법** | 데이터/IT | 회원가입, 개인정보 수집·이용 동의, 제3자 제공, 파기 의무 |
| **제조물 책임법** | 하드웨어/제조 | 제품 결함으로 인한 손해배상 책임 및 면책 요건 |
| **식품위생법** | 식품/F&B | 영업 허가·신고 요건, 위생 관리 기준, 표시 의무 |
| **화장품법** | 뷰티/바이오 | 제조업·책임판매업 등록, 원료 기준, 기능성 화장품 심사 |
| **의료기기법** | 헬스케어 | 의료기기 등급 분류, 제조·수입·판매업 허가 규정 |
| **중소기업창업 지원법** | 창업/투자 | 창업기업 범위, 세제 혜택, 벤처 확인 및 정부 지원 자격 |

---

### ⑥ 특허청 KIPRIS Plus 💡
- **발급/신청처**: [plus.kipris.or.kr](https://plus.kipris.or.kr) (`KIPRIS_API_KEY`)
- **특징**: 아이디어 검색 시 실시간 특허·실용신안 공개/등록공보 초록을 검색하여 선행기술 및 주요 출원인 동향 분석 (캐시 30일).

---

### ⑦ World Bank (세계은행) 🌐
- **발급/신청처**: 별도 키 불필요 (Public Open API)
- **수집 대상**: 10개국(한국, 미국, 일본, 중국, 베트남, 인도네시아, 태국, 독일, 영국, 인도) × 최근 15개년
- **수집 지표**: 총인구, 명목 GDP, 1인당 GDP, 가계최종소비지출, 인터넷 이용률, 도시화율, 고령인구 비중, 소비자물가상승률 (글로벌 TAM 및 국가별 거시 지표 비교)

---

## 3. 매일 자동 수집 걸어두기
`sync`는 각 작업의 마지막 성공 시각을 보고 주기가 된 것만 호출하므로, **하루 1번만** 예약하면 됩니다.
- Windows 작업 스케줄러: 기본 작업 만들기 → 매일 → 프로그램 `daily_sync.bat` (로그: `logs/sync.log`)
- Mac/Linux crontab: `30 6 * * * cd /경로/bizrag && .venv/bin/python -m bizrag sync >> logs/sync.log 2>&1`

실패한 작업은 성공으로 기록되지 않아 다음날 자동 재시도됩니다.

---

## 4. 에이전트에 연결 (Claude Desktop / MCP 클라이언트 예시)
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

---

## 5. 데이터 해석 원칙
- 네이버 지수는 **조회 조건 안의 상대값**. `query_sig`가 같은 값끼리만 비교. 검색 관심도 ≠ 구매 의사
- 특허 검색은 유사 기술 후보일 뿐, 침해·독점 판단 근거 아님
- 법령은 원문 그대로 저장(해석은 별도). 시행일자 메타데이터 확인
- 피해구제 건수 증가는 판매량 증가 영향일 수 있음
- 한국은행 CSI·BSI·뉴스심리지수는 100 기준 심리지표(실제 매출·소비액 아님). 뉴스심리지수 주간 값은 수집기가 일간 값을 평균한 것
- 기업경영분석은 업종 **평균**(분기는 외감기업, 연간은 전수 법인) — 소상공인·개인사업자 수익성과 다를 수 있음
- 가계 목적별 소비지출(원계열)은 계절성이 커서 직전 분기보다 **전년동기 대비**로 볼 것

---

## 6. 디렉토리 구조
```
bizrag/
  store.py          SQLite 저장소 (문서·청크 색인 / 시계열 / 원자료 / 버전 / 캐시 / 실행 기록)
  textindex.py      한국어 2-gram 색인 (2글자 단어·조사 대응 BM25)
  embeddings.py     다중 임베딩 프로바이더 (FastEmbed 로컬 다국어 모델, OpenAI, Gemini 지원)
  pinecone_store.py Pinecone Serverless Vector DB 연동 및 시맨틱 검색 엔진
  app.py            설정 로드, 주기 판단 sync
  knowledge.py      에이전트 조회 도구 및 RRF 하이브리드 검색 엔진 (MCP·CLI 공용)
  mcp_server.py     MCP 서버
  connectors/       naver · kosis · bok(한국은행) · law · kipris · worldbank · datagokr · inbox
config/sources.yaml 소스별 주기·감시 목록 및 7대 핵심 통계표 설정
tests/              모의 응답 및 Pinecone 연동 테스트 (Pass 25/25)
```

---

## 7. Pinecone Vector DB (pinecone.io) RAG 연동

`feature/B-rag-market`의 수집기가 모은 문서(법령 조문, 특허 초록, 한국은행/KOSIS 통계 요약, 소비자원 불만 등)를
**Pinecone Serverless Vector DB**에 임베딩하여 시맨틱(의미 기반) 검색 및 하이브리드 검색을 수행합니다.

### ① 키 및 환경변수 설정 (`.env`)
```bash
# Pinecone API 키 (https://app.pinecone.io)
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=bizrag-market
PINECONE_NAMESPACE=bizrag
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

# 임베딩 프로바이더 (FastEmbed 로컬 모델 기본 적용: 무료, 무제한, CPU 고속 ONNX)
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

### ② Pinecone 인덱스 생성 및 동기화
```bash
# 1. Pinecone Serverless 인덱스 확인/자동 생성 (384차원 Cosine)
python -m bizrag pinecone-init

# 2. 수집기로 수집된 SQLite 문서를 Pinecone에 일괄 임베딩 & 업서트 (12,199개 완료)
python -m bizrag pinecone-sync

# 3. Pinecone 시맨틱 검색 테스트
python -m bizrag pinecone-search "프랜차이즈 가맹점당 평균 매출"

# 4. 하이브리드 검색 (BM25 + Pinecone Vector RRF k=60 앙상블)
python -m bizrag search "온라인쇼핑 음식서비스 거래액" --mode hybrid
```

### ③ Python 코드 및 에이전트 연동 예시
```python
from bizrag.knowledge import Knowledge

k = Knowledge()

# 하이브리드 검색 (키워드 + 시맨틱 RRF)
docs = k.search_knowledge("온라인 쇼핑몰 환불 규정", mode="hybrid", limit=5)
for doc in docs:
    print(f"[{doc['source']}] {doc['title']} (score: {doc.get('hybrid_score')})")
    print(doc['text'])
```

---

## 8. 펫테크 전용 TAM/SAM/SOM 수집 파이프라인

펫테크 시장 크기(TAM·SAM·SOM) 산출을 위한 독립 수집 파이프라인입니다.
별도 Pinecone 네임스페이스(`pettech`)와 SQLite 코퍼스(`data/pettech/rag_corpus/knowledge.db`)를 사용하여
범용 RAG 데이터와 격리됩니다.

### ① 데이터 소스

| 소스 | 항목 | 용도 |
|---|---|---|
| **KOSIS** (반려동물양육현황조사) | 25개 통계표, 4,858 관측값 | 국내 SAM/SOM 근거 |
| **ECOS** (한국은행) | 반려동물용품·관리비 CPI 2020~2026.09, 348 관측값 | 국내 물가·지출 추세 |
| **NAVER** 검색·쇼핑인사이트 | 36개월 시계열, 9,350 관측값 | 소비자 관심·수요 |
| **WorldBank Open API** | 8개 글로벌 경제지표 × 10개국, 1,187 관측값 | 글로벌 TAM 추정 |
| **KIPRIS Plus** | 펫테크 특허 10개 키워드 검색 | 기술 경쟁 강도 |
| **종합 분석 문서** | TAM·SAM·SOM·방법론 4건 | 에이전트 추론 근거 |

### ② WorldBank 수집 지표 및 대상 국가

```python
# 8개 경제지표
WB_INDICATORS = {
    "SP.POP.TOTL":       "인구 (명)",
    "NY.GDP.MKTP.CD":    "GDP (현재 US$)",
    "NY.GDP.PCAP.CD":    "1인당 GDP (현재 US$)",
    "NE.CON.PRVT.CD":    "가계 최종소비지출 (현재 US$)",
    "IT.NET.USER.ZS":    "인터넷 이용률 (%)",
    "SP.URB.TOTL.IN.ZS": "도시화율 (%)",
    "SP.POP.65UP.TO.ZS": "65세 이상 인구 비율 (%)",
    "FP.CPI.TOTL.ZG":    "소비자물가상승률 (%)",
}

# 10개국 (한국·미국·일본·중국·독일·영국·호주·프랑스·베트남·브라질)
WB_COUNTRIES = ["KOR","USA","JPN","CHN","DEU","GBR","AUS","FRA","VNM","BRA"]
```

### ③ KIPRIS 특허 검색 키워드

| 키워드 | 분류 태그 |
|---|---|
| 반려동물 IoT | 반려동물IoT |
| 펫캠 CCTV | 펫캠 |
| 자동급식기 | 자동급식기 |
| 반려동물 웨어러블 | 웨어러블 |
| 반려동물 헬스케어 | 헬스케어 |
| 펫시터 앱 | 펫시터 |
| 반려동물 행동분석 | 행동분석 |
| 스마트 사료 | 스마트사료 |
| 반려동물 원격 | 원격돌봄 |
| 펫 구독 서비스 | 구독서비스 |

### ④ TAM 추정 방법론

WorldBank 가계 최종소비지출(`NE.CON.PRVT.CD`) × 국가별 반려동물 지출 비율로 산출:

| 국가 | 반려동물 지출 비율 |
|---|---|
| 한국 (KOR) | 0.8% |
| 미국 (USA), 호주 (AUS) | 1.5% |
| 독일 (DEU), 영국 (GBR) | 1.2% |
| 기타 선진국 | 1.0% |
| 신흥국 (VNM, BRA, CHN) | 0.5% |

### ⑤ 실행 방법

```bash
# 1. 환경변수 설정 (new.env)
#    KIPRIS_API_KEY, PINECONE_API_KEY, EMBEDDING_MODEL 등 확인

# 2. TAM/SAM/SOM 데이터 수집 및 코퍼스 구축
cd C:\...\bizrag
python scripts/collect_tam_som_data.py

# 3. 펫테크 코퍼스 → Pinecone pettech 네임스페이스 업서트
python -m bizrag.pinecone_upload sync
```

수집 완료 시 `data/pettech/rag_corpus/` 구조:
```
knowledge.db           SQLite RAG 코퍼스 (문서·청크·FTS5 색인)
exports/
  pinecone_chunks.jsonl  Pinecone 업서트용 벡터 청크 (13,929개)
embeddings.sqlite3     로컬 임베딩 캐시
embedding_report.json  임베딩 검증 리포트
pinecone_upload.json   Pinecone 업서트 검증 리포트
manifest.json          코퍼스 메타데이터
```

### ⑥ 관련 파일

| 파일 | 설명 |
|---|---|
| `scripts/collect_tam_som_data.py` | TAM/SAM/SOM 수집 메인 스크립트 (WorldBank·KIPRIS·종합문서) |
| `bizrag/pettech.py` | KOSIS·ECOS·NAVER 수집기 (Collector 클래스) |
| `bizrag/pet_documents.py` | 수집 데이터 → RAG 문서 변환 |
| `bizrag/pinecone_upload.py` | 코퍼스 임베딩 및 Pinecone 업서트 |
| `bizrag/rag_index.py` | RagStore: 토큰 경계 청킹 + BM25 FTS5 |
| `config/pettech_vector.yaml` | 임베딩 설정 (384차원, fastembed, batch 64) |
| `config/pettech.yaml` | NAVER·ECOS 수집 배치 설정 |
