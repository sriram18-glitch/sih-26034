import { Link, NavLink, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { useAppMode } from "../store/appMode";

const ICONS: Record<string, ReactNode> = {
  Dashboard: (<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.6} className="h-4 w-4" aria-hidden><rect x="2.5" y="2.5" width="6" height="6" rx="1.5" /><rect x="11.5" y="2.5" width="6" height="6" rx="1.5" /><rect x="2.5" y="11.5" width="6" height="6" rx="1.5" /><rect x="11.5" y="11.5" width="6" height="6" rx="1.5" /></svg>),
  Inspections: (<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.6} className="h-4 w-4" aria-hidden><path d="M4 5h12M4 10h12M4 15h7" strokeLinecap="round" /></svg>),
  "Scan Product": (<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.6} className="h-4 w-4" aria-hidden><path d="M3 7V4h3M14 3h3v3M17 13v3h-3M6 17H3v-3" strokeLinecap="round" /><circle cx="10" cy="10" r="3.2" /></svg>),
  Rules: (<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.6} className="h-4 w-4" aria-hidden><path d="M6 3h8l4 4v10H6z" strokeLinejoin="round" /><path d="M9 9h5M9 12.5h5" strokeLinecap="round" /></svg>),
  Reports: (<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.6} className="h-4 w-4" aria-hidden><path d="M5 3h7l3 3v11H5z" strokeLinejoin="round" /><path d="M8 12l2.5 2.5L13 11" strokeLinecap="round" strokeLinejoin="round" /></svg>),
  Audit: (<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.6} className="h-4 w-4" aria-hidden><circle cx="10" cy="10" r="7" /><path d="M10 6v4l2.5 2" strokeLinecap="round" /></svg>),
  Settings: (<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.6} className="h-4 w-4" aria-hidden><circle cx="10" cy="10" r="2.4" /><path d="M10 2.8v2.4M10 14.8v2.4M2.8 10h2.4M14.8 10h2.4M5 5l1.7 1.7M13.3 13.3L15 15M15 5l-1.7 1.7M6.7 13.3L5 15" strokeLinecap="round" /></svg>),
};

const links = [
  ["Dashboard", "/dashboard"],
  ["Inspections", "/history"],
  ["Scan Product", "/scan"],
  ["Rules", "/rules"],
  ["Reports", "/reports"],
  ["Audit", "/audit"],
  ["Settings", "/settings"],
];

export default function Layout({ children }: { children: ReactNode }) {
  const loc = useLocation();
  const { isDemo } = useAppMode();
  return (
    <div className="app-shell min-h-screen">
      <div className="reactive-bg" aria-hidden />
      <header className="sticky top-0 z-20 border-b border-white/10 bg-[#070b18]/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-3">
          <Link to="/" className="flex items-center gap-2 font-bold tracking-tight" aria-label="SIH26034 home">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-indigo-400 to-violet-600 text-sm">LM</span>
            <span className="hidden sm:inline">SIH26034 · Metrology Compliance</span>
          </Link>
          {isDemo ? (
            <span className="rounded-full border border-amber-400/50 bg-amber-400/15 px-2.5 py-0.5 text-[11px] font-bold tracking-widest text-amber-200" title="Demo data is simulated and labelled">
              DEMO MODE
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/40 bg-emerald-400/10 px-2.5 py-0.5 text-[11px] font-bold tracking-widest text-emerald-200" title="Live inspection data">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 animate-pulse" aria-hidden /> LIVE
            </span>
          )}
          <nav className="hidden flex-wrap gap-1 lg:flex" aria-label="Primary">
            {links.map(([label, to]) => (
              <NavLink key={to} to={to}
                className={({ isActive }) =>
                  `nav-link relative flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm ${isActive || loc.pathname === to ? "bg-white/10 text-white" : "text-slate-300 hover:bg-white/5"}`
                }>{ICONS[label]}<span>{label}</span></NavLink>
            ))}
          </nav>
          <Link to="/scan" className="btn-primary ml-auto text-sm">Scan Product</Link>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-4 pb-2 lg:hidden" aria-label="Primary mobile">
          {links.map(([label, to]) => (
            <NavLink key={to} to={to} className={({ isActive }) => `flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 text-sm ${isActive ? "bg-white/10 text-white" : "text-slate-300"}`}>{ICONS[label]}{label}</NavLink>
          ))}
        </nav>
      </header>
      <main className="relative mx-auto max-w-7xl px-4 py-6">{children}</main>
    </div>
  );
}
