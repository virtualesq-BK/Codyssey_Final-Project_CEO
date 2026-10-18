"use client";

import { useCallback, useRef, useState } from "react";
import { ModalFrame } from "@/components/DiagnosisModals";
import {
  AREA_OPTIONS,
  RESULT_META,
  VALIDATION_METHODS,
  type Validation,
  type ValidationArea,
  type ValidationResult,
} from "@/lib/validation";

const blue = "#134CD8";
const navy = "#071B45";
const slate = "#53647A";
const gray = "#6B7280";
const line = "#D7E0ED";

export type ValidationDraft = Omit<Validation, "id" | "createdAt" | "updatedAt"> & Partial<Pick<Validation, "id" | "createdAt">>;

/** 폼을 열 때 미리 채울 값 — 보고서 약점에서 열면 가설·분야가 채워진다 */
export type ValidationPrefill = Partial<ValidationDraft>;

const today = () => new Date().toLocaleDateString("sv-SE"); // YYYY-MM-DD

const field = "rounded-lg px-3 text-sm bg-white focus:outline-none w-full";

/** 가설 하나의 검증 결과 입력 — 방법은 인터뷰만이 아니라 설문·사전예약·MVP·판매 테스트 등 여러 가지 */
export default function ValidationForm({
  initial,
  onSave,
  onClose,
}: {
  initial: ValidationPrefill;
  onSave: (draft: ValidationDraft) => Promise<void>;
  onClose: () => void;
}) {
  const [hypothesis, setHypothesis] = useState(initial.hypothesis ?? "");
  const [area, setArea] = useState<ValidationArea>(initial.area ?? "CustomerAgent");
  const [method, setMethod] = useState(initial.method ?? "");
  const [result, setResult] = useState<ValidationResult | null>(initial.result ?? null);
  const [sample, setSample] = useState(initial.sampleSize != null ? String(initial.sampleSize) : "");
  const [target, setTarget] = useState(initial.target ?? "");
  const [metric, setMetric] = useState(initial.metric ?? "");
  const [note, setNote] = useState(initial.note ?? "");
  const [doneAt, setDoneAt] = useState(initial.doneAt || today());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 모달 틀이 닫기 함수가 바뀔 때마다 포커스를 옮기지 않게 고정한다
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const close = useCallback(() => closeRef.current(), []);

  const missing = [!hypothesis.trim() && "가설", !method && "검증 방법", !result && "결과"].filter(Boolean) as string[];
  const editing = !!initial.id;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (missing.length || !result) {
      setError(`${missing.join(" · ")}을(를) 채워주세요.`);
      return;
    }
    const n = sample.trim() ? Math.max(0, Math.round(Number(sample))) : null;
    setSaving(true);
    setError(null);
    try {
      await onSave({
        ...(initial.id ? { id: initial.id } : {}),
        ...(initial.createdAt ? { createdAt: initial.createdAt } : {}),
        hypothesis: hypothesis.trim(),
        area,
        result,
        method,
        sampleSize: n !== null && Number.isFinite(n) ? n : null,
        target: target.trim(),
        metric: metric.trim(),
        note: note.trim(),
        doneAt,
        origin: initial.origin ?? null,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSaving(false);
    }
  }

  return (
    <ModalFrame labelledBy="validation-title" onClose={close} width={600}>
      <form onSubmit={submit} className="flex flex-col">
        <div className="px-6 pt-6 pb-4 flex flex-col gap-1.5" style={{ borderBottom: `1px solid ${line}` }}>
          <h2 id="validation-title" className="text-lg font-bold m-0" style={{ color: navy }}>
            {editing ? "검증 기록 고치기" : "가설 검증 결과 남기기"}
          </h2>
          <p className="text-sm m-0 leading-relaxed" style={{ color: slate }}>
            직접 확인한 결과는 다음 보고서에 <b style={{ color: navy }}>창업가 검증</b> 근거로 들어가요. 검증되면 점수가 오르고, 반증되면 내려갈 수 있어요.
          </p>
        </div>

        <div className="px-6 py-5 flex flex-col gap-5">
          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-semibold" style={{ color: navy }}>
              검증한 가설 <span style={{ color: "#B42318" }}>*</span>
            </span>
            <textarea
              data-autofocus
              value={hypothesis}
              onChange={(e) => setHypothesis(e.target.value)}
              rows={2}
              maxLength={400}
              placeholder="예: 초등 담임교사는 학습지 만드는 데 주 3시간 이상 쓴다"
              className={`${field} py-2.5 resize-y leading-relaxed`}
              style={{ border: `1.5px solid ${line}` }}
            />
          </label>

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-semibold" style={{ color: navy }}>
              어느 분야의 가설인가요
            </span>
            <div className="flex gap-1.5 flex-wrap" role="radiogroup" aria-label="분야">
              {AREA_OPTIONS.map((a) => (
                <Chip key={a.value} on={area === a.value} onClick={() => setArea(a.value)}>
                  {a.label}
                </Chip>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-semibold" style={{ color: navy }}>
              검증 방법 <span style={{ color: "#B42318" }}>*</span>
            </span>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5" role="radiogroup" aria-label="검증 방법">
              {VALIDATION_METHODS.map((m) => (
                <Chip key={m.value} on={method === m.value} onClick={() => setMethod(m.value)} title={m.hint}>
                  {m.value}
                </Chip>
              ))}
            </div>
            {method && (
              <span className="text-xs" style={{ color: gray }}>
                {VALIDATION_METHODS.find((m) => m.value === method)?.hint}
              </span>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-semibold" style={{ color: navy }}>
              결과 <span style={{ color: "#B42318" }}>*</span>
            </span>
            <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="결과">
              {(Object.keys(RESULT_META) as ValidationResult[]).map((r) => {
                const meta = RESULT_META[r];
                const on = result === r;
                return (
                  <button
                    key={r}
                    type="button"
                    role="radio"
                    aria-checked={on}
                    onClick={() => setResult(r)}
                    className="rounded-xl px-3 py-2.5 flex flex-col items-start gap-0.5 text-left"
                    style={{
                      cursor: "pointer",
                      background: on ? meta.bg : "#fff",
                      border: `1.5px solid ${on ? meta.color : line}`,
                    }}
                  >
                    <b className="text-sm" style={{ color: on ? meta.color : navy }}>
                      {meta.label}
                    </b>
                    <span className="text-xs" style={{ color: slate }}>
                      {meta.desc}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-[1fr_120px_150px]">
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-semibold" style={{ color: navy }}>
                누구에게
              </span>
              <input
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                maxLength={120}
                placeholder="예: 경기 초등 담임교사"
                className={`${field} h-10`}
                style={{ border: `1.5px solid ${line}` }}
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-semibold" style={{ color: navy }}>
                인원·표본
              </span>
              <input
                type="number"
                min={0}
                inputMode="numeric"
                value={sample}
                onChange={(e) => setSample(e.target.value)}
                placeholder="명"
                className={`${field} h-10`}
                style={{ border: `1.5px solid ${line}` }}
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-semibold" style={{ color: navy }}>
                검증한 날
              </span>
              <input
                type="date"
                value={doneAt}
                onChange={(e) => setDoneAt(e.target.value)}
                className={`${field} h-10`}
                style={{ border: `1.5px solid ${line}` }}
              />
            </label>
          </div>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-semibold" style={{ color: navy }}>
              핵심 수치·결과 한 줄
            </span>
            <input
              value={metric}
              onChange={(e) => setMetric(e.target.value)}
              maxLength={400}
              placeholder="예: 12명 중 9명이 주 3시간 이상 · 사전예약 42명 · 판매 전환율 6%"
              className={`${field} h-10`}
              style={{ border: `1.5px solid ${line}` }}
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-semibold" style={{ color: navy }}>
              메모
            </span>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              maxLength={2000}
              placeholder="들은 말, 관찰한 것, 예상과 달랐던 점"
              className={`${field} py-2.5 resize-y leading-relaxed`}
              style={{ border: `1.5px solid ${line}` }}
            />
            <span className="text-xs" style={{ color: gray }}>
              이름·학교명·연락처 같은 개인정보는 빼고 적어주세요.
            </span>
          </label>

          {error && (
            <div className="rounded-lg px-3 py-2.5 text-sm" style={{ background: "#FEF2F2", color: "#B42318" }} role="alert">
              {error}
            </div>
          )}
        </div>

        <div className="px-6 py-4 flex justify-end gap-2" style={{ borderTop: `1px solid ${line}` }}>
          <button
            type="button"
            onClick={close}
            className="min-h-[44px] px-5 rounded-xl text-sm font-semibold bg-white"
            style={{ border: `1px solid ${line}`, color: slate, cursor: "pointer" }}
          >
            취소
          </button>
          <button
            type="submit"
            disabled={saving}
            className="min-h-[44px] px-5 rounded-xl text-sm font-bold text-white disabled:opacity-50"
            style={{ background: blue, border: "none", cursor: "pointer" }}
          >
            {saving ? "저장하는 중…" : "검증 기록 저장"}
          </button>
        </div>
      </form>
    </ModalFrame>
  );
}

function Chip({ on, onClick, title, children }: { on: boolean; onClick: () => void; title?: string; children: React.ReactNode }) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={on}
      onClick={onClick}
      title={title}
      className="min-h-[36px] px-3 rounded-lg text-xs font-semibold"
      style={{
        cursor: "pointer",
        background: on ? "#EAF0FD" : "#fff",
        color: on ? "#0F3DB0" : slate,
        border: `1.5px solid ${on ? blue : line}`,
      }}
    >
      {children}
    </button>
  );
}
