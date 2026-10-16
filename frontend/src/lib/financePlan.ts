/**
 * 월 손익계산서 — 업종·수익 방식에 맞는 항목을 AI가 제안하고 사용자가 고친다.
 * 계산은 여기서 한다: 매출 − 매출원가 = 매출총이익, 매출총이익 − 판매관리비 = 영업이익.
 */
import type { LineGroup } from "@/lib/api";

export type RevenueType = "subscription" | "sales" | "commission" | "b2b" | "ads";

export interface StatementLine {
  id: string;
  group: LineGroup;
  label: string;
  /** 월 금액 (원) */
  amount: number;
  basis?: string;
  /** 아직 AI 예시 그대로인지 (사용자가 고치면 false) */
  ai?: boolean;
}

export interface FinancePlan {
  type: RevenueType;
  lines: StatementLine[];
  /** 매출을 만드는 단위 (계약 기관, 구독자 …)와 그 월 수량 — 손익분기 '몇 곳/명'에 쓴다 */
  unitLabel: string;
  unitCount: number;
}

export const REVENUE_TYPES: Record<RevenueType, { label: string; desc: string }> = {
  subscription: { label: "구독형", desc: "매달·매년 정기 결제" },
  sales: { label: "판매형", desc: "제품·음식·서비스를 건별 판매" },
  commission: { label: "수수료형", desc: "거래를 중개하고 수수료" },
  b2b: { label: "B2B 계약형", desc: "기관·기업과 연간 계약" },
  ads: { label: "광고형", desc: "무료로 쓰고 광고로 수익" },
};

export const TYPE_ORDER: RevenueType[] = ["subscription", "sales", "commission", "b2b", "ads"];

export const GROUPS: { key: LineGroup; label: string; desc: string }[] = [
  { key: "revenue", label: "매출", desc: "돈이 들어오는 곳" },
  { key: "cogs", label: "매출원가 · 변동비", desc: "팔수록 같이 느는 비용" },
  { key: "opex", label: "판매관리비 · 고정비", desc: "매달 고정으로 나가는 비용" },
];

/** 프로필의 수익 모델 글로 유형을 짐작한다 (사용자가 바꿀 수 있음) */
export function guessRevenueType(text: string): RevenueType {
  const t = text.replace(/\s+/g, "");
  if (/수수료|중개|거래액|마켓플레이스|커미션/.test(t)) return "commission";
  if (/광고|애드|무료로/.test(t)) return "ads";
  if (/라이선스|계약|기관|학교|교육청|B2B|도입비/i.test(t)) return "b2b";
  if (/구독|월정액|정기결제|멤버십/.test(t)) return "subscription";
  if (/판매|객단가|주문|매장|구매/.test(t)) return "sales";
  return "subscription";
}

export interface Totals {
  revenue: number;
  cogs: number;
  gross: number;
  opex: number;
  operating: number;
  /** 영업이익률 (매출 0이면 null) */
  margin: number | null;
  /** 손익분기 매출 — 고정비 ÷ 공헌이익률 (팔수록 손해면 null) */
  breakevenRevenue: number | null;
  /** 손익분기에 필요한 단위 수 */
  breakevenUnits: number | null;
}

export function totalsOf(lines: StatementLine[], unitCount: number, revenueFactor = 1): Totals {
  const sum = (g: LineGroup) => lines.filter((l) => l.group === g).reduce((s, l) => s + (Number.isFinite(l.amount) ? l.amount : 0), 0);
  // 시나리오: 매출과 변동비는 같이 움직이고, 고정비는 그대로
  const revenue = sum("revenue") * revenueFactor;
  const cogs = sum("cogs") * revenueFactor;
  const opex = sum("opex");
  const gross = revenue - cogs;
  const operating = gross - opex;
  const ratio = revenue > 0 ? gross / revenue : 0;
  const breakevenRevenue = ratio > 0 ? opex / ratio : null;
  const perUnit = unitCount > 0 ? sum("revenue") / unitCount : 0;
  return {
    revenue,
    cogs,
    gross,
    opex,
    operating,
    margin: revenue > 0 ? operating / revenue : null,
    breakevenRevenue,
    breakevenUnits: breakevenRevenue != null && perUnit > 0 ? Math.ceil(breakevenRevenue / perUnit) : null,
  };
}

export const SCENARIOS = [
  { key: "conservative", label: "보수", factor: 0.7, desc: "매출 70%" },
  { key: "base", label: "기본", factor: 1, desc: "입력한 그대로" },
  { key: "optimistic", label: "낙관", factor: 1.3, desc: "매출 130%" },
] as const;

export const newLineId = () => Math.random().toString(36).slice(2, 10);

const wonShort = (v: number) => {
  const abs = Math.abs(v);
  const s = abs >= 1e8 ? `${(abs / 1e8).toFixed(1)}억` : abs >= 1e4 ? `${Math.round(abs / 1e4).toLocaleString()}만` : Math.round(abs).toLocaleString();
  return `${v < 0 ? "-" : ""}${s}원`;
};

/** 손익표가 채워져 있으면 한 줄 요약 (재무 카드·프로필 6번에 씀) */
export function financeSummary(plan: FinancePlan | null | undefined): string | null {
  if (!plan || !Array.isArray(plan.lines) || !plan.lines.some((l) => l.amount > 0)) return null;
  const t = totalsOf(plan.lines, plan.unitCount);
  const be = t.breakevenRevenue != null ? ` · 손익분기 월 ${wonShort(t.breakevenRevenue)}${t.breakevenUnits != null ? ` (${plan.unitLabel} ${t.breakevenUnits.toLocaleString()})` : ""}` : " · 팔수록 손해인 구조라 손익분기 없음";
  return `월 매출 ${wonShort(t.revenue)} · 비용 ${wonShort(t.cogs + t.opex)} · 영업이익 ${wonShort(t.operating)}${t.margin != null ? ` (${Math.round(t.margin * 100)}%)` : ""}${be}`;
}

/** 아직 AI 예시 그대로인 항목 비율이 낮을수록(직접 고칠수록) 확신도를 높게 본다 */
export function financeConfidence(plan: FinancePlan): number {
  const n = plan.lines.length || 1;
  const own = plan.lines.filter((l) => !l.ai).length / n;
  return Math.round((0.5 + 0.3 * own) * 100) / 100;
}
