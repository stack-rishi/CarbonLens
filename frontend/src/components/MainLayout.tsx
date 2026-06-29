import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/useAuthStore";
import {
  BarChart3,
  Network,
  Zap,
  Building2,
  FileText,
  MessageSquare,
  LogOut,
  Leaf,
  User as UserIcon,
  Menu,
  X,
} from "lucide-react";
import { cn } from "../lib/utils";

const NAV_ITEMS = [
  { name: "Dashboard",    href: "/dashboard",    icon: BarChart3 },
  { name: "Supply Chain", href: "/supply-chain", icon: Network },
  { name: "Emissions",    href: "/emissions",    icon: Zap },
  { name: "Suppliers",    href: "/suppliers",    icon: Building2 },
  { name: "Reports",      href: "/reports",      icon: FileText },
  { name: "AI Copilot",   href: "/chat",         icon: MessageSquare },
];

const PAGE_TITLES: Record<string, string> = {
  "/dashboard":    "Dashboard",
  "/supply-chain": "Supply Chain Map",
  "/emissions":    "Emissions Ledger",
  "/suppliers":    "Suppliers Network",
  "/reports":      "Reports",
  "/chat":         "AI Copilot",
  "/onboarding":   "Onboarding",
};

interface MainLayoutProps {
  children: React.ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const location  = useLocation();
  const navigate  = useNavigate();
  const logout    = useAuthStore((s) => s.logout);
  const user      = useAuthStore((s) => s.user);
  const [mobileOpen, setMobileOpen] = useState(false);

  const pageTitle = PAGE_TITLES[location.pathname] ?? "CarbonLens";

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const SidebarContent = () => (
    <div className="flex h-full flex-col justify-between relative z-10 overflow-hidden bg-[#0A0F0C]">
      {/* Subtle Gradient Accent on the far left */}
      <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#2D7A4F] via-[#4ADE80] to-[#2D7A4F]" />
      
      {/* Background ambient gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#4ADE80] to-transparent opacity-5 pointer-events-none" />

      {/* ── Logo ─────────────────────────── */}
      <div className="relative z-10 pt-10 px-6 pb-6 border-b border-white/[0.04]">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center">
            <Leaf className="h-6 w-6 text-[#2D7A4F]" />
          </div>
          <span className="text-lg font-bold tracking-tight text-white">
            CarbonLens
          </span>
        </div>

        {/* ── Nav items ───────────────────── */}
        <nav className="mt-8 space-y-3">
          {NAV_ITEMS.map((item) => {
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.href}
                to={item.href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "group relative flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200",
                  isActive 
                    ? "bg-[rgba(45,122,79,0.15)] border border-[rgba(45,122,79,0.3)]" 
                    : "hover:bg-white/[0.02]"
                )}
              >
                <div className={cn("flex h-6 w-6 items-center justify-center rounded-md", isActive ? "bg-[#4ADE80] bg-opacity-20" : "")}>
                  <item.icon className={cn("h-4 w-4 shrink-0 transition-colors", isActive ? "text-[#4ADE80]" : "text-[#94A3B8] group-hover:text-white")} />
                </div>
                <span className={cn("text-[14px]", isActive ? "font-semibold text-[#4ADE80]" : "font-normal text-[#94A3B8] group-hover:text-white")}>
                  {item.name}
                </span>
                
                {/* NEW Badge for AI Copilot */}
                {item.name === "AI Copilot" && (
                  <span className="ml-auto px-2 py-0.5 rounded-full bg-[#2d7a4f] text-white text-[9px] font-bold tracking-wider">
                    NEW
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* ── User + Logout ────────────────── */}
      <div className="p-4 relative z-10 mb-4">
        <div className="flex flex-col gap-3 p-4 rounded-2xl bg-white/[0.03] border border-white/[0.05] hover:bg-white/[0.05] transition-colors relative group cursor-pointer">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#1E293B]">
              <UserIcon className="h-5 w-5 text-white/50" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-semibold truncate text-white">
                {user?.email?.split('@')[0] || "User"}
              </p>
              <p className="text-[11px] font-medium text-[#64748B]">
                Sustainability Lead
              </p>
            </div>
          </div>
          
          <div className="absolute inset-x-0 bottom-full mb-2 opacity-0 group-hover:opacity-100 transition-opacity flex justify-center pointer-events-none group-hover:pointer-events-auto">
            <button
              onClick={handleLogout}
              className="flex items-center justify-center gap-2 py-2 px-4 rounded-xl text-[12px] font-semibold text-white bg-[#1E293B] hover:bg-red-500/20 hover:text-red-400 border border-white/10 transition-all shadow-lg"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen" style={{ background: "#f5f8f5" }}>
      {/* ── Desktop Sidebar ─────────────────── */}
      <aside
        className="hidden lg:flex w-[240px] shrink-0 flex-col"
        style={{ background: "#0d1a0f", borderRight: "1px solid rgba(255,255,255,0.06)" }}
      >
        <SidebarContent />
      </aside>

      {/* ── Mobile Sidebar ──────────────────── */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <aside
            className="fixed left-0 top-0 bottom-0 w-[240px] z-50"
            style={{ background: "#0d1a0f", borderRight: "1px solid rgba(255,255,255,0.06)" }}
          >
            <button
              onClick={() => setMobileOpen(false)}
              className="absolute top-4 right-4 p-1.5 rounded-lg"
              style={{ color: "#8ea58e" }}
            >
              <X className="h-4 w-4" />
            </button>
            <SidebarContent />
          </aside>
        </div>
      )}

      {/* ── Main Content ─────────────────────── */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Header */}
        <header
          className="flex items-center justify-between px-6 py-3.5 sticky top-0 z-10"
          style={{
            background: "rgba(245,248,245,0.85)",
            backdropFilter: "blur(12px)",
            borderBottom: "1px solid #d1e3d1",
          }}
        >
          <div className="flex items-center gap-3">
            <button
              className="lg:hidden p-1.5 rounded-lg transition-colors"
              style={{ color: "#5a6b5a" }}
              onClick={() => setMobileOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </button>
            <h1 className="text-lg font-semibold" style={{ color: "#0d1f10", letterSpacing: "-0.01em" }}>
              {pageTitle}
            </h1>
          </div>

          {user?.org_id && (
            <span
              className="hidden sm:inline text-xs px-3 py-1"
              style={{
                background: "#e8f2e8",
                border: "1px solid #d1e3d1",
                color: "#5a6b5a",
                borderRadius: "9999px",
              }}
            >
              Org: {user.org_id.slice(0, 8)}…
            </span>
          )}
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="mx-auto max-w-7xl">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
