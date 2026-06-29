import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useAuthStore } from "../store/useAuthStore";
import { Plus, Trash2, Calendar, FileDown, SlidersHorizontal, Database, Loader2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "../components/ui/dialog";

interface EmissionRecord {
  id: string;
  supplier_id: string | null;
  scope: string;
  category: string;
  amount_tco2e: number;
  period_start: string;
  period_end: string;
  source: string;
  created_at: string;
}
interface Supplier { id: string; name: string; }

const inputStyle: React.CSSProperties = {
  background: "#eef5ee", border: "1px solid #d1e3d1", borderRadius: 12,
  padding: "9px 13px", fontSize: 14, color: "#0d1f10", width: "100%", outline: "none",
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="label-caps">{label}</label>
      {children}
    </div>
  );
}

const SCOPE_STYLES: Record<string, React.CSSProperties> = {
  "1": { background: "rgba(239,68,68,0.10)", color: "#dc2626", border: "1px solid rgba(239,68,68,0.22)" },
  "2": { background: "rgba(249,115,22,0.10)", color: "#ea580c", border: "1px solid rgba(249,115,22,0.22)" },
  "3": { background: "rgba(234,179,8,0.10)",  color: "#ca8a04", border: "1px solid rgba(234,179,8,0.22)" },
};

