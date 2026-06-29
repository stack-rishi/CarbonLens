import { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  delta?: number;
  icon: LucideIcon;
  iconBg?: string;   // background color for icon pill
  iconColor?: string; // icon stroke color
  accent?: string;   // value text color
}

export function StatCard({
  title,
  value,
  delta,
  icon: Icon,
  iconBg = "rgba(45,122,79,0.15)",
  iconColor = "#2d7a4f",
  accent = "#0d1f10",
}: StatCardProps) {
  return (
    <div
      className="animate-fade-in-up"
      style={{
        background: "#e8f2e8",
        border: "1px solid #d1e3d1",
        borderRadius: 20,
        padding: "20px 24px",
        boxShadow: "0 2px 8px rgba(13,26,15,0.04)",
        transition: "box-shadow 0.2s ease",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLDivElement).style.boxShadow = "0 4px 16px rgba(13,26,15,0.09)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLDivElement).style.boxShadow = "0 2px 8px rgba(13,26,15,0.04)";
      }}
    >
      <div className="flex items-start justify-between mb-3">
        <p className="label-caps">{title}</p>
        <div
          className="stat-icon"
          style={{ background: iconBg }}
        >
          <Icon style={{ width: 18, height: 18, color: iconColor }} />
        </div>
      </div>

      <div className="flex items-baseline gap-1.5">
        <span
          className="text-2xl font-bold"
          style={{ color: accent, letterSpacing: "-0.02em", fontVariantNumeric: "tabular-nums" }}
        >
          {value}
        </span>
        <span className="text-xs font-medium" style={{ color: "#8a9b8a" }}>tCO2e</span>
      </div>

      {delta !== undefined && delta !== 0 && (
        <p className="mt-2 text-[11px] flex items-center gap-1">
          <span
            className="font-semibold"
            style={{ color: delta > 0 ? "#dc2626" : "#2d7a4f" }}
          >
            {delta > 0 ? "▲" : "▼"} {Math.abs(delta)}%
          </span>
          <span style={{ color: "#8a9b8a" }}>vs prev period</span>
        </p>
      )}
    </div>
  );
}
