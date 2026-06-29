import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { Leaf, ChevronRight, ChevronLeft, Check, Plus, Trash2 } from "lucide-react";
import confetti from "canvas-confetti";

const SECTORS = ["Manufacturing", "Logistics", "Retail", "Technology", "Energy", "Agriculture", "Finance", "Other"];
const COUNTRIES = [ { code: "IN", name: "India" }, { code: "US", name: "United States" }, { code: "GB", name: "United Kingdom" }, { code: "DE", name: "Germany" }, { code: "SG", name: "Singapore" } ];
const REVENUE = ["<$1M", "$1M–$10M", "$10M–$100M", "$100M+"];
const BASELINE = ["2020", "2021", "2022", "2023", "2024"];
const NET_ZERO = ["2030", "2035", "2040", "2050", "Not yet"];
const STDS = ["GHG Protocol", "CDP", "GRI", "TCFD"];

const inputStyle: React.CSSProperties = {
  background: "#e8f2e8", border: "1px solid #d1e3d1", borderRadius: 12, padding: "10px 14px", fontSize: 14, color: "#0d1f10", width: "100%", outline: "none", transition: "all 0.2s"
};

export default function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);

  const [org, setOrg] = useState(localStorage.getItem("onb_org") || "");
  const [ind, setInd] = useState("Manufacturing");
  const [country, setCountry] = useState("IN");
  const [rev, setRev] = useState("<$1M");
  const [concern, setConcern] = useState("all");

  const [sups, setSups] = useState([{ name: "", country: "IN", sector: "Manufacturing", esg: "" }]);

  const [baseYear, setBaseYear] = useState("2023");
  const [target, setTarget] = useState(20);
  const [netZ, setNetZ] = useState("2050");
  const [stds, setStds] = useState(["GHG Protocol"]);

  const handle1 = () => { localStorage.setItem("onb_org", org); setStep(2); };
  const handle2 = async (skip = false) => {
    if (!skip) {
      const valid = sups.filter(s => s.name.trim());
      if (valid.length) {
        setLoading(true);
        for (const s of valid) await api.post("/suppliers", { name: s.name, country: s.country, sector: s.sector, esg_score: s.esg ? parseFloat(s.esg) : null }).catch(() => {});
        setLoading(false);
      }
    }
    setStep(3);
  };
  const handle3 = () => {
    localStorage.setItem("onb_complete", "true");
    confetti({ particleCount: 120, spread: 80, origin: { y: 0.5 }, colors: ["#10b981", "#2d7a4f"] });
    setTimeout(() => navigate("/dashboard"), 1200);
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-12" style={{ background: "#f5f8f5", color: "#0d1f10" }}>
      <div className="w-full max-w-xl">
        <div className="flex items-center gap-2.5 mb-10 justify-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl" style={{ background: "linear-gradient(135deg,#2d7a4f,#3a9a65)" }}>
            <Leaf className="h-5 w-5 text-white" />
          </div>
          <span className="text-2xl font-bold" style={{ letterSpacing: "-0.02em" }}>Carbon<span style={{ color: "#2d7a4f" }}>Lens</span></span>
        </div>

        {/* Progress dots */}
        <div className="flex items-center gap-2 mb-10 justify-center">
          {[1,2,3].map(s => (
            <div key={s} className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full transition-colors" style={{ background: s <= step ? "#2d7a4f" : "#d1e3d1", border: s === step ? "2px solid rgba(45,122,79,0.3)" : "none", transform: s === step ? "scale(1.2)" : "scale(1)" }} />
              {s < 3 && <div className="h-1 w-12 rounded-full transition-colors" style={{ background: s < step ? "#2d7a4f" : "#eef5ee" }} />}
            </div>
          ))}
        </div>

        <div className="p-8 rounded-[24px]" style={{ background: "#fff", border: "1px solid #d1e3d1", boxShadow: "0 8px 30px rgba(13,26,15,0.06)" }}>
          {step === 1 && (
            <div className="space-y-6 animate-fade-in-up">
              <div className="text-center mb-8">
                <h2 className="text-2xl font-bold mb-2">Tell us about your organization</h2>
                <p className="text-sm" style={{ color: "#5a6b5a" }}>We'll configure CarbonLens based on your profile.</p>
              </div>
              <div className="space-y-4">
                <div className="space-y-1.5"><label className="label-caps">Organization Name</label><input value={org} onChange={e => setOrg(e.target.value)} style={inputStyle} placeholder="Acme Corp" /></div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5"><label className="label-caps">Industry</label><select value={ind} onChange={e => setInd(e.target.value)} style={inputStyle}>{SECTORS.map(s => <option key={s} value={s}>{s}</option>)}</select></div>
                  <div className="space-y-1.5"><label className="label-caps">Country</label><select value={country} onChange={e => setCountry(e.target.value)} style={inputStyle}>{COUNTRIES.map(s => <option key={s.code} value={s.code}>{s.name}</option>)}</select></div>
                </div>
                <div className="space-y-1.5"><label className="label-caps">Revenue Range</label><select value={rev} onChange={e => setRev(e.target.value)} style={inputStyle}>{REVENUE.map(s => <option key={s} value={s}>{s}</option>)}</select></div>
                <div className="space-y-2">
                  <label className="label-caps">Primary Emission Concern</label>
                  <div className="grid grid-cols-2 gap-2">
                    {[{v: "scope1", l: "Scope 1"}, {v: "scope2", l: "Scope 2"}, {v: "scope3", l: "Scope 3"}, {v: "all", l: "All Scopes"}].map(o => (
                      <label key={o.v} className="flex items-center gap-2 p-3 rounded-xl border cursor-pointer transition-colors" style={{ background: concern === o.v ? "rgba(45,122,79,0.08)" : "#e8f2e8", borderColor: concern === o.v ? "#2d7a4f" : "#d1e3d1", color: concern === o.v ? "#1f5e3a" : "#2d3d2d" }}>
                        <input type="radio" checked={concern === o.v} onChange={() => setConcern(o.v)} className="accent-[#2d7a4f]" />
                        <span className="text-sm font-semibold">{o.l}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
              <button onClick={handle1} disabled={!org} className="w-full btn-primary py-3.5 mt-4 justify-center">Continue <ChevronRight className="h-4 w-4" /></button>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-6 animate-fade-in-up">
              <div className="text-center mb-8">
                <h2 className="text-2xl font-bold mb-2">Key Suppliers</h2>
                <p className="text-sm" style={{ color: "#5a6b5a" }}>Add initial suppliers to construct your supply chain map.</p>
              </div>
              <div className="space-y-4">
                {sups.map((s, i) => (
                  <div key={i} className="p-5 rounded-[20px] relative" style={{ background: "#e8f2e8", border: "1px solid #d1e3d1" }}>
                    {sups.length > 1 && <button onClick={() => setSups(p => p.filter((_, x) => x !== i))} className="absolute top-4 right-4 text-red-500 hover:text-red-700"><Trash2 className="h-4 w-4" /></button>}
                    <p className="label-caps mb-3">Supplier {i + 1}</p>
                    <div className="space-y-3">
                      <input value={s.name} onChange={e => setSups(p => p.map((x, j) => j === i ? {...x, name: e.target.value} : x))} style={inputStyle} placeholder="Supplier name" />
                      <div className="grid grid-cols-3 gap-2">
                        <select value={s.country} onChange={e => setSups(p => p.map((x, j) => j === i ? {...x, country: e.target.value} : x))} style={{...inputStyle, padding: "8px 10px"}}>{COUNTRIES.map(c => <option key={c.code} value={c.code}>{c.code}</option>)}</select>
                        <select value={s.sector} onChange={e => setSups(p => p.map((x, j) => j === i ? {...x, sector: e.target.value} : x))} style={{...inputStyle, padding: "8px 10px"}}>{SECTORS.map(c => <option key={c} value={c}>{c}</option>)}</select>
                        <input type="number" placeholder="ESG 0-100" value={s.esg} onChange={e => setSups(p => p.map((x, j) => j === i ? {...x, esg: e.target.value} : x))} style={{...inputStyle, padding: "8px 10px"}} />
                      </div>
                    </div>
                  </div>
                ))}
                <button onClick={() => setSups(p => [...p, { name: "", country: "IN", sector: "Manufacturing", esg: "" }])} className="btn-ghost w-full py-2.5 text-sm gap-2"><Plus className="h-4 w-4" /> Add Another Supplier</button>
              </div>
              <div className="flex gap-3 pt-4">
                <button onClick={() => setStep(1)} className="btn-ghost py-3.5 px-6"><ChevronLeft className="h-4 w-4" /> Back</button>
                <button onClick={() => handle2(false)} disabled={loading} className="btn-primary flex-1 py-3.5 justify-center">Continue <ChevronRight className="h-4 w-4" /></button>
              </div>
              <div className="text-center mt-2"><button onClick={() => handle2(true)} className="text-xs font-semibold hover:underline" style={{ color: "#8a9b8a" }}>Skip for now</button></div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-6 animate-fade-in-up">
              <div className="text-center mb-8">
                <h2 className="text-2xl font-bold mb-2">Reduction Targets</h2>
                <p className="text-sm" style={{ color: "#5a6b5a" }}>Set your decarbonisation goals.</p>
              </div>
              <div className="space-y-5">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5"><label className="label-caps">Baseline Year</label><select value={baseYear} onChange={e => setBaseYear(e.target.value)} style={inputStyle}>{BASELINE.map(s => <option key={s} value={s}>{s}</option>)}</select></div>
                  <div className="space-y-1.5"><label className="label-caps">Net Zero Year</label><select value={netZ} onChange={e => setNetZ(e.target.value)} style={inputStyle}>{NET_ZERO.map(s => <option key={s} value={s}>{s}</option>)}</select></div>
                </div>
                <div className="space-y-3 p-5 rounded-[20px]" style={{ background: "#e8f2e8", border: "1px solid #d1e3d1" }}>
                  <div className="flex justify-between items-center"><label className="label-caps">2030 Reduction Target</label><span className="text-2xl font-bold" style={{ color: "#2d7a4f" }}>{target}%</span></div>
                  <input type="range" min={5} max={50} value={target} onChange={e => setTarget(parseInt(e.target.value))} className="w-full h-2 rounded-full accent-[#2d7a4f] bg-[#d1e3d1]" />
                </div>
                <div className="space-y-2">
                  <label className="label-caps">Reporting Standards</label>
                  <div className="grid grid-cols-2 gap-2">
                    {STDS.map(s => (
                      <button key={s} onClick={() => setStds(p => p.includes(s) ? p.filter(x => x !== s) : [...p, s])} className="flex items-center gap-2 p-3 rounded-xl border transition-colors text-left" style={{ background: stds.includes(s) ? "rgba(45,122,79,0.08)" : "#e8f2e8", borderColor: stds.includes(s) ? "#2d7a4f" : "#d1e3d1", color: stds.includes(s) ? "#1f5e3a" : "#2d3d2d" }}>
                        <div className="h-4 w-4 rounded flex items-center justify-center shrink-0" style={{ border: stds.includes(s) ? "none" : "1px solid #8a9b8a", background: stds.includes(s) ? "#2d7a4f" : "transparent" }}>
                          {stds.includes(s) && <Check className="h-3 w-3 text-white" />}
                        </div>
                        <span className="text-sm font-semibold">{s}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex gap-3 pt-4">
                <button onClick={() => setStep(2)} className="btn-ghost py-3.5 px-6"><ChevronLeft className="h-4 w-4" /> Back</button>
                <button onClick={handle3} className="btn-primary flex-1 py-3.5 justify-center">Complete Setup <Check className="h-4 w-4" /></button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
