import { useEffect, useState } from "react";
import { api } from "../api/client";
export default function Rules() {
  const [rules, setRules] = useState<any[]>([]);
  useEffect(() => { api.rules().then(setRules).catch(() => {}); }, []);
  return (
    <div className="space-y-4">
      <h2 className="text-3xl font-extrabold tracking-tight">Compliance Rules</h2>
      <div className="glass border-amber-400/30 p-4 text-sm text-slate-300">
        <b className="text-amber-200">Screening configuration — not authoritative legal advice.</b>
        <div className="mt-1 text-slate-400">Entries marked VERIFIED were checked against the cited official source; UNVERIFIED entries are heuristics. All must be re-checked against currently applicable Legal Metrology requirements before operational use.</div>
      </div>
      {rules.map((r) => (
        <div key={r.rule_code} className="glass p-4">
          <div className="flex gap-2 items-center flex-wrap"><b>{r.title}</b>
            <span className={`ml-auto rounded-full px-2 py-0.5 text-xs ${r.rule_status === "VERIFIED" ? "badge-compliant" : "badge-review"}`}>{r.rule_status || "UNVERIFIED"} · v{r.rule_version}</span></div>
          <div className="mt-1 text-sm text-slate-300">{r.description}</div>
          <div className="mt-1 text-xs text-slate-400">Requires: {r.requirement} · Severity: {r.severity}</div>
          <div className="mt-1 text-xs text-slate-400">Source: {r.source_reference}{r.source_url ? <> · <a className="underline" href={r.source_url} target="_blank" rel="noreferrer">official source</a></> : null}</div>
          {r.verification_notes && <div className="mt-1 text-xs text-slate-500">Note: {r.verification_notes}</div>}
        </div>
      ))}
    </div>
  );
}
