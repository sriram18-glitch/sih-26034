import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { api, statusBadge, statusLabel, friendlyError } from "../api/client";
import { useAppMode } from "../store/appMode";

function Empty({ title, body }: { title: string; body: string }) {
  return (
    <div className="empty-state">
      <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-xl bg-indigo-500/15 text-lg">◌</div>
      <div className="font-bold">{title}</div>
      <p className="mt-2 text-sm text-slate-400">{body}</p>
      <Link to="/scan" className="btn-primary mt-4 inline-block text-sm">Start New Inspection</Link>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null);
  const [recent, setRecent] = useState<any[]>([]);
  const [queue, setQueue] = useState<any[]>([]);
  const [counts, setCounts] = useState<any>(null);
  const [err, setErr] = useState("");
  const { mode, isDemo } = useAppMode();
  useEffect(() => {
    setStats(null);
    setRecent([]);
    setErr("");
    api.stats(mode).then(setStats).catch((e) => setErr(friendlyError(e, "load")));
    api.list("", mode).then((d) => setRecent(d.slice(0, 8))).catch(() => setRecent([]));
    api.attention(mode).then((a) => { setQueue(a.queue || []); setCounts(a.counts || null); }).catch(() => setQueue([]));
  }, [mode]);
  if (err) return <div className="glass p-6">Backend unavailable: {err}. Start backend on :8000. No fallback data is shown.</div>;
  if (!stats) return <div className="glass p-6">Loading dashboard…</div>;
  const hasData = stats.total > 0;
  const cards: [string, number, string][] = [
    ["Total Inspections", stats.total, "from-indigo-400 to-violet-500"],
    ["Potential Violations", stats.potential_violation, "from-red-400 to-orange-500"],
    ["Review Required", stats.review_required, "from-amber-300 to-orange-400"],
    ["Compliant", stats.compliant, "from-emerald-400 to-cyan-500"],
  ];
  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight">Officer Dashboard</h2>
          <p className="mt-1 text-sm text-slate-400">{isDemo ? "Demo Mode — showing simulated DEMO records only." : "Live Mode — showing real inspections only."}</p>
        </div>
        <Link to="/scan" className="btn-primary ml-auto text-sm">+ New Inspection</Link>
      </div>
      {queue.length > 0 && (
        <section className="glass p-4" aria-label="Attention queue">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-bold">Needs attention</h3>
            {counts && <span className="text-xs text-slate-400">{counts.high} high · {counts.medium} medium</span>}
          </div>
          <div className="mt-2 space-y-1.5">
            {queue.slice(0, 6).map((q: any) => (
              <Link key={q.id} to={`/inspections/${q.id}/result`}
                className="flex flex-wrap items-center gap-2 rounded-xl border border-white/10 p-2.5 text-sm hover:border-white/25">
                <span className={`rounded-full px-2 py-0.5 text-[11px] ${q.level === "HIGH" ? "badge-violation" : "badge-review"}`}>{q.level}</span>
                <span className="font-mono text-xs text-slate-400">{q.id.slice(0, 8)}</span>
                <span className="font-semibold">{q.product || "Unnamed package"}</span>
                <span className="text-xs text-slate-400">{q.reasons.slice(0, 2).join(" · ")}</span>
              </Link>
            ))}
          </div>
        </section>
      )}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {cards.map(([l, v, grad]) => (
          <div key={l} className="kpi-card glass group p-6">
            <div className={`mb-3 h-1 w-10 rounded-full bg-gradient-to-r ${grad}`} aria-hidden />
            <div className="metric-number">{v}</div>
            <div className="metric-label mt-1">{l}</div>
          </div>
        ))}
      </div>
      {!hasData ? (
        <Empty title="No analytics yet" body="Complete inspections to generate compliance analytics. Start your first inspection to see charts here." />
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          <div className="glass p-6"><h3 className="mb-3 font-bold">Inspections over time</h3>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={stats.inspections_over_time} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                <defs>
                  <linearGradient id="kpiBar" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#818cf8" stopOpacity={1} />
                    <stop offset="100%" stopColor="#6366f1" stopOpacity={0.55} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: "#0b1226", border: "1px solid rgba(129,140,248,.3)", borderRadius: 10, fontSize: 12 }} />
                <Bar dataKey="count" fill="url(#kpiBar)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer></div>
          <div className="glass p-6"><h3 className="mb-3 font-bold">Status distribution</h3>
            <ResponsiveContainer width="100%" height={260}><PieChart><Pie data={stats.status_distribution} dataKey="count" nameKey="status" label>{stats.status_distribution.map((_: any, i: number) => <Cell key={i} fill={["#34d399", "#f87171", "#fbbf24", "#94a3b8"][i % 4]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div>
        </div>
      )}
      <div className="glass overflow-x-auto p-6">
        <h3 className="mb-3 font-bold">Recent inspections</h3>
        {recent.length === 0 ? (
          <p className="py-6 text-center text-sm text-slate-400">No inspections yet. Start your first inspection to begin building compliance history.</p>
        ) : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-slate-400"><th>Inspection ID</th><th>Date</th><th>Product</th><th>Status</th><th>Officer</th><th>Images</th><th>Actions</th></tr></thead>
            <tbody>{recent.map((r) => (
              <tr key={r.id} className="border-t border-white/10">
                <td className="py-2 pr-3 font-mono text-xs">{r.id.slice(0, 8)}</td>
                <td className="pr-3 text-xs">{r.created_at?.slice(0, 16)}</td>
                <td className="pr-3">{r.product || "—"} {r.is_demo && <span className="badge-demo ml-1 rounded-full px-1.5 py-0.5 text-[10px]">DEMO</span>}</td>
                <td className="pr-3"><span className={`rounded-full px-2 py-0.5 text-xs ${statusBadge(r.status)}`}>{statusLabel(r.status)}</span></td>
                <td className="pr-3 text-xs">{r.officer}</td>
                <td className="pr-3 text-xs">{r.images ?? "—"}</td>
                <td><Link className="text-indigo-300 underline" to={`/inspections/${r.id}`}>Open</Link></td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>
    </div>
  );
}