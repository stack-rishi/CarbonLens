import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { ChevronDown, ChevronUp, CheckCircle, Archive } from "lucide-react";
import { api } from "../lib/api";
import { SeverityBadge } from "./SeverityBadge";
import { useToast } from "../hooks/use-toast";

interface Recommendation {
  title: string;
  description: string;
  category: string;
  estimated_impact_pct?: number;
}

interface Alert {
  id: string;
  alert_type: string;
  severity: "low" | "medium" | "high" | "critical";
  status: "active" | "acknowledged" | "resolved";
  title: string;
  message: string;
  scope?: string;
  metric_value?: number;
  threshold_value?: number;
  recommendations: Recommendation[];
  triggered_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
}

interface AlertCardProps {
  alert: Alert;
}

const CATEGORY_COLORS: Record<string, { bg: string; color: string }> = {
  logistics: { bg: "rgba(59,130,246,0.12)", color: "#3b82f6" },
  sourcing: { bg: "rgba(45,122,79,0.12)", color: "#2d7a4f" },
  process: { bg: "rgba(234,179,8,0.12)", color: "#ca8a04" },
  data_quality: { bg: "rgba(168,85,247,0.12)", color: "#9333ea" },
  strategy: { bg: "rgba(249,115,22,0.12)", color: "#ea580c" },
  general: { bg: "rgba(148,163,184,0.12)", color: "#64748b" },
};

export function AlertCard({ alert }: AlertCardProps) {
  const [expanded, setExpanded] = useState(false);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const acknowledgeMutation = useMutation({
    mutationFn: () => api.patch(`/alerts/${alert.id}/acknowledge`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["compliance-status"] });
      toast({ title: "Alert acknowledged" });
    },
  });

  const resolveMutation = useMutation({
    mutationFn: () => api.patch(`/alerts/${alert.id}/resolve`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["compliance-status"] });
      toast({ title: "Alert resolved" });
    },
  });

  const timeAgo = (() => {
    try {
      return formatDistanceToNow(new Date(alert.triggered_at), { addSuffix: true });
    } catch {
      return "recently";
    }
  })();

  const borderColor = {
    critical: "#ef4444",
    high: "#f97316",
    medium: "#eab308",
    low: "#94a3b8",
  }[alert.severity] ?? "#e2e8f0";

  return (
    <div
      className="rounded-2xl overflow-hidden transition-all duration-200"
      style={{
        background: "#fff",
        border: `1px solid ${borderColor}`,
        borderLeft: `4px solid ${borderColor}`,
        boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
      }}
    >
      {/* Header */}
      <div
        className="flex items-start gap-3 p-4 cursor-pointer"
        onClick={() => setExpanded((p) => !p)}
      >
        <SeverityBadge severity={alert.severity} className="mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold leading-tight" style={{ color: "#0d1f10" }}>
            {alert.title}
          </p>
          <p className="text-xs mt-0.5" style={{ color: "#8a9b8a" }}>
            {timeAgo}
            {alert.scope && (
              <span className="ml-2 px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 text-[10px] font-medium">
                Scope {alert.scope}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {/* Status chip */}
          <span
            className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
            style={{
              background:
                alert.status === "active"
                  ? "rgba(239,68,68,0.1)"
                  : alert.status === "acknowledged"
                  ? "rgba(234,179,8,0.1)"
                  : "rgba(34,197,94,0.1)",
              color:
                alert.status === "active"
                  ? "#dc2626"
                  : alert.status === "acknowledged"
                  ? "#ca8a04"
                  : "#16a34a",
            }}
          >
            {alert.status}
          </span>
          {expanded ? (
            <ChevronUp className="h-4 w-4 shrink-0" style={{ color: "#94a3b8" }} />
          ) : (
            <ChevronDown className="h-4 w-4 shrink-0" style={{ color: "#94a3b8" }} />
          )}
        </div>
      </div>

      {/* Expanded Body */}
      {expanded && (
        <div className="px-4 pb-4 space-y-4 border-t" style={{ borderColor: "#f1f5f1" }}>
          {/* Message */}
          <p className="text-sm mt-3 leading-relaxed" style={{ color: "#374151" }}>
            {alert.message}
          </p>

          {/* Metric values */}
          {(alert.metric_value !== undefined || alert.threshold_value !== undefined) && (
            <div className="flex gap-4">
              {alert.metric_value !== undefined && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "#8a9b8a" }}>
                    Current Value
                  </p>
                  <p className="text-sm font-bold" style={{ color: "#0d1f10" }}>
                    {alert.metric_value.toFixed(2)} tCO2e
                  </p>
                </div>
              )}
              {alert.threshold_value !== undefined && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "#8a9b8a" }}>
                    Threshold
                  </p>
                  <p className="text-sm font-bold" style={{ color: "#0d1f10" }}>
                    {alert.threshold_value.toFixed(2)} {alert.threshold_value <= 100 ? "" : "tCO2e"}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Recommendations */}
          {alert.recommendations?.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "#5a6b5a" }}>
                Recommendations
              </p>
              <div className="space-y-2">
                {alert.recommendations.map((rec, i) => {
                  const catStyle = CATEGORY_COLORS[rec.category] ?? CATEGORY_COLORS.general;
                  return (
                    <div
                      key={i}
                      className="p-3 rounded-xl"
                      style={{ background: "#f8fafc", border: "1px solid #e8f2e8" }}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-xs font-semibold" style={{ color: "#0d1f10" }}>
                          {rec.title}
                        </p>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <span
                            className="text-[10px] font-semibold px-1.5 py-0.5 rounded"
                            style={{ background: catStyle.bg, color: catStyle.color }}
                          >
                            {rec.category.replace("_", " ")}
                          </span>
                          {rec.estimated_impact_pct && (
                            <span
                              className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                              style={{ background: "rgba(45,122,79,0.12)", color: "#2d7a4f" }}
                            >
                              ~{rec.estimated_impact_pct}% impact
                            </span>
                          )}
                        </div>
                      </div>
                      <p className="text-xs mt-1 leading-relaxed" style={{ color: "#5a6b5a" }}>
                        {rec.description}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Footer actions */}
          <div className="flex gap-2 pt-1">
            {alert.status === "active" && (
              <button
                onClick={() => acknowledgeMutation.mutate()}
                disabled={acknowledgeMutation.isPending}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors"
                style={{
                  background: "rgba(234,179,8,0.12)",
                  color: "#ca8a04",
                  border: "1px solid rgba(234,179,8,0.3)",
                }}
              >
                <Archive className="h-3 w-3" />
                Acknowledge
              </button>
            )}
            {alert.status !== "resolved" && (
              <button
                onClick={() => resolveMutation.mutate()}
                disabled={resolveMutation.isPending}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors"
                style={{
                  background: "rgba(34,197,94,0.12)",
                  color: "#16a34a",
                  border: "1px solid rgba(34,197,94,0.3)",
                }}
              >
                <CheckCircle className="h-3 w-3" />
                Resolve
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
