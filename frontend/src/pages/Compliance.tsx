import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Shield, AlertTriangle, RefreshCw, Settings, FileDown, X } from "lucide-react";
import { api } from "../lib/api";
import { ComplianceGauge } from "../components/ComplianceGauge";
import { SeverityBadge } from "../components/SeverityBadge";
import { AlertCard } from "../components/AlertCard";
import { Skeleton } from "../components/ui/skeleton";
import { useToast } from "../hooks/use-toast";

const CHART_TOOLTIP_STYLE = {
  background: "#0d1a0f",
  border: "1px solid rgba(255,255,255,0.10)",
  borderRadius: "12px",
  color: "#e8f2e8",
  fontSize: "13px",
};

const STATUS_LABELS: Record<string, { label: string; emoji: string; color: string; bg: string }> = {
  compliant: { label: "Compliant", emoji: "🟢", color: "#16a34a", bg: "rgba(22,163,74,0.1)" },
  warning: { label: "Warning", emoji: "🟡", color: "#ca8a04", bg: "rgba(202,138,4,0.1)" },
  critical: { label: "Critical", emoji: "🔴", color: "#dc2626", bg: "rgba(220,38,38,0.1)" },
  unconfigured: { label: "Unconfigured", emoji: "⚪", color: "#64748b", bg: "rgba(100,116,139,0.1)" },
};

