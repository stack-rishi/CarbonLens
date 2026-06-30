import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Tabs, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Skeleton } from "../components/ui/skeleton";
import { useToast } from "../hooks/use-toast";
import { StatCard } from "../components/StatCard";
import { ComplianceGauge } from "../components/ComplianceGauge";
import { Factory, Zap, Globe, BarChart3, Activity, TrendingDown, Shield } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  BarChart,
  Bar,
} from "recharts";
import { Link, useNavigate } from "react-router-dom";

const CHART_TOOLTIP_STYLE = {
  background: "#0d1a0f",
  border: "1px solid rgba(255,255,255,0.10)",
  borderRadius: "12px",
  color: "#e8f2e8",
  fontSize: "13px",
};

export default function Dashboard() {
  const [period, setPeriod] = useState("12m");
  const { toast } = useToast();
  const navigate = useNavigate();

  const getPeriodDays = () => {
    if (period === "1m") return 30;
    if (period === "3m") return 90;
    if (period === "6m") return 180;
    return 365;
  };

  const getDateRange = () => {
    const start = new Date();
    start.setDate(start.getDate() - getPeriodDays());
    return {
      start_date: start.toISOString().split("T")[0],
      end_date: new Date().toISOString().split("T")[0],
    };
  };

  const { data: summary, isLoading: isSummaryLoading, isError: isSummaryError } = useQuery({
    queryKey: ["emissions-summary", period],
    queryFn: async () => {
      const res = await api.get("/emissions/summary", { params: getDateRange() });
      return res.data;
    },
    refetchInterval: 60000,
  });

  const { data: trendData, isLoading: isTrendLoading } = useQuery({
    queryKey: ["emissions-trend", period],
    queryFn: async () => {
      const res = await api.get("/emissions/trend", { params: getDateRange() });
      return res.data.trend;
    },
    refetchInterval: 60000,
  });

  const { data: recentActivity, isLoading: isActivityLoading } = useQuery({
    queryKey: ["emissions-recent"],
    queryFn: async () => {
      const res = await api.get("/emissions", { params: { limit: 5 } });
      return res.data;
    },
    refetchInterval: 60000,
  });

  const { data: complianceStatus } = useQuery({
    queryKey: ["compliance-status"],
    queryFn: async () => {
      const res = await api.get("/compliance/status");
      return res.data;
    },
    refetchInterval: 15000,
    retry: false,
  });

  React.useEffect(() => {
    if (isSummaryError) {
      toast({ title: "Error fetching dashboard data", description: "Please check your connection.", variant: "destructive" });
    }
  }, [isSummaryError, toast]);

  const isLoading = isSummaryLoading || isTrendLoading || isActivityLoading;

  const scope1 = summary?.by_scope?.["1"] || 0;
  const scope2 = summary?.by_scope?.["2"] || 0;
  const scope3 = summary?.by_scope?.["3"] || 0;
  const total  = summary?.total_tco2e || 0;

  const pieData = [
    { name: "Scope 1", value: scope1, color: "#ef4444" },
    { name: "Scope 2", value: scope2, color: "#f97316" },
    { name: "Scope 3", value: scope3, color: "#eab308" },
  ].filter((d) => d.value > 0);

  const topSuppliers = summary?.by_supplier
    ? Object.entries(summary.by_supplier)
        .map(([name, val]) => ({ name, value: Number(val) }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 5)
    : [];

  const baseline = 50000;
  const target   = baseline * 0.8;
  const progressPct = Math.min(100, Math.max(0, ((baseline - total) / (baseline - target)) * 100));

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <Skeleton className="h-9 w-48 rounded-xl" style={{ background: "#d1e3d1" }} />
          <Skeleton className="h-9 w-56 rounded-pill" style={{ background: "#d1e3d1" }} />
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[0,1,2,3].map(i => (
            <Skeleton key={i} className="h-28 w-full rounded-xl" style={{ background: "#d1e3d1" }} />
          ))}
        </div>
        <Skeleton className="h-80 w-full rounded-xl" style={{ background: "#d1e3d1" }} />
      </div>
    );
  }

  return (
    <div className="space-y-5 pb-10">
      {/* ── Header ───────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "#0d1f10", letterSpacing: "-0.02em" }}>
            Emissions Overview
          </h1>
          <p className="text-sm mt-0.5" style={{ color: "#5a6b5a" }}>
            Real-time GHG tracking across your supply chain
          </p>
        </div>
        {/* Period tabs — pill style (Meta pattern) */}
        <Tabs value={period} onValueChange={setPeriod}>
          <TabsList
            className="p-1 gap-0.5"
            style={{
              background: "#e8f2e8",
              border: "1px solid #d1e3d1",
              borderRadius: "9999px",
            }}
          >
            {["1m", "3m", "6m", "12m"].map((p) => (
              <TabsTrigger
                key={p}
                value={p}
                style={{
                  borderRadius: "9999px",
                  fontSize: "13px",
                  fontWeight: 600,
                  padding: "5px 14px",
                }}
                className="data-[state=active]:bg-forest data-[state=active]:text-white data-[state=active]:shadow-none text-ink-muted"
              >
                {p}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      {/* ── KPI Cards ────────────────────────────────── */}
      <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Scope 1 — Direct"
          value={scope1.toFixed(1)}
          icon={Factory}
          iconBg="rgba(239,68,68,0.12)"
          iconColor="#dc2626"
          accent="#dc2626"
        />
        <StatCard
          title="Scope 2 — Energy"
          value={scope2.toFixed(1)}
          icon={Zap}
          iconBg="rgba(249,115,22,0.12)"
          iconColor="#ea580c"
          accent="#ea580c"
        />
        <StatCard
          title="Scope 3 — Supply Chain"
          value={scope3.toFixed(1)}
          icon={Globe}
          iconBg="rgba(234,179,8,0.12)"
          iconColor="#ca8a04"
          accent="#ca8a04"
        />
        <StatCard
          title="Total All Scopes"
          value={total.toFixed(1)}
          icon={BarChart3}
          iconBg="rgba(45,122,79,0.15)"
          iconColor="#2d7a4f"
          accent="#2d7a4f"
        />
      </div>

      {/* ── Compliance Status Widget ──────────────────── */}
      {complianceStatus && (
        <Link
          to="/compliance"
          className="block card hover:shadow-md transition-shadow cursor-pointer"
          style={{ border: "1px solid #d1e3d1" }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div
                className="h-10 w-10 rounded-xl flex items-center justify-center"
                style={{ background: "rgba(45,122,79,0.12)" }}
              >
                <Shield className="h-5 w-5" style={{ color: "#2d7a4f" }} />
              </div>
              <div>
                <p className="text-sm font-semibold" style={{ color: "#0d1f10" }}>
                  Compliance Status
                </p>
                <p className="text-xs" style={{ color: "#5a6b5a" }}>
                  Click to view full compliance monitor →
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-xs font-medium" style={{ color: "#8a9b8a" }}>
                  Sustainability Score
                </p>
                <p
                  className="text-xl font-bold"
                  style={{
                    color:
                      complianceStatus.sustainability_score >= 70
                        ? "#22c55e"
                        : complianceStatus.sustainability_score >= 50
                        ? "#eab308"
                        : "#ef4444",
                  }}
                >
                  {Math.round(complianceStatus.sustainability_score)}/100
                </p>
              </div>
              <div style={{ width: 100, height: 80 }}>
                <ComplianceGauge
                  percentage={complianceStatus.compliance_pct}
                  status={complianceStatus.status}
                />
              </div>
            </div>
          </div>
        </Link>
      )}

      {/* ── Charts Row ───────────────────────────────── */}
      <div className="grid gap-4 md:grid-cols-5">
        {/* Area Chart — dark card */}
        <div className="md:col-span-3 card-dark">
          <p className="text-sm font-semibold mb-4" style={{ color: "#e8f2e8" }}>Monthly Emissions Trend</p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#ef4444" stopOpacity={0.5} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0.05} />
                  </linearGradient>
                  <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#f97316" stopOpacity={0.5} />
                    <stop offset="95%" stopColor="#f97316" stopOpacity={0.05} />
                  </linearGradient>
                  <linearGradient id="g3" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#eab308" stopOpacity={0.5} />
                    <stop offset="95%" stopColor="#eab308" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="month" stroke="#5a7a5a" fontSize={11} />
                <YAxis stroke="#5a7a5a" fontSize={11} />
                <Tooltip contentStyle={CHART_TOOLTIP_STYLE} labelStyle={{ color: "#e8f2e8" }} />
                <Legend wrapperStyle={{ color: "#8ea58e", fontSize: 12 }} />
                <Area type="monotone" dataKey="scope_1" name="Scope 1" stackId="1" stroke="#ef4444" fill="url(#g1)" strokeWidth={1.5} />
                <Area type="monotone" dataKey="scope_2" name="Scope 2" stackId="1" stroke="#f97316" fill="url(#g2)" strokeWidth={1.5} />
                <Area type="monotone" dataKey="scope_3" name="Scope 3" stackId="1" stroke="#eab308" fill="url(#g3)" strokeWidth={1.5} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Donut — dark card */}
        <div className="md:col-span-2 card-dark flex flex-col">
          <p className="text-sm font-semibold mb-4" style={{ color: "#e8f2e8" }}>Scope Distribution</p>
          <div className="flex-1 relative min-h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={90}
                  paddingAngle={4}
                  dataKey="value"
                  strokeWidth={0}
                >
                  {pieData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} opacity={0.85} />
                  ))}
                </Pie>
                <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
                <Legend wrapperStyle={{ color: "#8ea58e", fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
            {/* Center label */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none pb-8">
              <span
                className="text-2xl font-bold"
                style={{ color: "#e8f2e8", fontVariantNumeric: "tabular-nums", letterSpacing: "-0.02em" }}
              >
                {total.toFixed(0)}
              </span>
              <span className="text-xs mt-0.5" style={{ color: "#5a7a5a" }}>tCO2e total</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Bottom Row ───────────────────────────────── */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Top Suppliers Bar */}
        <div className="card-dark">
          <p className="text-sm font-semibold mb-4" style={{ color: "#e8f2e8" }}>Top Emitting Suppliers</p>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topSuppliers} layout="vertical" margin={{ top: 0, left: 20, right: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
                <XAxis type="number" stroke="#5a7a5a" fontSize={11} />
                <YAxis dataKey="name" type="category" stroke="#5a7a5a" fontSize={11} width={90} />
                <Tooltip
                  cursor={{ fill: "rgba(255,255,255,0.04)" }}
                  contentStyle={CHART_TOOLTIP_STYLE}
                />
                <Bar
                  dataKey="value"
                  name="tCO2e"
                  radius={[0, 6, 6, 0]}
                  onClick={(d) => navigate(`/supply-chain?supplier=${d.name}`)}
                  className="cursor-pointer"
                >
                  {topSuppliers.map((entry, i) => (
                    <Cell
                      key={i}
                      fill={(entry.value / (total || 1)) > 0.2 ? "#ef4444" : "#2d7a4f"}
                      opacity={0.85}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-semibold" style={{ color: "#0d1f10" }}>Recent Activity</p>
            <Link
              to="/emissions"
              className="text-xs font-semibold"
              style={{ color: "#2d7a4f" }}
            >
              View all →
            </Link>
          </div>
          <div className="space-y-2">
            {recentActivity?.map((record: any) => (
              <div
                key={record.id}
                className="flex items-center justify-between p-3 rounded-xl transition-colors"
                style={{ background: "#eef5ee", border: "1px solid #d1e3d1" }}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="h-8 w-8 rounded-full flex items-center justify-center shrink-0"
                    style={{ background: "rgba(45,122,79,0.12)" }}
                  >
                    <Activity style={{ width: 14, height: 14, color: "#2d7a4f" }} />
                  </div>
                  <div>
                    <p className="text-sm font-medium" style={{ color: "#0d1f10" }}>
                      {record.supplier?.name || "Internal Org"}
                    </p>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span
                        className="scope-badge"
                        style={
                          record.scope === "1" ? { background: "rgba(239,68,68,0.12)", color: "#dc2626" }
                          : record.scope === "2" ? { background: "rgba(249,115,22,0.12)", color: "#ea580c" }
                          : { background: "rgba(234,179,8,0.12)", color: "#ca8a04" }
                        }
                      >
                        Scope {record.scope}
                      </span>
                      <span className="text-[11px]" style={{ color: "#8a9b8a" }}>
                        {record.period_start}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <p
                    className="text-sm font-bold"
                    style={{ color: "#0d1f10", fontVariantNumeric: "tabular-nums" }}
                  >
                    {(record.amount_tco2e || 0).toFixed(1)}
                  </p>
                  <p className="text-[10px]" style={{ color: "#8a9b8a" }}>tCO2e</p>
                </div>
              </div>
            ))}
            {!recentActivity?.length && (
              <div className="text-center py-8 text-sm" style={{ color: "#8a9b8a" }}>
                No recent activity logged.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Reduction Target ─────────────────────────── */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <TrendingDown style={{ width: 16, height: 16, color: "#2d7a4f" }} />
          <p className="text-sm font-semibold" style={{ color: "#0d1f10" }}>Net Zero Reduction Target</p>
          <span
            className="ml-auto text-xs font-bold px-3 py-1"
            style={{ background: "rgba(45,122,79,0.12)", color: "#2d7a4f", borderRadius: 9999 }}
          >
            −20% goal
          </span>
        </div>

        <div className="flex items-end justify-between mb-3">
          <div>
            <p className="label-caps mb-0.5">Baseline (2023)</p>
            <p
              className="text-xl font-bold"
              style={{ color: "#0d1f10", letterSpacing: "-0.02em", fontVariantNumeric: "tabular-nums" }}
            >
              {baseline.toLocaleString()} tCO2e
            </p>
          </div>
          <div className="text-center">
            <p className="label-caps mb-0.5">Current</p>
            <p
              className="text-xl font-bold"
              style={{ color: "#2d7a4f", letterSpacing: "-0.02em", fontVariantNumeric: "tabular-nums" }}
            >
              {total.toFixed(0)} tCO2e
            </p>
          </div>
          <div className="text-right">
            <p className="label-caps mb-0.5">Target</p>
            <p
              className="text-xl font-bold"
              style={{ color: "#1f5e3a", letterSpacing: "-0.02em", fontVariantNumeric: "tabular-nums" }}
            >
              {target.toLocaleString()} tCO2e
            </p>
          </div>
        </div>

        <div className="progress-track">
          <div
            className="progress-fill"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <p className="text-xs mt-2 text-center" style={{ color: "#8a9b8a" }}>
          {progressPct.toFixed(0)}% of reduction achieved — estimated target by{" "}
          <span className="font-semibold" style={{ color: "#0d1f10" }}>Q4 2027</span>
        </p>
      </div>
    </div>
  );
}
