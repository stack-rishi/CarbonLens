import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/useAuthStore";
import { api } from "../lib/api";
import { Leaf, Check, Eye, EyeOff, Loader2, ArrowRight, Zap } from "lucide-react";

const SECTORS = ["Manufacturing","Logistics","Retail","Technology","Energy","Agriculture","Finance","Other"];
const COUNTRIES = [
  { code: "IN", name: "India" }, { code: "US", name: "United States" },
  { code: "GB", name: "United Kingdom" }, { code: "DE", name: "Germany" },
  { code: "SG", name: "Singapore" }, { code: "AU", name: "Australia" },
  { code: "JP", name: "Japan" }, { code: "CN", name: "China" },
  { code: "FR", name: "France" }, { code: "CA", name: "Canada" },
  { code: "BR", name: "Brazil" }, { code: "ZA", name: "South Africa" },
  { code: "AE", name: "UAE" }, { code: "KR", name: "South Korea" },
  { code: "NL", name: "Netherlands" }, { code: "SE", name: "Sweden" },
];

function getPasswordStrength(pw: string) {
  if (!pw.length) return { level: "weak" as const, label: "", pct: 0 };
  const score = [/[A-Z]/.test(pw), /[0-9]/.test(pw), /[^A-Za-z0-9]/.test(pw), pw.length >= 10].filter(Boolean).length;
  if (score <= 1) return { level: "weak" as const, label: "Weak", pct: 25 };
  if (score <= 2) return { level: "medium" as const, label: "Medium", pct: 62 };
  return { level: "strong" as const, label: "Strong", pct: 100 };
}

const inputStyle: React.CSSProperties = {
  background: "#eef5ee",
  border: "1px solid #d1e3d1",
  borderRadius: 12,
  padding: "10px 14px",
  fontSize: 14,
  color: "#0d1f10",
  width: "100%",
  outline: "none",
  transition: "border-color 0.15s, box-shadow 0.15s",
};
const inputFocusStyle = { borderColor: "#2d7a4f", boxShadow: "0 0 0 3px rgba(45,122,79,0.15)" };

function StyledInput({ type = "text", placeholder, value, onChange, required, extra }: any) {
  const [focused, setFocused] = React.useState(false);
  return (
    <input
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      required={required}
      style={{ ...inputStyle, ...(focused ? inputFocusStyle : {}), ...extra }}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
    />
  );
}

function StyledSelect({ value, onChange, children }: any) {
  const [focused, setFocused] = React.useState(false);
  return (
    <select
      value={value}
      onChange={onChange}
      style={{ ...inputStyle, ...(focused ? inputFocusStyle : {}), appearance: "none", cursor: "pointer" }}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
    >
      {children}
    </select>
  );
}

const FEATURES = [
  "Real-time Scope 1, 2 & 3 tracking",
  "AI-powered supply chain optimization",
  "GHG Protocol compliant reporting",
  "Automated forecast & scenario modelling",
];

