/**
 * 가설 검증 기록 — 창업가가 직접 검증한 결과.
 * 프로필(주장)도 보고서(AI 분석 스냅샷)도 아닌 별도 층이다.
 * 다음 보고서를 만들 때 '창업가 검증' 근거로 들어가 점수를 올리거나(검증됨) 내린다(반증됨).
 */
import type { IdeaReport } from "@/lib/idea";

export type ValidationResult = "supported" | "refuted" | "unclear";
export type ValidationArea =
  | "MarketAgent"
  | "CustomerAgent"
  | "CompetitorAgent"
  | "BusinessModelAgent"
  | "FinancialAgent"
  | "RiskAgent";

export interface Validation {
  id: string;
  hypothesis: string;
  area: ValidationArea;
  result: ValidationResult;
  method: string;
  sampleSize: number | null;
  /** 누구에게 검증했는지 (예: 초등 담임교사) */
  target: string;
  /** 핵심 수치·결과 한 줄 (예: 12명 중 9명이 주 3시간 이상) */
  metric: string;
  note: string;
  /** 검증한 날 (YYYY-MM-DD) */
  doneAt: string;
  /** 어디서 시작했는지 — 보고서 약점에서 눌렀으면 그 보고서 버전 */
  origin?: { reportId: string; version: number } | null;
  createdAt: string;
  updatedAt: string;
}

/** 백엔드 ValidationInput과 맞춘다 */
export interface ValidationInput {
  id: string;
  hypothesis: string;
  area: ValidationArea;
  result: ValidationResult;
  method: string;
  sample_size: number | null;
  target: string;
  metric: string;
  note: string;
  done_at: string;
  updated_at: string;
}

// 인터뷰는 여러 방법 중 하나일 뿐 — 실제 행동(가입·결제)을 보는 방법일수록 근거가 무겁다
export const VALIDATION_METHODS: { value: string; hint: string }[] = [
  { value: "고객 인터뷰", hint: "고객을 직접 만나 문제·대안을 물어봄" },
  { value: "설문조사", hint: "여러 명에게 같은 질문으로 응답을 모음" },
  { value: "랜딩페이지·사전예약", hint: "소개 페이지로 가입·사전예약 반응을 봄" },
  { value: "MVP 시범 운영", hint: "간단한 버전을 실제로 써보게 함" },
  { value: "판매 테스트", hint: "실제로 돈을 받고 팔아봄" },
  { value: "전문가 자문", hint: "업계 전문가에게 의견을 들음" },
  { value: "데이터 분석", hint: "공개 통계·내부 데이터를 분석함" },
  { value: "기타", hint: "그 밖의 방법" },
];

export const RESULT_META: Record<ValidationResult, { label: string; desc: string; color: string; bg: string; border: string }> = {
  supported: { label: "검증됨", desc: "가설이 맞았어요", color: "#0F7B6C", bg: "#E7F6EF", border: "#CDEBDD" },
  refuted: { label: "반증됨", desc: "가설이 틀렸어요", color: "#B42318", bg: "#FFF6F5", border: "#F5D3CF" },
  unclear: { label: "애매함", desc: "결론을 내리기 어려워요", color: "#8A4B08", bg: "#FFF6DE", border: "#F4E1B0" },
};

export const AREA_OPTIONS: { value: ValidationArea; label: string }[] = [
  { value: "CustomerAgent", label: "고객" },
  { value: "MarketAgent", label: "시장" },
  { value: "CompetitorAgent", label: "경쟁" },
  { value: "BusinessModelAgent", label: "수익 구조" },
  { value: "FinancialAgent", label: "재무" },
  { value: "RiskAgent", label: "리스크" },
];

export const AREA_LABEL = Object.fromEntries(AREA_OPTIONS.map((a) => [a.value, a.label])) as Record<ValidationArea, string>;

/** 약점 문장으로 분야를 짐작한다 (사용자가 폼에서 바꿀 수 있음) */
export function guessArea(text: string): ValidationArea {
  const rules: [RegExp, ValidationArea][] = [
    [/규제|법|인허가|개인정보|리스크|위험/, "RiskAgent"],
    [/재무|비용|손익|자금|원가|현금|투자/, "FinancialAgent"],
    [/가격|수익|과금|지불|매출|결제|구독|BM/, "BusinessModelAgent"],
    [/경쟁|차별|대체|진입/, "CompetitorAgent"],
    [/시장|규모|TAM|SAM|SOM|성장/, "MarketAgent"],
  ];
  return rules.find(([re]) => re.test(text))?.[1] ?? "CustomerAgent";
}

export function toValidationInput(v: Validation): ValidationInput {
  return {
    id: v.id,
    hypothesis: v.hypothesis.slice(0, 400),
    area: v.area,
    result: v.result,
    method: v.method,
    sample_size: v.sampleSize,
    target: v.target.slice(0, 120),
    metric: v.metric.slice(0, 400),
    note: v.note.slice(0, 2000),
    done_at: v.doneAt,
    updated_at: v.updatedAt,
  };
}

/** 이 보고서를 만들 때 들어간 검증 기록 */
export function usedIn(report: IdeaReport | null | undefined): ValidationInput[] {
  return report?.input.validations ?? [];
}

/** 최신 보고서에 아직 반영되지 않은 검증 (새로 추가했거나, 반영 뒤에 고친 것) */
export function pendingValidations(validations: Validation[], latest: IdeaReport | null | undefined): Validation[] {
  const used = new Map(usedIn(latest).map((u) => [u.id, u.updated_at]));
  return validations.filter((v) => used.get(v.id) !== v.updatedAt);
}

/** 이 검증이 반영된 가장 최근 보고서 버전 */
export function reflectedVersion(v: Validation, reports: IdeaReport[]): number | null {
  const hit = reports.find((r) => usedIn(r).some((u) => u.id === v.id && u.updated_at === v.updatedAt));
  return hit?.version ?? null;
}

export function methodLine(v: Pick<Validation, "method" | "sampleSize" | "target">) {
  return [v.method, v.sampleSize ? `${v.sampleSize}명` : "", v.target].filter(Boolean).join(" · ");
}
