/**
 * 아이템 프로필을 화면 표의 '줄'로 펼치고, 줄 하나를 고치면 다시 칸 문자열로 합친다.
 * 1차 분석(v2)은 칸마다 "키: 값" 줄로 채우므로 그 키를 줄 이름으로 쓴다.
 */
import type { IdeaProfile, IdeaReport } from "@/lib/idea";

/** 칸별로 기대하는 줄 — 1차 분석 프롬프트(PROFILE_SYSTEM)의 틀과 맞춘다 */
const TEMPLATES: Partial<Record<keyof IdeaProfile, { key: string; label: string; hint: string }[]>> = {
  customer: [
    { key: "첫 공략", label: "첫 공략 고객", hint: "처음 공략할 구체적인 고객 한 그룹" },
    { key: "사용자 / 구매자", label: "쓰는 사람 / 돈 내는 사람", hint: "쓰는 사람 / 돈 내는 사람" },
  ],
  problem: [
    { key: "문제", label: "문제 정의", hint: "누가, 어떤 상황에서, 무엇 때문에, 그래서 어떤 결과가" },
    { key: "빈도·강도", label: "빈도 · 강도", hint: "얼마나 자주, 얼마나 아픈지" },
    { key: "현재 대안", label: "지금 쓰는 대안", hint: "지금 쓰는 방법 — 한계: 그 방법의 불만" },
  ],
  solution: [
    { key: "핵심 기능", label: "핵심 기능", hint: "2~3개, · 로 구분" },
    { key: "차별점", label: "고유 가치 · 차별점", hint: "지금 쓰는 대안과 다른 점" },
  ],
  revenueModel: [
    { key: "구매자 · 방식 · 가격 가설", label: "수익 방식 · 가격", hint: "누가 · 구독/건당/라이선스 등 · 대략 얼마" },
  ],
};

export interface ProfileRow {
  id: string;
  label: string;
  value: string;
  hint: string;
  /** 고칠 수 있는 줄이면 어느 칸의 어느 키인지 */
  field?: keyof IdeaProfile;
  key?: string | null;
  /** 상세분석 결과에서 온 줄 (읽기 전용) */
  fromReport?: number;
  required?: boolean;
}

const norm = (s: string) => s.replace(/\s+/g, "");

/** "키: 값" 줄들을 키 → 값으로. 키 없는 줄은 앞 줄 값에 이어 붙인다 */
function parseLines(text: string): { key: string | null; value: string }[] {
  const out: { key: string | null; value: string }[] = [];
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line) continue;
    // "- 후보 ①: …" 같은 목록 줄은 키가 아니라 앞 줄의 이어짐
    const bullet = /^[-·•*]\s/.test(line);
    const m = bullet ? null : line.match(/^([^:：]{1,24})[:：]\s*(.*)$/);
    if (m) out.push({ key: m[1].trim(), value: m[2].trim() });
    else if (out.length) out[out.length - 1].value += `\n${line}`;
    else out.push({ key: null, value: line });
  }
  return out;
}

/** 칸 하나를 줄들로. 틀이 있는데 키 구조가 아니면(직접 쓴 글·예전 기록) 한 줄로 보여준다 */
export function fieldRows(profile: IdeaProfile, field: keyof IdeaProfile, fallbackLabel: string, required: boolean): ProfileRow[] {
  const template = TEMPLATES[field];
  const text = profile[field] ?? "";
  if (!template) {
    return [{ id: field, label: fallbackLabel, value: text, hint: "", field, key: null, required }];
  }
  const parsed = parseLines(text);
  const structured = parsed.length > 0 && parsed.every((p) => p.key !== null);
  if (text.trim() && !structured) {
    return [{ id: field, label: fallbackLabel, value: text.trim(), hint: "", field, key: null, required }];
  }
  const used = new Set<number>();
  const rows: ProfileRow[] = template.map((t) => {
    const idx = parsed.findIndex((p, i) => !used.has(i) && p.key && norm(p.key) === norm(t.key));
    if (idx >= 0) used.add(idx);
    return {
      id: `${field}:${t.key}`,
      label: t.label,
      value: idx >= 0 ? parsed[idx].value : "",
      hint: t.hint,
      field,
      key: t.key,
      required,
    };
  });
  parsed.forEach((p, i) => {
    if (!used.has(i) && p.key) {
      rows.push({ id: `${field}:${p.key}`, label: p.key, value: p.value, hint: "", field, key: p.key, required: false });
    }
  });
  return rows;
}

/** 줄 하나를 고친 결과를 칸 문자열로 다시 합친다 */
export function updateRow(profile: IdeaProfile, row: ProfileRow, value: string): IdeaProfile {
  if (!row.field) return profile;
  if (row.key === null || row.key === undefined) return { ...profile, [row.field]: value.trim() };
  const rows = fieldRows(profile, row.field, row.label, false).map((r) =>
    r.id === row.id ? { ...r, value: value.trim() } : r,
  );
  const text = rows
    .filter((r) => r.value)
    .map((r) => `${r.key}: ${r.value}`)
    .join("\n");
  return { ...profile, [row.field]: text };
}

/** 비었거나 "(미확인)"뿐인 줄. 일부만 미확인이면 채워진 것으로 본다 */
export function isUnknown(value: string) {
  return !value.replace(/\(미확인\)/g, "").trim();
}

type Claim = { text?: string } | undefined;
type Finding = Record<string, unknown>;

function findingOf(report: IdeaReport | null, agent: string, key: string): Finding | null {
  const findings = report?.response.workflow_result.agent_results[agent]?.findings ?? [];
  for (const f of findings) if (f && typeof f === "object" && key in f) return f[key] as Finding;
  return null;
}

/** 상세분석에서 가져오는 줄 — 분석 전이면 값이 비어 있다 */
export function reportRows(report: IdeaReport | null) {
  const market = findingOf(report, "MarketAgent", "market_analysis");
  const competition = findingOf(report, "CompetitorAgent", "competition_analysis");
  const v = report?.version;
  const competitors = [
    ...(((competition?.direct_competitors as Finding[]) ?? []).map((c) => c.name as string)),
    ...(((competition?.indirect_competitors as Finding[]) ?? []).map((c) => `${c.name as string} (간접)`)),
  ].filter(Boolean);
  const market_ = (k: string) => ((market?.[k] as Claim)?.text ?? "").trim();

  return {
    market: [
      { id: "market:size", label: "시장 규모", value: market_("market_size"), hint: "전체 / 목표 시장 규모 — 공공 통계 근거", fromReport: v },
      { id: "market:target", label: "목표 시장", value: market_("target_market_size"), hint: "1차 공략 시장의 크기", fromReport: v },
      { id: "market:growth", label: "성장 추세", value: market_("growth_rate"), hint: "관련 시장·대상 수의 변화", fromReport: v },
    ] as ProfileRow[],
    competition: [
      {
        id: "comp:list",
        label: "주요 경쟁사",
        value: competitors.join(" · ") || ((competition?.summary as string) ?? ""),
        hint: "경쟁·대체 서비스 비교",
        fromReport: v,
      },
      {
        id: "comp:position",
        label: "경쟁 포지션",
        value: ((competition?.competitive_position as Claim)?.text ?? "").trim(),
        hint: "우리가 설 자리",
        fromReport: v,
      },
    ] as ProfileRow[],
  };
}
