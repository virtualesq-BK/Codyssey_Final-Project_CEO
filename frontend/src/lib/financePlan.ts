/**
 * 재무 시나리오 입력 — 수익 방식별로 사용자가 이해하는 말로 받고, 계산기(D팀, 구독형 구조)가 알아듣는 값으로 바꾼다.
 * 계산기 입력: price(고객 1명 월 결제액) · customers(월 결제 고객 수) · variable_cost_per_unit · fixed_cost
 *             · acquisition_cost · new_customers · monthly_churn_rate (금액 원, 기간 월)
 */
import type { FinanceInputs } from "@/lib/api";

export type RevenueType = "subscription" | "sales" | "commission" | "b2b" | "ads";

export interface FinancePlan {
  type: RevenueType;
  values: Record<string, number | null>;
}

export interface PlanField {
  key: string;
  label: string;
  unit: "원" | "명" | "건" | "곳" | "%";
  hint: string;
  optional?: boolean;
}

interface TypeDef {
  label: string;
  desc: string;
  /** 손익분기·고객 가치에서 '고객' 대신 쓰는 말 */
  unitNoun: string;
  fields: PlanField[];
  note: string;
}

const COMMON: PlanField[] = [
  { key: "fixed_cost", label: "월 고정비", unit: "원", hint: "인건비·임대료·툴 구독 등" },
  { key: "acquisition_cost", label: "월 마케팅·영업비", unit: "원", hint: "고객을 데려오는 데 쓰는 돈" },
];

export const REVENUE_TYPES: Record<RevenueType, TypeDef> = {
  subscription: {
    label: "구독형",
    desc: "매달·매년 정기 결제",
    unitNoun: "구독자",
    fields: [
      { key: "price", label: "월 구독료", unit: "원", hint: "예: 15000" },
      { key: "customers", label: "구독자 수", unit: "명", hint: "예: 300" },
      { key: "variable_cost_per_unit", label: "구독자 1명당 월 비용", unit: "원", hint: "서버·콘텐츠·결제 수수료" },
      ...COMMON,
      { key: "new_customers", label: "월 신규 구독자", unit: "명", hint: "예: 40" },
      { key: "monthly_churn_rate", label: "월 해지율", unit: "%", hint: "예: 5" },
    ],
    note: "구독료와 구독자 수를 그대로 계산했어요.",
  },
  sales: {
    label: "판매형",
    desc: "제품·음식·서비스를 건별 판매",
    unitNoun: "판매 건",
    fields: [
      { key: "aov", label: "평균 객단가", unit: "원", hint: "주문 1건 평균 금액" },
      { key: "orders", label: "월 판매 건수", unit: "건", hint: "예: 900" },
      { key: "cogs", label: "1건당 원가", unit: "원", hint: "재료비·포장·배송비" },
      ...COMMON,
      { key: "new_customers", label: "월 신규 고객", unit: "명", hint: "예: 200" },
      { key: "repeat_rate", label: "재구매율", unit: "%", hint: "한 달 안에 다시 사는 비율", optional: true },
    ],
    note: "객단가를 결제액, 판매 건수를 고객 수로 보고 계산했어요. 재구매율로 고객 가치를 어림해요.",
  },
  commission: {
    label: "수수료형",
    desc: "거래를 중개하고 수수료",
    unitNoun: "거래",
    fields: [
      { key: "gmv_per_txn", label: "건당 평균 거래액", unit: "원", hint: "거래 1건의 전체 금액" },
      { key: "take_rate", label: "수수료율", unit: "%", hint: "예: 10" },
      { key: "txns", label: "월 거래 건수", unit: "건", hint: "예: 2000" },
      { key: "cost_per_txn", label: "거래 1건당 비용", unit: "원", hint: "결제 수수료·CS 등" },
      ...COMMON,
      { key: "new_customers", label: "월 신규 이용자", unit: "명", hint: "예: 300" },
      { key: "monthly_churn_rate", label: "월 이탈률", unit: "%", hint: "예: 8", optional: true },
    ],
    note: "거래액 × 수수료율을 우리 매출로 계산했어요 (거래액 전체가 아니라).",
  },
  b2b: {
    label: "B2B 계약형",
    desc: "기관·기업과 연간 계약",
    unitNoun: "계약 기관",
    fields: [
      { key: "annual_contract", label: "계약 1건 연 금액", unit: "원", hint: "예: 1800000" },
      { key: "accounts", label: "계약 기관 수", unit: "곳", hint: "예: 20" },
      { key: "cost_per_account", label: "기관 1곳당 월 운영비", unit: "원", hint: "지원·서버·교육" },
      ...COMMON,
      { key: "new_customers", label: "월 신규 계약", unit: "곳", hint: "예: 2" },
      { key: "renewal_rate", label: "연 재계약률", unit: "%", hint: "예: 80" },
    ],
    note: "연 계약 금액을 12로 나눠 월 매출로, 재계약률로 월 해지율을 어림해 계산했어요.",
  },
  ads: {
    label: "광고형",
    desc: "무료로 쓰고 광고로 수익",
    unitNoun: "사용자",
    fields: [
      { key: "arpu", label: "사용자 1명당 월 광고 수익", unit: "원", hint: "예: 300" },
      { key: "mau", label: "월 활성 사용자", unit: "명", hint: "예: 50000" },
      { key: "cost_per_user", label: "사용자 1명당 월 비용", unit: "원", hint: "서버·콘텐츠" },
      ...COMMON,
      { key: "new_customers", label: "월 신규 사용자", unit: "명", hint: "예: 8000" },
      { key: "monthly_churn_rate", label: "월 이탈률", unit: "%", hint: "예: 20", optional: true },
    ],
    note: "사용자 1명당 광고 수익을 결제액, 활성 사용자를 고객 수로 보고 계산했어요.",
  },
};

