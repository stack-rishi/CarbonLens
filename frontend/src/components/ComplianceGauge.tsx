import {
  RadialBarChart,
  RadialBar,
  ResponsiveContainer,
} from "recharts";

interface ComplianceGaugeProps {
  percentage: number;
  status: "compliant" | "warning" | "critical" | "unconfigured";
}

const STATUS_COLORS = {
  compliant: "#22c55e",
  warning: "#eab308",
  critical: "#ef4444",
  unconfigured: "#94a3b8",
};

export function ComplianceGauge({ percentage, status }: ComplianceGaugeProps) {
  const color = STATUS_COLORS[status] ?? "#94a3b8";
  const data = [{ value: percentage, fill: color }];

  return (
    <div className="relative w-full h-full flex items-center justify-center" style={{ minHeight: 120 }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart
          cx="50%"
          cy="50%"
          innerRadius="60%"
          outerRadius="90%"
          barSize={12}
          data={data}
          startAngle={220}
          endAngle={-40}
        >
          {/* Background track */}
          <RadialBar
            dataKey="value"
            cornerRadius={6}
            background={{ fill: "rgba(0,0,0,0.06)" }}
          />
        </RadialBarChart>
      </ResponsiveContainer>
      {/* Center text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <span
          className="text-3xl font-bold"
          style={{ color, fontVariantNumeric: "tabular-nums", letterSpacing: "-0.02em" }}
        >
          {Math.round(percentage)}%
        </span>
        <span className="text-xs mt-0.5" style={{ color: "#8a9b8a" }}>
          compliant
        </span>
      </div>
    </div>
  );
}
