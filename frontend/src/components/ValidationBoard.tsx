"use client";

import { useState } from "react";
import type { IdeaReport } from "@/lib/idea";
import {
  AREA_LABEL,
  AREA_OPTIONS,
  RESULT_META,
  type Validation,
  type ValidationResult,
  guessArea,
  methodLine,
  pendingValidations,
  reflectedVersion,
} from "@/lib/validation";
import type { ValidationPrefill } from "@/components/ValidationForm";

const blue = "#134CD8";
const navy = "#071B45";
const slate = "#53647A";
const gray = "#6B7280";
const line = "#D7E0ED";

/** 프로필의 '검증 기록' 탭 — 가설별 상태 보드 + 보고서 반영 */
export default function ValidationBoard({
  validations,
  reports,
  loading,
  error,
  canDiagnose,
  diagnosing,
  onAdd,
  onEdit,
  onDelete,
  onDiagnose,
}: {
  validations: Validation[];
  reports: IdeaReport[];
  loading: boolean;
  error: string | null;
  canDiagnose: boolean;
  diagnosing: boolean;
  onAdd: (prefill: ValidationPrefill) => void;
  onEdit: (v: Validation) => void;
  onDelete: (v: Validation) => void;
  onDiagnose: () => void;
}) {
  const latest = reports[0] ?? null;
  const pending = pendingValidations(validations, latest);
  const count = (r: ValidationResult) => validations.filter((v) => v.result === r).length;
  // 아직 검증 기록이 없는 약점을 '검증할 가설' 후보로 보여준다
  const weaknesses = (latest?.response.workflow_result.decision_result?.weaknesses ?? [])
    .map((w) => w.replace(/\(?\s*(신뢰도|확신도)[^)]*\)?/g, "").trim())
    .filter((w) => w && !validations.some((v) => v.hypothesis === w))
    .slice(0, 4);

  return (
    <section className="flex flex-col gap-4" aria-label="가설 검증 기록">
      <div className="bg-white rounded-lg shadow-card p-6 flex flex-col gap-4" style={{ border: `1px solid ${line}` }}>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex flex-col gap-1 min-w-0">
            <b className="text-base" style={{ color: navy }}>
              가설 검증 기록
            </b>
            <p className="text-sm m-0 leading-relaxed" style={{ color: slate }}>
              인터뷰 · 설문 · 사전예약 · MVP 시범 · 판매 테스트 등으로 직접 확인한 결과를 남겨요. 다음 보고서에 <b style={{ color: navy }}>창업가 검증</b> 근거로
              들어가, 검증되면 점수가 오르고 반증되면 내려갈 수 있어요.
            </p>
          </div>
          <button
            type="button"
            onClick={() => onAdd({})}
            className="min-h-[44px] px-4 rounded-xl text-sm font-bold text-white shrink-0"
            style={{ background: blue, border: "none", cursor: "pointer" }}
          >
            + 검증 추가
          </button>
        </div>

        {validations.length > 0 && (
          <div className="flex gap-2 flex-wrap">
            {(Object.keys(RESULT_META) as ValidationResult[]).map((r) => (
              <span key={r} className="text-xs font-bold px-2.5 py-1 rounded-lg" style={{ background: RESULT_META[r].bg, color: RESULT_META[r].color }}>
                {RESULT_META[r].label} {count(r)}
              </span>
            ))}
          </div>
        )}

        {pending.length > 0 && (
          <div className="rounded-xl p-4 flex items-center justify-between gap-3 flex-wrap" style={{ background: "#EAF0FD" }}>
            <span className="text-sm leading-relaxed" style={{ color: navy }}>
              {latest ? (
                <>
                  최신 보고서(v{latest.version})에 아직 반영되지 않은 검증이 <b>{pending.length}건</b> 있어요
                </>
              ) : (
                <>
                  검증 <b>{pending.length}건</b>이 첫 보고서에 근거로 들어가요
                </>
              )}
            </span>
            {!diagnosing && (
              <button
                type="button"
                onClick={onDiagnose}
                disabled={!canDiagnose}
                className="min-h-[44px] px-4 rounded-xl text-sm font-bold text-white disabled:opacity-50"
                style={{ background: blue, border: "none", cursor: "pointer" }}
              >
                {latest ? "검증 반영해 보고서 새로 작성 (유료)" : "상세분석하기 (유료)"}
              </button>
            )}
          </div>
        )}

        {error && (
          <div className="rounded-lg px-3 py-2.5 text-sm" style={{ background: "#FEF2F2", color: "#B42318" }} role="alert">
            {error}
          </div>
        )}
      </div>

      {loading ? (
        <div className="bg-white rounded-lg p-6 text-sm animate-pulse" style={{ border: `1px solid ${line}`, color: blue }}>
          검증 기록을 불러오는 중…
        </div>
      ) : validations.length === 0 ? (
        <div className="bg-white rounded-lg p-6 flex flex-col gap-3" style={{ border: `1px dashed ${line}` }}>
          <p className="text-sm m-0" style={{ color: slate }}>
            아직 검증 기록이 없어요. 보고서 약점 옆 <b style={{ color: navy }}>검증하기</b>를 누르거나, 아래 후보에서 골라 시작해 보세요.
          </p>
          {weaknesses.length > 0 && <Candidates items={weaknesses} onAdd={onAdd} />}
        </div>
      ) : (
        <>
          {AREA_OPTIONS.filter((a) => validations.some((v) => v.area === a.value)).map((a) => (
            <div key={a.value} className="flex flex-col gap-2">
              <div className="text-xs font-bold px-1" style={{ color: gray }}>
                {a.label}
              </div>
              {validations
                .filter((v) => v.area === a.value)
                .map((v) => (
                  <ValidationCard key={v.id} v={v} version={reflectedVersion(v, reports)} onEdit={() => onEdit(v)} onDelete={() => onDelete(v)} />
                ))}
            </div>
          ))}
          {weaknesses.length > 0 && (
            <div className="bg-white rounded-lg p-5 flex flex-col gap-3" style={{ border: `1px dashed ${line}` }}>
              <span className="text-xs font-bold" style={{ color: gray }}>
                보고서가 짚은 다른 약점 — 검증할 가설 후보
              </span>
              <Candidates items={weaknesses} onAdd={onAdd} />
            </div>
          )}
        </>
      )}
    </section>
  );
}

