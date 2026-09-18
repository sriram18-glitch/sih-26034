import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, statusBadge, statusLabel, friendlyError } from "../api/client";
import EvidenceViewer from "../components/EvidenceViewer";

export default function Details() {
  const { id = "" } = useParams();
  const [d, setD] = useState<any>(null);
  const [edit, setEdit] = useState<Record<string, string>>({});
  const [notes, setNotes] = useState("");
  const [msg, setMsg] = useState("");
  const [hoveredField, setHoveredField] = useState<string | null>(null);
  const [findings, setFindings] = useState<any[]>([]);

  const load = () => {
    api.get(id).then((x) => { setD(x); const e: any = {}; x.fields.forEach((f: any) => (e[f.field] = f.value)); setEdit(e); }).catch((e) => setMsg(friendlyError(e, "load")));
    api.findings(id).then(setFindings).catch(() => setFindings([]));
  };
  useEffect(() => { load(); }, [id]);
  if (!d) return <div className="glass p-6">{msg ? `Could not load inspection: ${msg}` : "Loading inspection…"}</div>;

  // Find the first image URL for evidence
  const imageUrl = d.images?.[0]?.id ? api.imageUrl(d.images[0].id) : "";

  async function submit(kind: string) {
    setMsg("Saving review…");
    try {
      const body: any = { actor: "officer@gov.in", corrections: edit, notes };
      if (kind === "confirm") body.confirm_violation = true;
      if (kind === "fp") body.mark_false_positive = true;
      await api.review(id, body);
      await api.genReport(id);
      setMsg("Review saved + report generated.");
      load();
    } catch (e: any) {
      setMsg(`Review failed: ${e.message || e}`);
    }
  }
  async function rerun() {
    setMsg("Re-running analysis…");
    try {
      await api.analyze(id);
      setMsg("Re-analysis complete.");
      load();
    } catch (e: any) {
      setMsg(`Re-analysis failed: ${e.message || e}`);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h2 className="text-2xl font-bold">Inspection {id.slice(0, 8)}</h2>
        <div className="flex items-center gap-2">
          <span className={`rounded-full px-3 py-1 text-xs ${statusBadge(d.overall)}`}>{statusLabel(d.overall)}</span>
          <Link to={`/inspections/${id}/result`} className="btn-ghost ml-auto text-sm">Result view</Link>
          <a className="btn-ghost text-sm" href={api.reportUrl(id)} target="_blank" rel="noreferrer">Download PDF</a>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Image with evidence highlights */}
        <div className="glass p-4">
          <h3 className="mb-3 font-bold">Package Image</h3>
          {imageUrl ? (
            <EvidenceViewer 
              imageUrl={imageUrl} 
              boxes={d.fields.map((f: any) => ({
                field: f.field,
                value: f.value,
                bbox: f.bbox,
                highlighted: hoveredField === f.field
              }))}
              onFieldHover={setHoveredField}
              onFieldUnhover={() => setHoveredField(null)}
            />
          ) : (
            <div className="h-96 flex items-center justify-center text-sm text-slate-400">
              No image available
            </div>
          )}
        </div>

        {/* Extracted information and review */}
        <div className="glass p-4 space-y-2">
          <h3 className="font-bold">Verify extracted fields</h3>
          {d.fields.map((f: any) => (
            <label key={f.field} className={`block text-xs text-slate-300 ${hoveredField === f.field ? "border-indigo-400/50 bg-indigo-500/5 p-2" : ""}`}>
              <div className="flex justify-between items-start">
                <div>
                  <h4 className="font-semibold text-slate-100">{f.field}</h4>
                  <p className="text-sm text-slate-300">{f.value || <span className="text-slate-500">— {f.status}</span>}</p>
                  {f.normalized && f.normalized !== f.value && (
                    <p className="text-xs text-slate-400">Normalized: {f.normalized}</p>
                  )}
                </div>
                <input 
                  className="input mt-1 text-sm" 
                  value={edit[f.field] ?? ""} 
                  onChange={(e) => setEdit({ ...edit, [f.field]: e.target.value })} 
                />
              </div>
            </label>
          ))}
          <label className="block text-xs">Officer notes<textarea className="input mt-1" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Observation, reason…" /></label>
          <div className="flex flex-wrap gap-2">
            <button className="btn-primary text-sm" onClick={() => submit("save")}>Save corrections</button>
            <button className="btn-ghost text-sm" onClick={() => submit("confirm")}>Confirm violation</button>
            <button className="btn-ghost text-sm" onClick={() => submit("fp")}>Mark false positive</button>
            <button className="btn-ghost text-sm" onClick={rerun}>Re-run analysis</button>
          </div>
          {msg && <div className="text-xs text-indigo-200">{msg}</div>}
        </div>
      </div>

      <div className="space-y-4">
        {findings.filter((f: any) => f.status === "OPEN").length > 0 && (
          <div className="glass p-4">
            <h3 className="mb-2 font-bold">Open findings — verify against evidence</h3>
            {findings.filter((f: any) => f.status === "OPEN").map((f: any) => (
              <div key={f.id} className="border-t border-white/10 py-2 text-sm first:border-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-xs ${f.level === "HIGH" ? "badge-violation" : "badge-review"}`}>{f.level}</span>
                  <b>{f.title}</b>
                </div>
                <div className="mt-1 flex flex-wrap gap-2">
                  <button className="btn-ghost text-xs" onClick={() =>
                    api.resolveFinding(id, f.id, { actor: "officer@gov.in", decision: "VERIFIED", reason: notes || "verified against images" }).then(load).catch((e) => setMsg(friendlyError(e, "review")))}>Mark verified</button>
                  <button className="btn-ghost text-xs" onClick={() =>
                    api.resolveFinding(id, f.id, { actor: "officer@gov.in", decision: "FALSE_POSITIVE", reason: notes || "OCR misread" }).then(load).catch((e) => setMsg(friendlyError(e, "review")))}>False positive</button>
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="glass p-4">
          <h3 className="mb-2 font-bold">Rule checks</h3>
          {d.results.map((r: any) => <div key={r.rule_code} className="border-t border-white/10 py-2 text-sm"><b>{r.rule_code}</b> <span className="text-slate-400">· {r.status} · {r.severity}</span><div className="text-slate-300">{r.explanation}</div></div>)}
        </div>
        <div className="glass p-4">
          <h3 className="mb-2 font-bold">Review history (original preserved)</h3>
          {d.reviews.length === 0 ? <p className="text-sm text-slate-400">No reviews yet.</p> :
            d.reviews.map((r: any, i: number) => <div key={i} className="border-t border-white/10 py-1 text-xs">{r.at?.slice(0, 19)} · {r.actor} · {r.action} · {r.field} {r.before}→{r.after} {r.reason}</div>)}
        </div>
      </div>
    </div>
  );
}