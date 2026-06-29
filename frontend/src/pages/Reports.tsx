import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { FileText, Download, Eye, RefreshCw, Loader2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { formatDistanceToNow, format } from "date-fns";

interface Report {
  id: string; period_start: string; period_end: string; s3_url: string | null;
  status: "pending" | "processing" | "done" | "failed"; created_at: string;
}

const inputStyle: React.CSSProperties = {
  background: "#eef5ee", border: "1px solid #d1e3d1", borderRadius: 12,
  padding: "9px 13px", fontSize: 14, color: "#0d1f10", width: "100%", outline: "none",
};

export default function Reports() {
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const currentYearStart = `${new Date().getFullYear()}-01-01`;
  const today = new Date().toISOString().split('T')[0];
  const [start, setStart] = useState(currentYearStart);
  const [end, setEnd] = useState(today);
  const [reportType, setReportType] = useState("full");
  const [sections, setSections] = useState({ scope: true, supplier: true, monthly: true, methodology: true });
  const [error, setError] = useState<string | null>(null);

  const { data: reports, isLoading } = useQuery<Report[]>({
    queryKey: ["reports"],
    queryFn: async () => (await api.get("/reports")).data,
    refetchInterval: (q) => (q.state.data as Report[] | undefined)?.some(r => r.status === "pending" || r.status === "processing") ? 3000 : false,
  });

  const generateMutation = useMutation({
    mutationFn: async (payload: any) => (await api.post("/reports", payload)).data,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["reports"] }); setModalOpen(false); },
    onError: (err: any) => setError(err.response?.data?.detail || "Failed to generate report."),
  });

  const handleGenerate = (e: React.FormEvent) => {
    e.preventDefault();
    if (new Date(start) > new Date(end)) return setError("Start date cannot be after end date.");
    generateMutation.mutate({ period_start: start, period_end: end, report_type: reportType, sections });
  };

  const handleRetry = (period_start: string, period_end: string) => {
    generateMutation.mutate({ period_start, period_end, report_type: "full", sections: { scope: true, supplier: true, monthly: true, methodology: true } });
  };

  const downloadPdf = (relativeUrl: string) => {
    const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8080/api/v1";
    window.open(`${baseUrl.replace("/api/v1", "")}${relativeUrl}`, "_blank");
  };

  const hasProcessing = reports?.some(r => r.status === "pending" || r.status === "processing");

  return (
    <div className="space-y-5 pb-10">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "#0d1f10", letterSpacing: "-0.02em" }}>Reports</h1>
          <p className="text-sm mt-0.5" style={{ color: "#5a6b5a" }}>GHG Protocol aligned PDF reports</p>
        </div>
        <button onClick={() => setModalOpen(true)} className="btn-primary gap-2">
          <FileText className="h-4 w-4" /> Generate New Report
        </button>
      </div>

      {hasProcessing && (
        <div className="flex items-center gap-3 p-4 rounded-xl" style={{ background: "rgba(45,122,79,0.1)", border: "1px solid rgba(45,122,79,0.2)" }}>
          <Loader2 className="h-4 w-4 animate-spin" style={{ color: "#2d7a4f" }} />
          <p className="text-sm font-semibold" style={{ color: "#1f5e3a" }}>Report generating... This usually takes 30-60 seconds.</p>
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center items-center h-48">
          <Loader2 className="h-7 w-7 animate-spin" style={{ color: "#2d7a4f" }} />
        </div>
      ) : !reports || reports.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-16 text-center space-y-4" style={{ background: "#e8f2e8", border: "1px solid #d1e3d1", borderRadius: 20 }}>
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl" style={{ background: "rgba(45,122,79,0.1)" }}>
            <FileText style={{ width: 28, height: 28, color: "#2d7a4f" }} />
          </div>
          <div>
            <h3 className="text-base font-semibold" style={{ color: "#0d1f10" }}>No reports yet</h3>
            <p className="text-sm mt-1" style={{ color: "#5a6b5a" }}>Generate your first sustainability report to get started.</p>
          </div>
          <button onClick={() => setModalOpen(true)} className="btn-ghost">Generate Report</button>
        </div>
      ) : (
        <div style={{ background: "#e8f2e8", border: "1px solid #d1e3d1", borderRadius: 20, overflow: "hidden" }}>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: "#eef5ee", borderBottom: "1px solid #d1e3d1" }}>
                {["Period", "Generated", "Status", "Actions"].map((h) => (
                  <th key={h} className="label-caps px-4 py-3 text-left last:text-right">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {reports.map((r) => {
                const startStr = format(new Date(r.period_start), "MMM yyyy");
                const endStr = format(new Date(r.period_end), "MMM yyyy");
                return (
                  <tr key={r.id} style={{ borderBottom: "1px solid rgba(209,227,209,0.5)", transition: "background 0.12s" }} onMouseEnter={e => e.currentTarget.style.background = "#eef5ee"} onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                    <td className="px-4 py-3 font-semibold" style={{ color: "#0d1f10" }}>{startStr} – {endStr}</td>
                    <td className="px-4 py-3 text-xs" style={{ color: "#5a6b5a" }}>{formatDistanceToNow(new Date(r.created_at), { addSuffix: true })}</td>
                    <td className="px-4 py-3">
                      {r.status === "done" && <span className="scope-badge" style={{ background: "rgba(34,197,94,0.12)", color: "#16a34a", border: "1px solid rgba(34,197,94,0.25)" }}>Ready</span>}
                      {r.status === "failed" && <span className="scope-badge" style={{ background: "rgba(239,68,68,0.12)", color: "#dc2626", border: "1px solid rgba(239,68,68,0.25)" }}>Failed</span>}
                      {(r.status === "pending" || r.status === "processing") && <span className="scope-badge" style={{ background: "rgba(59,130,246,0.12)", color: "#2563eb", border: "1px solid rgba(59,130,246,0.25)" }}><Loader2 className="h-3 w-3 animate-spin mr-1 inline" /> Processing</span>}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {r.status === "done" && (
                        <div className="flex items-center justify-end gap-2">
                          <button onClick={() => r.s3_url && downloadPdf(r.s3_url)} className="btn-ghost py-1.5 px-3 text-xs gap-1.5">
                            <Download className="h-3 w-3" /> Download PDF
                          </button>
                          <button onClick={() => r.s3_url && downloadPdf(r.s3_url)} className="p-1.5 rounded-lg text-[#5a6b5a] hover:text-[#0d1f10] hover:bg-black/5">
                            <Eye className="h-4 w-4" />
                          </button>
                        </div>
                      )}
                      {r.status === "failed" && (
                        <button onClick={() => handleRetry(r.period_start, r.period_end)} className="btn-ghost py-1.5 px-3 text-xs gap-1.5 !text-red-600 !border-red-200">
                          <RefreshCw className="h-3 w-3" /> Retry
                        </button>
                      )}
                      {(r.status === "pending" || r.status === "processing") && (
                        <span className="text-xs text-[#8a9b8a]">Preparing...</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent style={{ background: "#f5f8f5", border: "1px solid #d1e3d1", borderRadius: 20, maxWidth: 440 }}>
          <DialogHeader>
            <DialogTitle style={{ color: "#0d1f10" }}>Generate Sustainability Report</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleGenerate} className="space-y-5 py-2">
            {error && <div className="p-3 text-sm rounded-xl" style={{ background: "rgba(239,68,68,0.08)", color: "#dc2626" }}>{error}</div>}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="label-caps">Period Start</label>
                <input type="date" value={start} onChange={e => setStart(e.target.value)} style={inputStyle} required />
              </div>
              <div className="space-y-1.5">
                <label className="label-caps">Period End</label>
                <input type="date" value={end} onChange={e => setEnd(e.target.value)} style={inputStyle} required />
              </div>
            </div>
            <div className="space-y-2">
              <label className="label-caps">Report Type</label>
              <div className="flex gap-2 p-1" style={{ background: "#e8f2e8", borderRadius: 9999, border: "1px solid #d1e3d1" }}>
                {[ { id: "full", l: "Full Report" }, { id: "summary", l: "Summary" } ].map(t => (
                  <button key={t.id} type="button" onClick={() => setReportType(t.id)} className="flex-1 py-1.5 text-xs font-semibold transition-all" style={{ borderRadius: 9999, background: reportType === t.id ? "#2d7a4f" : "transparent", color: reportType === t.id ? "#fff" : "#5a6b5a" }}>
                    {t.l}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <label className="label-caps">Include Sections</label>
              <div className="space-y-2 text-sm" style={{ color: "#2d3d2d" }}>
                {[ { id: "scope", l: "Scope breakdown" }, { id: "supplier", l: "Supplier analysis" }, { id: "monthly", l: "Monthly trends" }, { id: "methodology", l: "Methodology notes" } ].map(s => (
                  <label key={s.id} className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={(sections as any)[s.id]} onChange={e => setSections({...sections, [s.id]: e.target.checked})} className="accent-[#2d7a4f] h-4 w-4" />
                    {s.l}
                  </label>
                ))}
              </div>
            </div>
            <div className="pt-2">
              <button type="submit" disabled={generateMutation.isPending} className="w-full btn-primary py-2.5">
                {generateMutation.isPending ? <><Loader2 className="mr-2 h-4 w-4 animate-spin inline" /> Generating...</> : "Generate Report"}
              </button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