function Candidates({ items, onAdd }: { items: string[]; onAdd: (prefill: ValidationPrefill) => void }) {
  return (
    <ul className="m-0 p-0 list-none flex flex-col gap-1.5">
      {items.map((w, i) => (
        <li key={i}>
          <button
            type="button"
            onClick={() => onAdd({ hypothesis: w, area: guessArea(w) })}
            className="w-full text-left rounded-lg px-3 py-2.5 text-sm flex items-center justify-between gap-3"
            style={{ background: "#F5F7FB", border: "none", color: slate, cursor: "pointer" }}
          >
            <span className="min-w-0 line-clamp-2">{w}</span>
            <span className="text-xs font-bold shrink-0" style={{ color: blue }}>
              검증하기 ›
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function ValidationCard({ v, version, onEdit, onDelete }: { v: Validation; version: number | null; onEdit: () => void; onDelete: () => void }) {
  const meta = RESULT_META[v.result];
  const [open, setOpen] = useState(false);
  return (
    <article className="bg-white rounded-lg p-5 flex flex-col gap-2" style={{ border: `1px solid ${line}`, borderLeft: `4px solid ${meta.color}` }}>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs font-bold px-2 py-0.5 rounded-md" style={{ background: meta.bg, color: meta.color }}>
          {meta.label}
        </span>
        <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded" style={{ background: "#F5F7FB", color: slate }}>
          {AREA_LABEL[v.area]}
        </span>
        <span
          className="text-[11px] font-semibold px-1.5 py-0.5 rounded"
          style={version ? { background: "#E7F6EF", color: "#0F7B6C" } : { background: "#FFF6DE", color: "#8A4B08" }}
        >
          {version ? `v${version}에 반영됨` : "보고서 반영 전"}
        </span>
        <span className="ml-auto flex gap-1">
          <button type="button" onClick={onEdit} className="text-xs font-semibold px-2 py-1" style={{ background: "none", border: "none", color: slate, cursor: "pointer" }}>
            고치기
          </button>
          <button type="button" onClick={onDelete} className="text-xs font-semibold px-2 py-1" style={{ background: "none", border: "none", color: "#B42318", cursor: "pointer" }}>
            삭제
          </button>
        </span>
      </div>
      <b className="text-sm leading-relaxed" style={{ color: navy }}>
        {v.hypothesis}
      </b>
      {v.metric && (
        <p className="m-0 text-sm" style={{ color: navy }}>
          → {v.metric}
        </p>
      )}
      <div className="text-xs" style={{ color: gray }}>
        {[methodLine(v), v.doneAt].filter(Boolean).join(" · ")}
      </div>
      {v.note && (
        <div>
          <button
            type="button"
            onClick={() => setOpen((x) => !x)}
            aria-expanded={open}
            className="text-xs font-semibold p-0"
            style={{ background: "none", border: "none", color: blue, cursor: "pointer" }}
          >
            {open ? "▾ 메모 접기" : "▸ 메모 보기"}
          </button>
          {open && (
            <p className="m-0 mt-1.5 text-sm leading-relaxed whitespace-pre-wrap" style={{ color: slate }}>
              {v.note}
            </p>
          )}
        </div>
      )}
    </article>
  );
}
