import { useEffect, useState } from "react";
import { api, friendlyError } from "../api/client";
import { useAppMode } from "../store/appMode";
export default function Audit() {
  const [rows, setRows] = useState<any[]>([]);
  const [err, setErr] = useState("");
  const { mode, isDemo } = useAppMode();
  useEffect(() => { setErr(""); api.auditAll(mode).then(setRows).catch((e) => setErr(friendlyError(e, "load"))); }, [mode]);
  return (
    <div className="space-y-4"><h2 className="text-3xl font-extrabold tracking-tight">Audit Trail <span className="text-sm font-normal text-slate-400">(append-only · real events only · {isDemo ? "Demo Mode" : "Live Mode"})</span></h2>
      {err ? <div className="glass p-6 text-sm text-red-300">Could not load audit events: {err}</div>
      : rows.length === 0 ? (
        <div className="empty-state">
          <div className="font-bold">No audit events yet</div>
          <p className="mt-1 text-sm text-slate-400">Activity will appear here as inspections are processed.</p>
        </div>
      ) : (
      <div className="glass p-4 text-sm">
        {rows.map((a, i) => (
          <div key={i} className="border-t border-white/10 py-1.5 font-mono text-xs first:border-0">
            {a.at?.slice(0, 19)} · {a.event} · {a.inspection_id?.slice(0, 8)} · {a.actor} {a.reason}
          </div>))}
      </div>
      )}
    </div>
  );
}