export default function Compliance() {
  const [alertFilter, setAlertFilter] = useState<string>("all");
  const [showThresholdModal, setShowThresholdModal] = useState(false);
  const [showTargetModal, setShowTargetModal] = useState(false);
  const [thresholdInputs, setThresholdInputs] = useState<Record<string, string>>({});
  const [targetInputs, setTargetInputs] = useState({
    baseline_year: "",
    target_reduction_pct: "20",
    net_zero_target_year: "",
  });
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch compliance status — refetch every 15s for "real-time" feel
  const { data: status, isLoading: isStatusLoading } = useQuery({
    queryKey: ["compliance-status"],
    queryFn: async () => {
      const res = await api.get("/compliance/status");
      return res.data;
    },
    refetchInterval: 15000,
  });

  // Fetch thresholds
  const { data: thresholds } = useQuery({
    queryKey: ["compliance-thresholds"],
    queryFn: async () => {
      const res = await api.get("/compliance/thresholds");
      return res.data as Array<{ scope: string; threshold_tco2e: number | null; configured: boolean }>;
    },
  });

  // Fetch alerts
  const { data: alerts, isLoading: isAlertsLoading } = useQuery({
    queryKey: ["alerts", alertFilter],
    queryFn: async () => {
      const params: Record<string, string> = { limit: "50" };
      if (alertFilter !== "all") params.status = alertFilter;
      const res = await api.get("/alerts", { params });
      return res.data;
    },
    refetchInterval: 15000,
  });

  // Manual recalculate
  const evaluateMutation = useMutation({
    mutationFn: () => api.post("/compliance/evaluate"),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["compliance-status"] });
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      const count = data.data?.new_or_updated_alerts?.length ?? 0;
      toast({
        title: "Recalculated",
        description: `${count} alert(s) updated`,
      });
    },
    onError: () => {
      toast({ title: "Evaluation failed", variant: "destructive" });
    },
  });

  // Save thresholds
  const thresholdMutation = useMutation({
    mutationFn: (thresholds: Array<{ scope: string; threshold_tco2e: number }>) =>
      api.put("/compliance/thresholds", { thresholds }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compliance-thresholds"] });
      queryClient.invalidateQueries({ queryKey: ["compliance-status"] });
      setShowThresholdModal(false);
      toast({ title: "Thresholds saved" });
    },
  });

  // Save targets
  const targetMutation = useMutation({
    mutationFn: (targets: { baseline_year?: number; target_reduction_pct?: number; net_zero_target_year?: number }) =>
      api.put("/compliance/targets", targets),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compliance-status"] });
      setShowTargetModal(false);
      toast({ title: "Reduction targets updated" });
    },
    onError: (err: any) => {
      toast({ title: "Failed to save targets", description: err.response?.data?.detail || "", variant: "destructive" });
    },
  });

  // Generate compliance report
  const reportMutation = useMutation({
    mutationFn: () => api.post("/compliance/report/generate", {}),
    onSuccess: (data) => {
      toast({
        title: "Report generation started",
        description: `Report ID: ${data.data?.id?.slice(0, 8)}...`,
      });
    },
  });

  const handleSaveThresholds = () => {
    const payload = Object.entries(thresholdInputs)
      .filter(([, v]) => v && !isNaN(Number(v)) && Number(v) > 0)
      .map(([scope, v]) => ({ scope, threshold_tco2e: Number(v) }));
    if (payload.length === 0) {
      toast({ title: "Enter at least one threshold", variant: "destructive" });
      return;
    }
    thresholdMutation.mutate(payload);
  };

  const handleSaveTargets = () => {
    const baseline = targetInputs.baseline_year ? Number(targetInputs.baseline_year) : undefined;
    const reduction = targetInputs.target_reduction_pct ? Number(targetInputs.target_reduction_pct) : 20.0;
    const netZero = targetInputs.net_zero_target_year ? Number(targetInputs.net_zero_target_year) : undefined;

    if (baseline && (baseline < 2000 || baseline > 2100)) {
      toast({ title: "Invalid baseline year", variant: "destructive" });
      return;
    }
    if (netZero && (netZero < 2020 || netZero > 2100)) {
      toast({ title: "Invalid net-zero year", variant: "destructive" });
      return;
    }

    targetMutation.mutate({
      baseline_year: baseline,
      target_reduction_pct: reduction,
      net_zero_target_year: netZero,
    });
  };

  const overallStatus = status?.status ?? "unconfigured";
  const statusMeta = STATUS_LABELS[overallStatus] ?? STATUS_LABELS.unconfigured;
  const compliancePct = status?.compliance_pct ?? 0;
  const sustainabilityScore = status?.sustainability_score ?? 0;
  const scopeBreakdown: any[] = status?.scope_breakdown ?? [];
  const currentMonth = status?.current_month ?? {};
  const previousMonth = status?.previous_month ?? {};
  const alertCounts = status?.active_alerts_count ?? { low: 0, medium: 0, high: 0, critical: 0 };
  const totalCriticalHigh = (alertCounts.critical ?? 0) + (alertCounts.high ?? 0);

  // Trend chart data
  const trendData = [
    {
      name: "Scope 1",
      Current: currentMonth.scope1 ?? 0,
      Previous: previousMonth.scope1 ?? 0,
    },
    {
      name: "Scope 2",
      Current: currentMonth.scope2 ?? 0,
      Previous: previousMonth.scope2 ?? 0,
    },
    {
      name: "Scope 3",
      Current: currentMonth.scope3 ?? 0,
      Previous: previousMonth.scope3 ?? 0,
    },
  ];

  if (isStatusLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <Skeleton className="h-9 w-48 rounded-xl" style={{ background: "#d1e3d1" }} />
          <Skeleton className="h-9 w-40 rounded-xl" style={{ background: "#d1e3d1" }} />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-40 rounded-xl" style={{ background: "#d1e3d1" }} />
          ))}
        </div>
        <Skeleton className="h-64 w-full rounded-xl" style={{ background: "#d1e3d1" }} />
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-10">
      {/* ── Header ───────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "#0d1f10", letterSpacing: "-0.02em" }}>
            Compliance Monitor
          </h1>
          <p className="text-sm mt-0.5" style={{ color: "#5a6b5a" }}>
            Real-time threshold tracking, alert management, and sustainability scoring
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => evaluateMutation.mutate()}
            disabled={evaluateMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all"
            style={{ background: "#0d1a0f", color: "#4ade80" }}
          >
            <RefreshCw className={`h-4 w-4 ${evaluateMutation.isPending ? "animate-spin" : ""}`} />
            {evaluateMutation.isPending ? "Recalculating…" : "Recalculate Now"}
          </button>
          <button
            onClick={() => {
              const init: Record<string, string> = {};
              thresholds?.forEach((t) => {
                if (t.threshold_tco2e) init[t.scope] = String(t.threshold_tco2e);
              });
              setThresholdInputs(init);
              setShowThresholdModal(true);
            }}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all"
            style={{
              background: "#e8f2e8",
              color: "#2d7a4f",
              border: "1px solid #d1e3d1",
            }}
          >
            <Settings className="h-4 w-4" />
            Configure Thresholds
          </button>
          <button
            onClick={() => {
              // Pre-fill targets from the compliance status or default values
              setTargetInputs({
                baseline_year: status?.baseline_year ? String(status.baseline_year) : "2023",
                target_reduction_pct: status?.target_reduction_pct ? String(status.target_reduction_pct) : "20",
                net_zero_target_year: status?.net_zero_target_year ? String(status.net_zero_target_year) : "2030",
              });
              setShowTargetModal(true);
            }}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all"
            style={{
              background: "#e8f2e8",
              color: "#2d7a4f",
              border: "1px solid #d1e3d1",
            }}
          >
            <Settings className="h-4 w-4" />
            Configure Targets
          </button>
          <button
            onClick={() => reportMutation.mutate()}
            disabled={reportMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all"
            style={{
              background: "rgba(45,122,79,0.12)",
              color: "#2d7a4f",
              border: "1px solid rgba(45,122,79,0.2)",
            }}
          >
            <FileDown className="h-4 w-4" />
            Export Report
          </button>
        </div>
      </div>

      {/* ── Top Row: 3 Status Cards ───────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1: Compliance Status + Gauge */}
        <div
          className="card flex flex-col"
          style={{ minHeight: 200 }}
        >
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-semibold" style={{ color: "#0d1f10" }}>
              Compliance Status
            </p>
            <span
              className="px-3 py-1 rounded-full text-xs font-bold"
              style={{ background: statusMeta.bg, color: statusMeta.color }}
            >
              {statusMeta.emoji} {statusMeta.label}
            </span>
          </div>
          <div className="flex-1" style={{ minHeight: 140 }}>
            <ComplianceGauge percentage={compliancePct} status={overallStatus as any} />
          </div>
        </div>

        {/* Card 2: Sustainability Score */}
        <div className="card flex flex-col justify-between" style={{ minHeight: 200 }}>
          <p className="text-sm font-semibold" style={{ color: "#0d1f10" }}>
            Sustainability Score
          </p>
          <div className="flex-1 flex flex-col items-center justify-center">
            <span
              className="text-6xl font-bold"
              style={{
                color:
                  sustainabilityScore >= 70
                    ? "#22c55e"
                    : sustainabilityScore >= 50
                    ? "#eab308"
                    : "#ef4444",
                fontVariantNumeric: "tabular-nums",
                letterSpacing: "-0.03em",
              }}
            >
              {Math.round(sustainabilityScore)}
            </span>
            <span className="text-lg font-medium mt-1" style={{ color: "#8a9b8a" }}>
              / 100
            </span>
            <p className="text-xs mt-2 text-center" style={{ color: "#5a6b5a" }}>
              Weighted score: reduction progress, ESG, trend & compliance
            </p>
          </div>
        </div>

        {/* Card 3: Active Alerts by Severity */}
        <div className="card" style={{ minHeight: 200 }}>
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="h-4 w-4" style={{ color: totalCriticalHigh > 0 ? "#ef4444" : "#2d7a4f" }} />
            <p className="text-sm font-semibold" style={{ color: "#0d1f10" }}>
              Active Alerts
            </p>
            {totalCriticalHigh > 0 && (
              <span
                className="ml-auto px-2 py-0.5 rounded-full text-xs font-bold"
                style={{ background: "#ef4444", color: "#fff" }}
              >
                {totalCriticalHigh} urgent
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2">
            {(["critical", "high", "medium", "low"] as const).map((sev) => (
              <div
                key={sev}
                className="flex flex-col items-center justify-center p-3 rounded-xl"
                style={{ background: "#f8fafc", border: "1px solid #e8f2e8" }}
              >
                <span
                  className="text-2xl font-bold"
                  style={{
                    color:
                      sev === "critical"
                        ? "#dc2626"
                        : sev === "high"
                        ? "#ea580c"
                        : sev === "medium"
                        ? "#ca8a04"
                        : "#64748b",
                  }}
                >
                  {alertCounts[sev] ?? 0}
                </span>
                <SeverityBadge severity={sev} className="mt-1" />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Scope Breakdown Row ────────────────────────── */}
      <div>
        <h2 className="text-base font-semibold mb-3" style={{ color: "#0d1f10" }}>
          Scope Breakdown
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {scopeBreakdown.map((sb: any) => {
            const pct = sb.pct_of_threshold;
            const isOver = pct !== null && pct > 100;
            const isWarn = pct !== null && pct > 90 && pct <= 100;
            const barColor = pct === null
              ? "#d1d5db"
              : pct > 110
              ? "#ef4444"
              : pct > 90
              ? "#eab308"
              : "#22c55e";

            return (
              <div
                key={sb.scope}
                className="card"
                style={{ border: isOver ? "1px solid #fca5a5" : isWarn ? "1px solid #fde68a" : undefined }}
              >
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-bold uppercase tracking-wider" style={{ color: "#5a6b5a" }}>
                    {sb.scope === "total" ? "Total" : `Scope ${sb.scope}`}
                  </p>
                  {!sb.configured && (
                    <span
                      className="text-[10px] font-semibold px-1.5 py-0.5 rounded"
                      style={{ background: "#f1f5f1", color: "#94a3b8" }}
                    >
                      Not set
                    </span>
                  )}
                </div>
                <p className="text-lg font-bold mb-1" style={{ color: "#0d1f10" }}>
                  {sb.current_tco2e.toFixed(1)}
                  <span className="text-xs font-normal ml-1" style={{ color: "#8a9b8a" }}>tCO2e</span>
                </p>
                {sb.configured ? (
                  <>
                    <div
                      className="h-2 rounded-full overflow-hidden"
                      style={{ background: "#e8f2e8" }}
                    >
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${Math.min(pct ?? 0, 100)}%`,
                          background: barColor,
                        }}
                      />
                    </div>
                    <p className="text-xs mt-1" style={{ color: barColor, fontWeight: 600 }}>
                      {pct?.toFixed(1)}% of {sb.threshold_tco2e?.toFixed(1)} tCO2e limit
                    </p>
                  </>
                ) : (
                  <button
                    onClick={() => setShowThresholdModal(true)}
                    className="text-xs mt-1 font-semibold"
                    style={{ color: "#2d7a4f" }}
                  >
                    + Set threshold →
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Trend Comparison Chart ─────────────────────── */}
      <div className="card-dark">
        <p className="text-sm font-semibold mb-4" style={{ color: "#e8f2e8" }}>
          Current vs Previous Month — Emissions by Scope
        </p>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={trendData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="name" stroke="#5a7a5a" fontSize={11} />
              <YAxis stroke="#5a7a5a" fontSize={11} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
              <Legend wrapperStyle={{ color: "#8ea58e", fontSize: 12 }} />
              <Bar dataKey="Previous" name="Previous Month" fill="#475569" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Current" name="Current Month" fill="#2d7a4f" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Alert Feed ─────────────────────────────────── */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold" style={{ color: "#0d1f10" }}>
            Alert History
          </h2>
          {/* Filter tabs */}
          <div
            className="flex items-center gap-1 p-1 rounded-xl"
            style={{ background: "#e8f2e8", border: "1px solid #d1e3d1" }}
          >
            {["all", "active", "acknowledged", "resolved"].map((f) => (
              <button
                key={f}
                onClick={() => setAlertFilter(f)}
                className="px-3 py-1 rounded-lg text-xs font-semibold transition-all"
                style={
                  alertFilter === f
                    ? { background: "#2d7a4f", color: "#fff" }
                    : { color: "#5a6b5a" }
                }
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {isAlertsLoading ? (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-16 rounded-xl" style={{ background: "#d1e3d1" }} />
            ))}
          </div>
        ) : alerts?.length === 0 ? (
          <div
            className="flex flex-col items-center justify-center py-16 rounded-2xl text-center"
            style={{ background: "#f8faf8", border: "1px dashed #d1e3d1" }}
          >
            <Shield className="h-12 w-12 mb-3" style={{ color: "#d1e3d1" }} />
            <p className="text-sm font-semibold" style={{ color: "#5a6b5a" }}>
              No alerts in this view
            </p>
            <p className="text-xs mt-1" style={{ color: "#8a9b8a" }}>
              All clear! Configure thresholds to start monitoring.
            </p>
            <button
              onClick={() => setShowThresholdModal(true)}
              className="mt-4 px-4 py-2 rounded-xl text-sm font-semibold"
              style={{ background: "#2d7a4f", color: "#fff" }}
            >
              Set up thresholds
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert: any) => (
              <AlertCard key={alert.id} alert={alert} />
            ))}
          </div>
        )}
      </div>

      {/* ── Configure Thresholds Modal ─────────────────── */}
      {showThresholdModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setShowThresholdModal(false)}
          />
          <div
            className="relative z-50 w-full max-w-md rounded-2xl p-6 shadow-2xl"
            style={{ background: "#fff" }}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold" style={{ color: "#0d1f10" }}>
                Configure Emission Thresholds
              </h3>
              <button
                onClick={() => setShowThresholdModal(false)}
                className="p-1 rounded-lg"
                style={{ color: "#94a3b8" }}
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <p className="text-xs mb-4" style={{ color: "#5a6b5a" }}>
              Set monthly emission thresholds (tCO2e) per scope. Alerts fire when current emissions exceed these values.
            </p>
            <div className="space-y-3">
              {["1", "2", "3", "total"].map((scope) => (
                <div key={scope} className="flex items-center gap-3">
                  <label
                    className="text-sm font-semibold w-20 shrink-0"
                    style={{ color: "#0d1f10" }}
                  >
                    {scope === "total" ? "Total" : `Scope ${scope}`}
                  </label>
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={thresholdInputs[scope] ?? ""}
                    onChange={(e) =>
                      setThresholdInputs((p) => ({ ...p, [scope]: e.target.value }))
                    }
                    placeholder="e.g. 50.0"
                    className="flex-1 px-3 py-2 rounded-xl text-sm border outline-none focus:ring-2 focus:ring-green-500"
                    style={{ border: "1px solid #d1e3d1" }}
                  />
                  <span className="text-xs shrink-0" style={{ color: "#8a9b8a" }}>
                    tCO2e
                  </span>
                </div>
              ))}
            </div>
            <div className="flex gap-2 mt-5">
              <button
                onClick={() => setShowThresholdModal(false)}
                className="flex-1 py-2 rounded-xl text-sm font-semibold"
                style={{ background: "#f1f5f1", color: "#374151" }}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveThresholds}
                disabled={thresholdMutation.isPending}
                className="flex-1 py-2 rounded-xl text-sm font-bold"
                style={{ background: "#2d7a4f", color: "#fff" }}
              >
                {thresholdMutation.isPending ? "Saving…" : "Save Thresholds"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Configure Targets Modal ─────────────────── */}
      {showTargetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setShowTargetModal(false)}
          />
          <div
            className="relative z-50 w-full max-w-md rounded-2xl p-6 shadow-2xl"
            style={{ background: "#fff" }}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold" style={{ color: "#0d1f10" }}>
                Configure Reduction Targets
              </h3>
              <button
                onClick={() => setShowTargetModal(false)}
                className="p-1 rounded-lg"
                style={{ color: "#94a3b8" }}
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <p className="text-xs mb-4" style={{ color: "#5a6b5a" }}>
              Configure your organization's baseline carbon year and targeted net-zero milestones.
            </p>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <label className="text-sm font-semibold w-32 shrink-0" style={{ color: "#0d1f10" }}>
                  Baseline Year
                </label>
                <input
                  type="number"
                  placeholder="e.g. 2023"
                  value={targetInputs.baseline_year}
                  onChange={(e) => setTargetInputs((p) => ({ ...p, baseline_year: e.target.value }))}
                  className="flex-1 px-3 py-2 rounded-xl text-sm border outline-none focus:ring-2 focus:ring-green-500"
                  style={{ border: "1px solid #d1e3d1" }}
                />
              </div>
              <div className="flex items-center gap-3">
                <label className="text-sm font-semibold w-32 shrink-0" style={{ color: "#0d1f10" }}>
                  Reduction Goal
                </label>
                <input
                  type="number"
                  placeholder="e.g. 20"
                  value={targetInputs.target_reduction_pct}
                  onChange={(e) => setTargetInputs((p) => ({ ...p, target_reduction_pct: e.target.value }))}
                  className="flex-1 px-3 py-2 rounded-xl text-sm border outline-none focus:ring-2 focus:ring-green-500"
                  style={{ border: "1px solid #d1e3d1" }}
                />
                <span className="text-xs shrink-0" style={{ color: "#8a9b8a" }}>
                  %
                </span>
              </div>
              <div className="flex items-center gap-3">
                <label className="text-sm font-semibold w-32 shrink-0" style={{ color: "#0d1f10" }}>
                  Net-Zero Year
                </label>
                <input
                  type="number"
                  placeholder="e.g. 2030"
                  value={targetInputs.net_zero_target_year}
                  onChange={(e) => setTargetInputs((p) => ({ ...p, net_zero_target_year: e.target.value }))}
                  className="flex-1 px-3 py-2 rounded-xl text-sm border outline-none focus:ring-2 focus:ring-green-500"
                  style={{ border: "1px solid #d1e3d1" }}
                />
              </div>
            </div>
            <div className="flex gap-2 mt-5">
              <button
                onClick={() => setShowTargetModal(false)}
                className="flex-1 py-2 rounded-xl text-sm font-semibold"
                style={{ background: "#f1f5f1", color: "#374151" }}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveTargets}
                disabled={targetMutation.isPending}
                className="flex-1 py-2 rounded-xl text-sm font-bold"
                style={{ background: "#2d7a4f", color: "#fff" }}
              >
                {targetMutation.isPending ? "Saving…" : "Save Targets"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
