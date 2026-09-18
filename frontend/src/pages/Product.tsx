import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
export default function Product() {
  const { id = "" } = useParams();
  const [d, setD] = useState<any>(null);
  useEffect(() => { api.get(id).then(setD).catch(() => {}); }, [id]);
  if (!d) return <div className="glass p-6">Loading…</div>;
  return (
    <div className="glass space-y-2 p-5"><h2 className="text-xl font-bold">Package: {d.product || "Unknown"}</h2>
      <div className="text-sm text-slate-300">Inspection {d.id} · Officer {d.officer} · {d.created_at}</div>
      {d.fields.map((f: any) => <div key={f.field} className="border-t border-white/10 py-1.5 text-sm"><b>{f.field}:</b> {f.value || `— (${f.status})`} <span className="text-xs text-slate-400">conf {Math.round(f.confidence * 100)}% · {f.source}</span></div>)}
    </div>
  );
}
