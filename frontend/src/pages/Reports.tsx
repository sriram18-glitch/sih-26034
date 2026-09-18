import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, friendlyError } from "../api/client";
import { useAppMode } from "../store/appMode";

export default function Reports() {
  const [rows, setRows] = useState<any[]>([]);
  const [err, setErr] = useState("");
  const { mode } = useAppMode();
  useEffect(() => { api.list("?status=", mode).then(setRows).catch((e) => setErr(friendlyError(e, "load"))); }, [mode]);
  const withStage = rows.filter((r) => r.stage === "REPORTED" || r.stage === "REVIEWED");
  return (
    <div className="space-y-4">
      <h2 className="text-3xl font-extrabold tracking-tight">Reports</h2>
      <div className="glass p-4 text-sm text-slate-300">Reports generated from completed inspections appear here. Each PDF carries the automated-screening disclaimer.</div>
      {err ? <div className="glass p-6 text-sm text-red-300">{err}</div>
      : withStage.length === 0 ? (
        <div className="empty-state">
          <div className="font-bold">No reports generated yet</div>
          <p className="mt-1 text-sm text-slate-400">Reports generated from completed inspections will appear here.</p>
          <Link to="/scan" className="btn-primary mt-4 inline-block text-sm">Start New Inspection</Link>
        </div>
      ) : withStage.map((r) => (
        <div key={r.id} className="glass flex items-center gap-3 p-3 text-sm">
          <span className="font-mono text-xs">{r.id.slice(0, 8)}</span><span>{r.product || "—"}</span>
          {r.is_demo && <span className="badge-demo rounded-full px-1.5 py-0.5 text-[10px]">DEMO</span>}
          <span className="ml-auto flex gap-2"><Link className="text-indigo-300 underline" to={`/inspections/${r.id}`}>Open</Link><a className="text-indigo-300 underline" href={api.reportUrl(r.id)} target="_blank" rel="noreferrer">PDF</a></span>
        </div>))}
    </div>
  );
}