export default function Login() {
  const navigate = useNavigate();
  const login    = useAuthStore((s) => s.login);
  const [tab, setTab]       = useState<"signin" | "register">("signin");

  // Sign In
  const [siEmail, setSiEmail]       = useState("");
  const [siPassword, setSiPassword] = useState("");
  const [siShowPw, setSiShowPw]     = useState(false);
  const [siError, setSiError]       = useState<string | null>(null);
  const [siLoading, setSiLoading]   = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);

  const handleQuickDemo = async () => {
    setTab("signin");
    setSiEmail("admin@acmecorp.com");
    setSiPassword("password123");
    setSiError(null);
    setDemoLoading(true);
    try {
      const res = await api.post("/auth/login", { email: "admin@acmecorp.com", password: "password123" });
      login(res.data.access_token, res.data.user);
      try {
        const suppRes = await api.get("/suppliers");
        navigate(!suppRes.data?.length ? "/onboarding" : "/dashboard");
      } catch { navigate("/dashboard"); }
    } catch (err: any) {
      setSiError(err.response?.data?.detail || "Demo login failed. Make sure the backend is running and seeded.");
    } finally { setDemoLoading(false); }
  };

  // Register
  const [regCompany, setRegCompany] = useState("");
  const [regEmail, setRegEmail]     = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regConfirm, setRegConfirm] = useState("");
  const [regSector, setRegSector]   = useState("Manufacturing");
  const [regCountry, setRegCountry] = useState("IN");
  const [regShowPw, setRegShowPw]   = useState(false);
  const [regError, setRegError]     = useState<string | null>(null);
  const [regLoading, setRegLoading] = useState(false);

  const pwStrength = getPasswordStrength(regPassword);

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setSiError(null); setSiLoading(true);
    try {
      const res = await api.post("/auth/login", { email: siEmail, password: siPassword });
      login(res.data.access_token, res.data.user);
      try {
        const suppRes = await api.get("/suppliers");
        navigate(!suppRes.data?.length ? "/onboarding" : "/dashboard");
      } catch { navigate("/dashboard"); }
    } catch (err: any) {
      setSiError(err.response?.data?.detail || "Authentication failed. Please try again.");
    } finally { setSiLoading(false); }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegError(null);
    if (regPassword !== regConfirm) { setRegError("Passwords do not match."); return; }
    setRegLoading(true);
    try {
      const res = await api.post("/auth/register", {
        email: regEmail, password: regPassword,
        org_name: regCompany, sector: regSector, country: regCountry,
      });
      login(res.data.access_token, res.data.user);
      navigate("/onboarding");
    } catch (err: any) {
      setRegError(err.response?.data?.detail || "Registration failed. Please try again.");
    } finally { setRegLoading(false); }
  };

  const pwColor = pwStrength.level === "weak" ? "#ef4444" : pwStrength.level === "medium" ? "#f59e0b" : "#2d7a4f";

  return (
    <div className="flex min-h-screen" style={{ background: "#f5f8f5" }}>
      {/* ── Left panel (hero) ─── */}
      <div
        className="hidden lg:flex lg:w-[46%] flex-col justify-between p-14"
        style={{ background: "#0d1a0f" }}
      >
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div
            className="flex h-9 w-9 items-center justify-center rounded-xl"
            style={{ background: "linear-gradient(135deg,#2d7a4f,#3a9a65)" }}
          >
            <Leaf className="h-5 w-5 text-white" />
          </div>
          <span className="text-xl font-bold" style={{ color: "rgba(255,255,255,0.90)" }}>
            Carbon<span style={{ color: "#6dc98a" }}>Lens</span>
          </span>
        </div>

        {/* Hero copy */}
        <div>
          <h2
            className="text-4xl font-bold leading-tight mb-5"
            style={{ color: "#e8f2e8", letterSpacing: "-0.02em" }}
          >
            Track emissions.<br />
            Optimise chains.<br />
            Hit your targets.
          </h2>
          <p className="text-sm mb-10" style={{ color: "#5a7a5a", lineHeight: 1.7 }}>
            Enterprise-grade carbon accounting with AI-powered insights for sustainability teams worldwide.
          </p>
          <ul className="space-y-3.5">
            {FEATURES.map((f) => (
              <li key={f} className="flex items-start gap-3">
                <div
                  className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full"
                  style={{ background: "rgba(45,122,79,0.25)" }}
                >
                  <Check style={{ width: 11, height: 11, color: "#6dc98a" }} />
                </div>
                <span className="text-sm" style={{ color: "#8ea58e" }}>{f}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="text-xs" style={{ color: "#2d4a30" }}>Trusted by sustainability teams worldwide</p>
      </div>

      {/* ── Right panel (form) ─── */}
      <div className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-[420px]">
          {/* Mobile logo */}
          <div className="flex items-center gap-2 lg:hidden mb-10">
            <div
              className="flex h-8 w-8 items-center justify-center rounded-xl"
              style={{ background: "linear-gradient(135deg,#2d7a4f,#3a9a65)" }}
            >
              <Leaf className="h-4 w-4 text-white" />
            </div>
            <span className="text-lg font-bold" style={{ color: "#0d1f10" }}>
              Carbon<span style={{ color: "#2d7a4f" }}>Lens</span>
            </span>
          </div>

          {/* Tab switcher — pill style */}
          <div
            className="flex p-1 mb-8 gap-1"
            style={{ background: "#e8f2e8", borderRadius: 9999, border: "1px solid #d1e3d1" }}
          >
            {(["signin", "register"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className="flex-1 py-2 text-sm font-semibold transition-all"
                style={{
                  borderRadius: 9999,
                  background: tab === t ? "#2d7a4f" : "transparent",
                  color: tab === t ? "#ffffff" : "#5a6b5a",
                }}
              >
                {t === "signin" ? "Sign In" : "Create Account"}
              </button>
            ))}
          </div>

          {/* Sign In */}
          {tab === "signin" && (
            <div>
              <h1 className="text-2xl font-bold mb-1" style={{ color: "#0d1f10", letterSpacing: "-0.02em" }}>
                Welcome back
              </h1>
              <p className="text-sm mb-6" style={{ color: "#5a6b5a" }}>
                Sign in to your sustainability dashboard
              </p>
              <form onSubmit={handleSignIn} className="space-y-4">
                {siError && (
                  <div
                    className="p-3 text-sm rounded-xl"
                    style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.20)", color: "#dc2626" }}
                  >
                    {siError}
                  </div>
                )}
                <div className="space-y-1.5">
                  <label className="label-caps">Email</label>
                  <StyledInput
                    type="email"
                    placeholder="you@company.com"
                    value={siEmail}
                    onChange={(e: any) => setSiEmail(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="label-caps">Password</label>
                  <div className="relative">
                    <StyledInput
                      type={siShowPw ? "text" : "password"}
                      placeholder="••••••••"
                      value={siPassword}
                      onChange={(e: any) => setSiPassword(e.target.value)}
                      required
                      extra={{ paddingRight: 42 }}
                    />
                    <button
                      type="button"
                      onClick={() => setSiShowPw(!siShowPw)}
                      className="absolute right-3 top-1/2 -translate-y-1/2"
                      style={{ color: "#8a9b8a" }}
                    >
                      {siShowPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  <div className="flex justify-end">
                    <button type="button" className="text-xs font-semibold" style={{ color: "#2d7a4f" }}>
                      Forgot password?
                    </button>
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={siLoading}
                  className="w-full btn-primary flex items-center justify-center gap-2 py-3"
                  style={{ opacity: siLoading ? 0.75 : 1 }}
                >
                  {siLoading
                    ? <><Loader2 className="h-4 w-4 animate-spin" /> Signing in…</>
                    : <> Sign In <ArrowRight className="h-4 w-4" /></>
                  }
                </button>

                {/* Quick Demo Shortcut */}
                <div className="relative flex items-center my-3">
                  <div className="flex-1 h-px" style={{ background: "#d1e3d1" }} />
                  <span className="px-3 text-xs" style={{ color: "#8a9b8a" }}>or</span>
                  <div className="flex-1 h-px" style={{ background: "#d1e3d1" }} />
                </div>
                <button
                  type="button"
                  onClick={handleQuickDemo}
                  disabled={demoLoading}
                  className="w-full flex items-center justify-center gap-2 py-2.5 text-sm font-semibold transition-all"
                  style={{
                    borderRadius: 12,
                    background: "linear-gradient(135deg, #152218, #1f3025)",
                    color: "#6dc98a",
                    border: "1px solid rgba(109,201,138,0.25)",
                    opacity: demoLoading ? 0.75 : 1,
                    cursor: demoLoading ? "not-allowed" : "pointer",
                  }}
                >
                  {demoLoading
                    ? <><Loader2 className="h-4 w-4 animate-spin" /> Launching demo…</>
                    : <><Zap className="h-4 w-4" /> Quick Demo (Acme Corp Admin)</>
                  }
                </button>
              </form>
            </div>
          )}

          {/* Register */}
          {tab === "register" && (
            <div>
              <h1 className="text-2xl font-bold mb-1" style={{ color: "#0d1f10", letterSpacing: "-0.02em" }}>
                Create your account
              </h1>
              <p className="text-sm mb-6" style={{ color: "#5a6b5a" }}>
                Set up your organisation on CarbonLens
              </p>
              <form onSubmit={handleRegister} className="space-y-4">
                {regError && (
                  <div
                    className="p-3 text-sm rounded-xl"
                    style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.20)", color: "#dc2626" }}
                  >
                    {regError}
                  </div>
                )}
                <div className="space-y-1.5">
                  <label className="label-caps">Company Name</label>
                  <StyledInput placeholder="Acme Corp" value={regCompany} onChange={(e: any) => setRegCompany(e.target.value)} required />
                </div>
                <div className="space-y-1.5">
                  <label className="label-caps">Work Email</label>
                  <StyledInput type="email" placeholder="you@company.com" value={regEmail} onChange={(e: any) => setRegEmail(e.target.value)} required />
                </div>
                <div className="space-y-1.5">
                  <label className="label-caps">Password</label>
                  <div className="relative">
                    <StyledInput
                      type={regShowPw ? "text" : "password"}
                      placeholder="••••••••"
                      value={regPassword}
                      onChange={(e: any) => setRegPassword(e.target.value)}
                      required
                      extra={{ paddingRight: 42 }}
                    />
                    <button type="button" onClick={() => setRegShowPw(!regShowPw)} className="absolute right-3 top-1/2 -translate-y-1/2" style={{ color: "#8a9b8a" }}>
                      {regShowPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {regPassword && (
                    <div className="flex items-center gap-2 mt-1.5">
                      <div style={{ flex: 1, height: 4, background: "#d1e3d1", borderRadius: 9999, overflow: "hidden" }}>
                        <div style={{ width: `${pwStrength.pct}%`, height: "100%", background: pwColor, borderRadius: 9999, transition: "width 0.3s ease" }} />
                      </div>
                      <span className="text-xs font-semibold" style={{ color: pwColor, minWidth: 44 }}>{pwStrength.label}</span>
                    </div>
                  )}
                </div>
                <div className="space-y-1.5">
                  <label className="label-caps">Confirm Password</label>
                  <StyledInput type="password" placeholder="••••••••" value={regConfirm} onChange={(e: any) => setRegConfirm(e.target.value)} required />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="label-caps">Sector</label>
                    <StyledSelect value={regSector} onChange={(e: any) => setRegSector(e.target.value)}>
                      {SECTORS.map((s) => <option key={s} value={s}>{s}</option>)}
                    </StyledSelect>
                  </div>
                  <div className="space-y-1.5">
                    <label className="label-caps">Country</label>
                    <StyledSelect value={regCountry} onChange={(e: any) => setRegCountry(e.target.value)}>
                      {COUNTRIES.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
                    </StyledSelect>
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={regLoading}
                  className="w-full btn-primary flex items-center justify-center gap-2 py-3"
                  style={{ opacity: regLoading ? 0.75 : 1 }}
                >
                  {regLoading
                    ? <><Loader2 className="h-4 w-4 animate-spin" /> Creating account…</>
                    : <> Create Account <ArrowRight className="h-4 w-4" /></>
                  }
                </button>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