export default function Emissions() {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const [startDate, setStartDate] = useState("");
  const [endDate,   setEndDate]   = useState("");
  const [open, setOpen] = useState(false);

  // Form
  const [supplierId, setSupplierId] = useState("");
  const [scope,      setScope]      = useState("1");
  const [category,   setCategory]   = useState("Stationary Combustion");
  const [amount,     setAmount]     = useState("15.5");
  const [pStart,     setPStart]     = useState("");
  const [pEnd,       setPEnd]       = useState("");
  const [source,     setSource]     = useState("manual");

  const { data: suppliers } = useQuery<Supplier[]>({
    queryKey: ["suppliers-dropdown"],
    queryFn: async () => (await api.get("/suppliers")).data,
  });

  const { data: records, isLoading } = useQuery<EmissionRecord[]>({
    queryKey: ["emissions", startDate, endDate],
    queryFn: async () => {
      const params: any = {};
      if (startDate) params.start_date = startDate;
      if (endDate)   params.end_date   = endDate;
      return (await api.get("/emissions", { params })).data;
    },
  });

  const createMutation = useMutation({
    mutationFn: async (d: any) => (await api.post("/emissions", d)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["emissions"] });
      setOpen(false);
      setSupplierId(""); setScope("1"); setCategory("Stationary Combustion");
      setAmount("15.5"); setPStart(""); setPEnd(""); setSource("manual");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => api.delete(`/emissions/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["emissions"] }),
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate({ supplier_id: supplierId || null, scope, category, amount_tco2e: parseFloat(amount), period_start: pStart, period_end: pEnd, source });
  };

  const isAdmin   = user?.role === "admin";
  const isAnalyst = user?.role === "admin" || user?.role === "analyst";

  const totalShown = records?.reduce((s, r) => s + r.amount_tco2e, 0) ?? 0;

  return (
    <div className="space-y-5 pb-10">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "#0d1f10", letterSpacing: "-0.02em" }}>Emissions Ledger</h1>
          <p className="text-sm mt-0.5" style={{ color: "#5a6b5a" }}>Log and audit Scope 1, 2 & 3 footprint entries</p>
        </div>
        {isAnalyst && (
          <button onClick={() => setOpen(true)} className="btn-primary gap-2">
            <Plus className="h-4 w-4" /> Add Entry
          </button>
        )}
      </div>

      {/* Filter bar */}
      <div
        className="flex flex-wrap items-center gap-3 p-4 justify-between"
        style={{ background: "#e8f2e8", border: "1px solid #d1e3d1", borderRadius: 16 }}
      >
        <div className="flex flex-wrap gap-3 items-center">
          <SlidersHorizontal style={{ width: 15, height: 15, color: "#2d7a4f" }} />
          <div className="flex items-center gap-2">
            <span className="label-caps">From</span>
            <input type="date" style={inputStyle} value={startDate} onChange={(e) => setStartDate(e.target.value)} className="w-36" />
          </div>
          <div className="flex items-center gap-2">
            <span className="label-caps">To</span>
            <input type="date" style={inputStyle} value={endDate} onChange={(e) => setEndDate(e.target.value)} className="w-36" />
          </div>
          {(startDate || endDate) && (
            <button
              onClick={() => { setStartDate(""); setEndDate(""); }}
              className="text-xs font-semibold px-3 py-1.5"
              style={{ borderRadius: 9999, color: "#dc2626", background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.18)" }}
            >
              Clear
            </button>
          )}
        </div>
        <div className="flex items-center gap-3">
          {records?.length ? (
            <span className="text-xs font-semibold" style={{ color: "#2d7a4f" }}>
              {records.length} entries · {totalShown.toFixed(1)} tCO2e
            </span>
          ) : null}
          <button className="btn-ghost text-sm gap-1.5 py-2 px-4">
            <FileDown className="h-4 w-4" /> Export CSV
          </button>
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex justify-center items-center h-48">
          <Loader2 className="h-7 w-7 animate-spin" style={{ color: "#2d7a4f" }} />
        </div>
      ) : (
        <div style={{ background: "#e8f2e8", border: "1px solid #d1e3d1", borderRadius: 20, overflow: "hidden" }}>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: "1px solid #d1e3d1", background: "#eef5ee" }}>
                {["Period", "Scope", "Category", "Supplier Node", "Source", "Emissions (tCO2e)", ...(isAdmin ? [""] : [])].map((h) => (
                  <th key={h} className="label-caps px-4 py-3 text-left font-semibold last:text-right">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {records && records.length > 0 ? records.map((r, i) => {
                const sName = suppliers?.find((s) => s.id === r.supplier_id)?.name || "Corporate (Internal)";
                return (
                  <tr
                    key={r.id}
                    style={{ borderBottom: "1px solid rgba(209,227,209,0.5)", transition: "background 0.12s" }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "#eef5ee")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                    className={i % 2 === 0 ? "" : ""}
                  >
                    <td className="px-4 py-3" style={{ color: "#2d3d2d" }}>
                      <span className="flex items-center gap-1.5">
                        <Calendar style={{ width: 12, height: 12, color: "#8a9b8a" }} />
                        {r.period_start} → {r.period_end}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="scope-badge" style={SCOPE_STYLES[r.scope] || {}}>Scope {r.scope}</span>
                    </td>
                    <td className="px-4 py-3 capitalize" style={{ color: "#2d3d2d" }}>{r.category || "General"}</td>
                    <td className="px-4 py-3 font-medium" style={{ color: "#0d1f10" }}>{sName}</td>
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-1" style={{ color: "#5a6b5a" }}>
                        <Database style={{ width: 11, height: 11 }} />
                        <span className="capitalize text-xs">{r.source}</span>
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-bold" style={{ color: "#0d1f10", fontVariantNumeric: "tabular-nums" }}>
                      {r.amount_tco2e.toFixed(2)}
                    </td>
                    {isAdmin && (
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => confirm("Delete this record?") && deleteMutation.mutate(r.id)}
                          className="p-1.5 rounded-lg transition-colors"
                          style={{ color: "#8a9b8a" }}
                          onMouseEnter={(e) => (e.currentTarget.style.color = "#dc2626")}
                          onMouseLeave={(e) => (e.currentTarget.style.color = "#8a9b8a")}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    )}
                  </tr>
                );
              }) : (
                <tr>
                  <td colSpan={7} className="text-center py-14" style={{ color: "#8a9b8a" }}>
                    No emission records match your filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Add dialog */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent style={{ background: "#f5f8f5", border: "1px solid #d1e3d1", borderRadius: 20, maxWidth: 520 }}>
          <DialogHeader>
            <DialogTitle style={{ color: "#0d1f10" }}>Log New Emission Entry</DialogTitle>
            <DialogDescription style={{ color: "#5a6b5a" }}>
              Input carbon audit metrics from utility bills, freight logs, or supplier declarations.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate}>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <Field label="Audited Scope">
                  <select value={scope} onChange={(e) => setScope(e.target.value)} style={inputStyle}>
                    <option value="1">Scope 1 — Direct combustion</option>
                    <option value="2">Scope 2 — Electricity grid</option>
                    <option value="3">Scope 3 — Suppliers & logistics</option>
                  </select>
                </Field>
                <Field label="Supplier Association">
                  <select value={supplierId} onChange={(e) => setSupplierId(e.target.value)} style={inputStyle}>
                    <option value="">None (Internal Corporate)</option>
                    {suppliers?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </Field>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Category">
                  <input value={category} onChange={(e) => setCategory(e.target.value)} style={inputStyle} placeholder="Electricity bill" required />
                </Field>
                <Field label="Amount (tCO2e)">
                  <input type="number" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} style={inputStyle} required />
                </Field>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Period Start">
                  <input type="date" value={pStart} onChange={(e) => setPStart(e.target.value)} style={inputStyle} required />
                </Field>
                <Field label="Period End">
                  <input type="date" value={pEnd} onChange={(e) => setPEnd(e.target.value)} style={inputStyle} required />
                </Field>
              </div>
              <Field label="Data Source">
                <select value={source} onChange={(e) => setSource(e.target.value)} style={inputStyle}>
                  <option value="manual">Manual Form Input</option>
                  <option value="automatic_erp">ERP Database Sync</option>
                  <option value="utility_api">Utility Provider API</option>
                </select>
              </Field>
            </div>
            <DialogFooter className="gap-2">
              <button type="button" onClick={() => setOpen(false)} className="btn-ghost text-sm py-2 px-5">Cancel</button>
              <button type="submit" disabled={createMutation.isPending} className="btn-primary text-sm py-2 px-6">
                {createMutation.isPending ? <><Loader2 className="h-4 w-4 animate-spin" /> Saving…</> : "Log Entry"}
              </button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
