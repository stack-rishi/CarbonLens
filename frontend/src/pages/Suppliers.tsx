import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useAuthStore } from "../store/useAuthStore";
import { Plus, Trash2, Award, Leaf, Loader2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "../components/ui/dialog";

interface Supplier {
  id: string; name: string; country: string; sector: string;
  emission_factor_kg_per_unit: number; esg_score: number;
  lat: number; lng: number; created_at: string;
}

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

function getEsgStyle(score: number): React.CSSProperties {
  if (score >= 80) return { background: "rgba(34,197,94,0.12)", color: "#16a34a", border: "1px solid rgba(34,197,94,0.25)" };
  if (score >= 60) return { background: "rgba(234,179,8,0.12)",  color: "#ca8a04", border: "1px solid rgba(234,179,8,0.25)" };
  return          { background: "rgba(239,68,68,0.12)",  color: "#dc2626", border: "1px solid rgba(239,68,68,0.25)" };
}

const FLAGS: Record<string, string> = {
  US: "🇺🇸", IN: "🇮🇳", DE: "🇩🇪", GB: "🇬🇧", JP: "🇯🇵",
  FR: "🇫🇷", CN: "🇨🇳", BR: "🇧🇷", AU: "🇦🇺", SG: "🇸🇬",
};

export default function Suppliers() {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const [open, setOpen] = useState(false);

  const [name,    setName]    = useState("");
  const [country, setCountry] = useState("IN");
  const [sector,  setSector]  = useState("");
  const [factor,  setFactor]  = useState("1.0");
  const [esg,     setEsg]     = useState("75");
  const [lat,     setLat]     = useState("20.0");
  const [lng,     setLng]     = useState("77.0");

  const { data: suppliers, isLoading } = useQuery<Supplier[]>({
    queryKey: ["suppliers"],
    queryFn: async () => (await api.get("/suppliers")).data,
  });

  const createMutation = useMutation({
    mutationFn: async (d: any) => (await api.post("/suppliers", d)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      setOpen(false);
      setName(""); setCountry("IN"); setSector(""); setFactor("1.0"); setEsg("75"); setLat("20.0"); setLng("77.0");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => api.delete(`/suppliers/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["suppliers"] }),
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate({
      name, country: country.substring(0, 2).toUpperCase(), sector,
      emission_factor_kg_per_unit: parseFloat(factor),
      esg_score: parseFloat(esg), lat: parseFloat(lat), lng: parseFloat(lng),
    });
  };

  const isAdmin   = user?.role === "admin";
  const isAnalyst = user?.role === "admin" || user?.role === "analyst";

  const leaders = [...(suppliers || [])].sort((a, b) => b.esg_score - a.esg_score).slice(0, 3);
  const cleanest = [...(suppliers || [])].sort((a, b) => a.emission_factor_kg_per_unit - b.emission_factor_kg_per_unit).slice(0, 3);

  return (
    <div className="space-y-5 pb-10">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "#0d1f10", letterSpacing: "-0.02em" }}>Suppliers Network</h1>
          <p className="text-sm mt-0.5" style={{ color: "#5a6b5a" }}>Audit ESG profiles and logistics parameters of value chain nodes</p>
        </div>
        {isAnalyst && (
          <button onClick={() => setOpen(true)} className="btn-primary gap-2">
            <Plus className="h-4 w-4" /> Add Supplier
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-48">
          <Loader2 className="h-7 w-7 animate-spin" style={{ color: "#2d7a4f" }} />
        </div>
      ) : (
        <div className="grid gap-5 lg:grid-cols-3">
          {/* Main table */}
          <div
            className="lg:col-span-2"
            style={{ background: "#e8f2e8", border: "1px solid #d1e3d1", borderRadius: 20, overflow: "hidden" }}
          >
            <div className="px-5 py-4 border-b" style={{ borderColor: "#d1e3d1" }}>
              <p className="text-sm font-semibold" style={{ color: "#0d1f10" }}>
                Tracked Suppliers
                <span className="ml-2 text-xs font-normal" style={{ color: "#5a6b5a" }}>
                  {suppliers?.length || 0} nodes
                </span>
              </p>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr style={{ background: "#eef5ee", borderBottom: "1px solid #d1e3d1" }}>
                  {["Supplier", "Country", "Sector", "ESG Index", "Intensity Factor", ...(isAdmin ? [""] : [])].map((h) => (
                    <th key={h} className="label-caps px-4 py-3 text-left">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {suppliers && suppliers.length > 0 ? suppliers.map((s) => (
                  <tr
                    key={s.id}
                    style={{ borderBottom: "1px solid rgba(209,227,209,0.5)", transition: "background 0.12s" }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "#eef5ee")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    <td className="px-4 py-3 font-semibold" style={{ color: "#0d1f10" }}>{s.name}</td>
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-1.5" style={{ color: "#2d3d2d" }}>
                        <span>{FLAGS[s.country] || "🏳️"}</span>
                        <span className="text-xs">{s.country}</span>
                      </span>
                    </td>
                    <td className="px-4 py-3 capitalize text-xs" style={{ color: "#5a6b5a" }}>{s.sector || "Unassigned"}</td>
                    <td className="px-4 py-3">
                      <span className="scope-badge" style={getEsgStyle(s.esg_score)}>{s.esg_score}</span>
                    </td>
                    <td className="px-4 py-3 text-xs font-mono" style={{ color: "#2d3d2d" }}>
                      {s.emission_factor_kg_per_unit?.toFixed(3)} kg/t
                    </td>
                    {isAdmin && (
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => confirm("Delete this supplier? This will cascade-delete linked edges.") && deleteMutation.mutate(s.id)}
                          className="p-1.5 rounded-lg"
                          style={{ color: "#8a9b8a", transition: "color 0.15s" }}
                          onMouseEnter={(e) => (e.currentTarget.style.color = "#dc2626")}
                          onMouseLeave={(e) => (e.currentTarget.style.color = "#8a9b8a")}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    )}
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={6} className="text-center py-14 text-sm" style={{ color: "#8a9b8a" }}>
                      No suppliers registered. Click 'Add Supplier' to create one.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Side cards */}
          <div className="space-y-4">
            {/* ESG Leaders */}
            <div style={{ background: "#e8f2e8", border: "1px solid #d1e3d1", borderRadius: 20, padding: "20px 24px" }}>
              <div className="flex items-center gap-2 mb-4">
                <div className="flex h-7 w-7 items-center justify-center rounded-xl" style={{ background: "rgba(45,122,79,0.15)" }}>
                  <Award style={{ width: 14, height: 14, color: "#2d7a4f" }} />
                </div>
                <p className="text-sm font-semibold" style={{ color: "#0d1f10" }}>Sustainability Leaders</p>
              </div>
              <div className="space-y-3">
                {leaders.length > 0 ? leaders.map((s, i) => (
                  <div key={s.id} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold w-4" style={{ color: "#8a9b8a" }}>{i + 1}</span>
                      <span className="text-sm font-medium" style={{ color: "#0d1f10" }}>{s.name}</span>
                    </div>
                    <span className="scope-badge" style={getEsgStyle(s.esg_score)}>{s.esg_score}</span>
                  </div>
                )) : <p className="text-xs" style={{ color: "#8a9b8a" }}>No leaders to report.</p>}
              </div>
            </div>

            {/* Carbon Intensities */}
            <div style={{ background: "#e8f2e8", border: "1px solid #d1e3d1", borderRadius: 20, padding: "20px 24px" }}>
              <div className="flex items-center gap-2 mb-4">
                <div className="flex h-7 w-7 items-center justify-center rounded-xl" style={{ background: "rgba(45,122,79,0.15)" }}>
                  <Leaf style={{ width: 14, height: 14, color: "#2d7a4f" }} />
                </div>
                <p className="text-sm font-semibold" style={{ color: "#0d1f10" }}>Carbon Intensities</p>
              </div>
              <div className="space-y-3">
                {cleanest.length > 0 ? cleanest.map((s) => (
                  <div key={s.id} className="flex items-center justify-between">
                    <span className="text-sm font-medium" style={{ color: "#0d1f10" }}>{s.name}</span>
                    <span className="text-xs font-mono font-semibold" style={{ color: "#2d7a4f" }}>
                      {s.emission_factor_kg_per_unit?.toFixed(2)} kg
                    </span>
                  </div>
                )) : <p className="text-xs" style={{ color: "#8a9b8a" }}>No data points logged.</p>}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add Supplier Dialog */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent style={{ background: "#f5f8f5", border: "1px solid #d1e3d1", borderRadius: 20, maxWidth: 520 }}>
          <DialogHeader>
            <DialogTitle style={{ color: "#0d1f10" }}>Register New Supplier</DialogTitle>
            <DialogDescription style={{ color: "#5a6b5a" }}>
              Specify company profile details, geographical tags, and initial carbon intensiveness.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate}>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <Field label="Supplier Name">
                  <input value={name} onChange={(e) => setName(e.target.value)} style={inputStyle} placeholder="Acme Logistics" required />
                </Field>
                <Field label="Country Code (2-char)">
                  <input value={country} onChange={(e) => setCountry(e.target.value)} style={inputStyle} placeholder="IN" maxLength={2} required />
                </Field>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Sector">
                  <input value={sector} onChange={(e) => setSector(e.target.value)} style={inputStyle} placeholder="Manufacturing" required />
                </Field>
                <Field label="ESG Score (0–100)">
                  <input type="number" min={0} max={100} value={esg} onChange={(e) => setEsg(e.target.value)} style={inputStyle} required />
                </Field>
              </div>
              <Field label="Emission Factor (kg CO₂e per unit)">
                <input type="number" step="0.00001" value={factor} onChange={(e) => setFactor(e.target.value)} style={inputStyle} required />
              </Field>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Latitude">
                  <input type="number" step="0.0001" value={lat} onChange={(e) => setLat(e.target.value)} style={inputStyle} required />
                </Field>
                <Field label="Longitude">
                  <input type="number" step="0.0001" value={lng} onChange={(e) => setLng(e.target.value)} style={inputStyle} required />
                </Field>
              </div>
            </div>
            <DialogFooter className="gap-2">
              <button type="button" onClick={() => setOpen(false)} className="btn-ghost text-sm py-2 px-5">Cancel</button>
              <button type="submit" disabled={createMutation.isPending} className="btn-primary text-sm py-2 px-6">
                {createMutation.isPending ? <><Loader2 className="h-4 w-4 animate-spin" /> Saving…</> : "Save Supplier"}
              </button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