export const TYPE_ORDER: RevenueType[] = ["subscription", "sales", "commission", "b2b", "ads"];

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

const n = (v: number | null | undefined) => (v == null || Number.isNaN(v) ? null : v);
const pct = (v: number | null | undefined) => (n(v) == null ? null : (v as number) / 100);

/** 화면 입력 → 계산기 입력 */
export function toCalculatorInputs(plan: FinancePlan): FinanceInputs {
  const v = plan.values;
  const common = { fixed_cost: n(v.fixed_cost), acquisition_cost: n(v.acquisition_cost), new_customers: n(v.new_customers) };
  switch (plan.type) {
    case "subscription":
      return { ...common, price: n(v.price), customers: n(v.customers), variable_cost_per_unit: n(v.variable_cost_per_unit), monthly_churn_rate: pct(v.monthly_churn_rate) };
    case "sales":
      return {
        ...common,
        price: n(v.aov),
        customers: n(v.orders),
        variable_cost_per_unit: n(v.cogs),
        monthly_churn_rate: n(v.repeat_rate) == null ? null : Math.max(0.01, 1 - (v.repeat_rate as number) / 100),
      };
    case "commission":
      return {
        ...common,
        price: n(v.gmv_per_txn) != null && n(v.take_rate) != null ? (v.gmv_per_txn as number) * ((v.take_rate as number) / 100) : null,
        customers: n(v.txns),
        variable_cost_per_unit: n(v.cost_per_txn),
        monthly_churn_rate: pct(v.monthly_churn_rate),
      };
    case "b2b":
      return {
        ...common,
        price: n(v.annual_contract) == null ? null : (v.annual_contract as number) / 12,
        customers: n(v.accounts),
        variable_cost_per_unit: n(v.cost_per_account),
        monthly_churn_rate: n(v.renewal_rate) == null ? null : Math.max(0.001, (1 - (v.renewal_rate as number) / 100) / 12),
      };
    case "ads":
      return { ...common, price: n(v.arpu), customers: n(v.mau), variable_cost_per_unit: n(v.cost_per_user), monthly_churn_rate: pct(v.monthly_churn_rate) };
  }
}

/** 분석이 뽑아 둔 계산기 값으로 처음 칸을 채운다 (구독형은 전부, 다른 유형은 공통 칸만) */
export function planFromExtracted(type: RevenueType, extracted: FinanceInputs): FinancePlan {
  const values: Record<string, number | null> = {
    fixed_cost: extracted.fixed_cost ?? null,
    acquisition_cost: extracted.acquisition_cost ?? null,
    new_customers: extracted.new_customers ?? null,
  };
  if (type === "subscription") {
    values.price = extracted.price ?? null;
    values.customers = extracted.customers ?? null;
    values.variable_cost_per_unit = extracted.variable_cost_per_unit ?? null;
    values.monthly_churn_rate = extracted.monthly_churn_rate == null ? null : extracted.monthly_churn_rate * 100;
  }
  return { type, values };
}
