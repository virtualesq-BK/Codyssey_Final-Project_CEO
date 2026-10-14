import { type IdeaStatus, STATUS_META } from "@/lib/idea";

export default function StatusPill({ status }: { status: IdeaStatus }) {
  const meta = STATUS_META[status];
  const inProgress = status === "profiling" || status === "diagnosing";
  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs font-semibold px-2 py-0.5 rounded whitespace-nowrap"
      style={{ background: meta.bg, color: meta.color }}
    >
      {inProgress && <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: meta.dot }} />}
      {meta.label}
    </span>
  );
}
