/**
 * 보고서 분야별 문단 다듬기 — 에이전트가 쓴 원문을 화면에 그대로 내보내지 않는다.
 * - 분석 끝에 붙는 내부 경고(" / 근거 없는 Fact를 Hypothesis로 전환했습니다" 등)를 뗀다
 * - 근거 번호 인용([0, 1, 2])과 마크다운 강조(**…**)를 지운다
 * - 분야마다 다른 말투를 '~다' 체로 맞춘다 (했습니다 → 했다, 입니다 → 이다)
 * 예전에 만든 보고서에도 적용되도록 화면에서 처리한다.
 */

// 에이전트 코드가 요약·권장 사항 끝에 덧붙이는 경고 — 화면에는 근거 패널이 따로 있어 뺀다
const INTERNAL_NOTE = /(Hypothesis로 전환|^근거 부족:|^검색 실패|추가 근거 수집 필요|시장 수치는 모두 가설)/;

const RISK_LEVEL: Record<string, string> = { critical: "매우 높음", high: "높음", medium: "중간", low: "낮음", unknown: "평가 불가" };

/** 인용 번호·마크다운 지우기 (말투는 그대로) */
export function stripMarkup(text: string): string {
  return text
    .replace(/\s*\[\d+(?:\s*[,~-]\s*\d+)*\]/g, "")
    .replace(/\*\*|__/g, "")
    .replace(/^#+\s*/gm, "")
    .replace(/\(\s*score\s*(\d+)\s*,\s*(critical|high|medium|low|unknown)\s*\)/gi, (_, n, lv) => `(위험 점수 ${n}, ${RISK_LEVEL[lv.toLowerCase()]})`)
    .replace(/[ \t]{2,}/g, " ")
    .trim();
}

/** '~습니다/~입니다'로 끝나는 문장을 '~다' 체로 */
function toPlainTone(text: string): string {
  return text
    .replace(/입니다(?=[.!?\s]|$)/g, "이다")
    .replace(/([가-힣])습니다(?=[.!?\s]|$)/g, "$1다")
    // 받침 ㅂ 꼴: 부족합니다 → 부족하다, 예상됩니다 → 예상된다
    .replace(/합니다(?=[.!?\s]|$)/g, "하다")
    .replace(/됩니다(?=[.!?\s]|$)/g, "된다")
    .replace(/집니다(?=[.!?\s]|$)/g, "진다");
}

/** 분야 요약 문단 */
export function cleanSummary(text: string): string {
  const kept = text
    .split(" / ")
    .map((s) => s.trim())
    .filter((s, i) => i === 0 || !INTERNAL_NOTE.test(s));
  return toPlainTone(stripMarkup(kept.join(" / ")));
}

/** 권장 사항 목록 — 내부 경고 줄은 빼고 인용 번호·마크다운만 지운다 */
export function cleanRecommendations(items: string[]): string[] {
  return items.filter((s) => !INTERNAL_NOTE.test(s.trim())).map(stripMarkup).filter(Boolean);
}
