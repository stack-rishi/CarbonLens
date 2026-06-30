import { cn } from "../lib/utils";

interface SeverityBadgeProps {
  severity: "low" | "medium" | "high" | "critical";
  className?: string;
}

const SEVERITY_STYLES = {
  low: {
    bg: "rgba(148,163,184,0.15)",
    color: "#64748b",
    dot: "#94a3b8",
    label: "Low",
  },
  medium: {
    bg: "rgba(234,179,8,0.15)",
    color: "#ca8a04",
    dot: "#eab308",
    label: "Medium",
  },
  high: {
    bg: "rgba(249,115,22,0.15)",
    color: "#ea580c",
    dot: "#f97316",
    label: "High",
  },
  critical: {
    bg: "rgba(239,68,68,0.15)",
    color: "#dc2626",
    dot: "#ef4444",
    label: "Critical",
  },
};

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  const s = SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.low;
  return (
    <span
      className={cn("inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold", className)}
      style={{ background: s.bg, color: s.color }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full shrink-0"
        style={{ background: s.dot }}
      />
      {s.label}
    </span>
  );
}
