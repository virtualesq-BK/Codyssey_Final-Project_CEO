import type { ReactNode } from "react";

interface Props {
  eyebrow: string;
  title: string;
  description?: ReactNode;
  /** 제목 오른쪽(넓은 화면)·아래(좁은 화면)에 둘 버튼 등 */
  actions?: ReactNode;
}

/** 목록 화면 맨 위 미니 히어로 — 키컬러(로열 블루) 띠로 아래 내용과 섹션을 나눈다. 안의 버튼은 흰 바탕으로 */
export default function PageHero({ eyebrow, title, description, actions }: Props) {
  return (
    <section className="relative overflow-hidden" style={{ background: "linear-gradient(100deg, #1B57EA 0%, #1446C4 100%)" }}>
      {/* 오른쪽 끝에 은은한 빛 */}
      <div
        aria-hidden="true"
        className="absolute pointer-events-none"
        style={{
          right: -120,
          top: -160,
          width: 420,
          height: 420,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(255,255,255,0.22), rgba(255,255,255,0) 70%)",
        }}
      />

      <div className="relative max-w-[1200px] mx-auto px-6 py-10 md:py-12 flex items-end justify-between gap-6 flex-wrap">
        <div className="flex flex-col gap-2 min-w-0">
          <div
            className="inline-flex items-center gap-2 self-start px-3 py-1 rounded-full text-xs font-semibold"
            style={{ color: "#fff", background: "rgba(255,255,255,0.12)", border: "1px solid rgba(255,255,255,0.15)" }}
          >
            <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: "#FDB71A" }} />
            {eyebrow}
          </div>
          <h1 className="text-3xl md:text-4xl font-bold m-0 tracking-tight" style={{ color: "#fff" }}>
            {title}
          </h1>
          {description && (
            <p className="m-0 text-base leading-relaxed" style={{ color: "rgba(255,255,255,0.85)" }}>
              {description}
            </p>
          )}
        </div>
        {actions && <div className="flex gap-2 flex-wrap">{actions}</div>}
      </div>
    </section>
  );
}
