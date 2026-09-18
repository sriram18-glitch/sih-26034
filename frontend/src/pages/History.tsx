import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, statusBadge, statusLabel, friendlyError } from "../api/client";
import { useAppMode } from "../store/appMode";

export default function History() {
  const [rows, setRows] = useState<any[]>([]);
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [maker, setMaker] = useState("");
  const [finding, setFinding] = useState("");
  const [err, setErr] = useState("");
  const [picked, setPicked] = useState<string[]>([]);
  const [cmp, setCmp] = useState<any>(null);
  const [cmpErr, setCmpErr] = useState("");
  const { mode } = useAppMode();
  const load = () => {
    setErr("");
    const p = `?status=${encodeURIComponent(status)}&q=${encodeURIComponent(q)}&manufacturer=${encodeURIComponent(maker)}&finding=${encodeURIComponent(finding)}`;
    api.list(p, mode).then(setRows).catch((e) => setErr(friendlyError(e, "load")));
  };
  useEffect(() => { load(); setPicked([]); setCmp(null); }, [mode]);
  const toggle = (id: string) =>
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id].slice(-4)));
  const runCompare = () => {
    setCmpErr("");
    if (picked.length < 2) { setCmpErr("Select at least two inspections to compare."); return; }
    api.compare(picked).then(setCmp).catch((e) => setCmpErr(String(e)));
  };
  return (
    <div className="space-y-4">
      <h2 className="text-3xl font-extrabold tracking-tight">Inspections</h2>
      <div className="flex flex-wrap gap-2">
        <select className="input max-w-60" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status">
          <option value="">All statuses</option><option value="COMPLIANT">Compliant</option>
          <option value="POTENTIAL_VIOLATION">Potential violation</option><option value="REVIEW_REQUIRED">Review required</option>
        </select>
        <input className="input max-w-60" placeholder="Search product / ID" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" />
        <input className="input max-w-60" placeholder="Manufacturer" value={maker} onChange={(e) => setMaker(e.target.value)} aria-label="Filter by manufacturer" />
        <select className="input max-w-60" value={finding} onChange={(e) => setFinding(e.target.value)} aria-label="Filter by issue type">
          <option value="">All issue types</option>
          <option value="conflict">Open inconsistency</option>
          <option value="failed_rule">Failed rule check</option>
        </select>
        <button className="btn-ghost text-sm" onClick={load}>Filter</button>
        {picked.length > 0 && (
          <button className="btn-primary text-sm" onClick={runCompare}>
            Compare {picked.length} selected
          </button>
        )}
      </div>
      {cmpErr && <div className="glass border-red-500/30 p-3 text-sm text-red-300">{cmpErr}</div>}
      {cmp && (
        <div className="glass overflow-x-auto p-4" aria-label="Package comparison">
          <h3 className="mb-2 font-bold">Package comparison (deterministic, extracted values only)</h3>
          <table className="w-full text-sm">
            <thead><tr className="text-left text-slate-400"><th>Declaration</th>
              {cmp.columns.map((c: any) => <th key={c.id}>{c.product || c.id.slice(0, 8)}</th>)}
            </tr></thead>
            <tbody>{cmp.rows.map((r: any) => (
              <tr key={r.field} className={`border-t border-white/10 ${r.differs ? "bg-amber-400/[0.06]" : ""}`}>
                <td className="py-1.5 pr-3 text-slate-400">{r.field}{r.differs ? " ⚠" : ""}</td>
                {r.values.map((v: any) => (
                  <td key={v.inspection} className="py-1.5 pr-3">{v.value || <span className="text-slate-500">— {v.status}</span>}</td>
                ))}
              </tr>))}</tbody>
          </table>
        </div>
      )}
      {err ? (
        <div className="glass p-6 text-sm text-red-300">Could not load inspections: {err}</div>
      ) : rows.length === 0 ? (
        <div className="empty-state">
          <div className="font-bold">No inspections found</div>
          <p className="mt-1 text-sm text-slate-400">Start your first inspection to begin building compliance history.</p>
          <Link to="/scan" className="btn-primary mt-4 inline-block text-sm">Start New Inspection</Link>
        </div>
      ) : (
        <div className="glass overflow-x-auto p-4">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-slate-400"><th></th><th>Inspection ID</th><th>Date</th><th>Product</th><th>Status</th><th>Officer</th><th>Images</th><th>Actions</th></tr></thead>
            <tbody>{rows.map((r) => (
              <tr key={r.id} className="border-t border-white/10">
                <td className="pr-2"><input type="checkbox" aria-label={`Select ${r.id.slice(0, 8)} for comparison`}
                  checked={picked.includes(r.id)} onChange={() => toggle(r.id)} /></td>
                <td className="py-2 pr-3 font-mono text-xs">{r.id.slice(0, 8)}</td>
                <td className="pr-3 text-xs">{r.created_at?.slice(0, 16)}</td>
                <td className="pr-3">{r.product || "—"} {r.is_demo && <span className="badge-demo ml-1 rounded-full px-1.5 py-0.5 text-[10px]">DEMO</span>}</td>
                <td className="pr-3"><span className={`rounded-full px-2 py-0.5 text-xs ${statusBadge(r.status)}`}>{statusLabel(r.status)}</span></td>
                <td className="pr-3 text-xs">{r.officer}</td>
                <td className="pr-3 text-xs">{r.images ?? "—"}</td>
                <td><Link className="text-indigo-300 underline" to={`/inspections/${r.id}`}>Open</Link></td>
              </tr>))}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}
