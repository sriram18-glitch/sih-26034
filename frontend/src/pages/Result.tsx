import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { api, statusBadge, statusLabel } from "../api/client";
import EvidenceViewer from "../components/EvidenceViewer";

function confTone(c: number, status: string) {
  if (status === "MISSING") return "badge-pending";
  if (status === "UNREADABLE") return "badge-review";
  if (c >= 0.75) return "badge-compliant";
  if (c >= 0.45) return "badge-review";
  return "badge-violation";
}
function confWord(c: number, status: string) {
  if (status === "MISSING") return "NOT DETECTED";
  if (status === "UNREADABLE") return "NEEDS REVIEW";
  if (c >= 0.75) return "HIGH CONFIDENCE";
  if (c >= 0.45) return "MEDIUM — VERIFY";
  return "LOW — VERIFY";
}

export default function Result() {
  const { id } = useParams();
  const loc = useLocation() as any;
  const [data, setData] = useState<any>(loc.state?.preloaded || null);
  const [full, setFull] = useState<any>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [imgIdx, setImgIdx] = useState(0);
  const [openRule, setOpenRule] = useState<string | null>(null);
  const [findings, setFindings] = useState<any[] | null>(null);
  const [coverage, setCoverage] = useState<any[] | null>(null);
  const [attention, setAttention] = useState<any>(null);

  useEffect(() => {
    if (id && !data) {
      api.analyze(id).then(setData).catch(() => api.get(id).then(setFull));
    }
    if (id) {
      api.get(id).then(setFull).catch(() => {});
      api.findings(id).then(setFindings).catch(() => setFindings([]));
    }
  }, [id]);

  useEffect(() => {
    if (data?.findings) setFindings(data.findings);
    if (data?.coverage) setCoverage(data.coverage);
    if (data?.attention) setAttention(data.attention);
  }, [data]);

  const fields = data?.fields ? Object.entries(data.fields).map(([field, v]: any) => ({ field, ...v })) : full?.fields || [];
  const results = data?.results || full?.results || [];
  const overall = data?.overall || full?.overall || "PENDING";
  const provider = data?.provider || full?.provider || "";
  const isDemoProvider = provider.includes("demo");
  const isDemoRecord = full?.is_demo ?? (loc.state?.appMode === "demo");
  const imagesProcessed = data?.images_processed ?? (full?.images?.length ?? null);
  const detected = data?.fields_detected ?? fields.filter((f: any) => (f.value || "").trim()).length;
  const needReview = data?.fields_needing_review ?? fields.filter((f: any) => f.status !== "OK" || !(f.value || "").trim()).length;

  const serverImages: { id: string }[] = full?.images || [];
  const previewUrl: string = loc.state?.preview || "";
  const totalImgs = Math.max(serverImages.length, previewUrl ? 1 : 0, Number(imagesProcessed) || 0);
  const activeUrl = previewUrl && (imgIdx === 0 || serverImages.length === 0)
    ? previewUrl
    : serverImages.length > 0
      ? api.imageUrl(serverImages[Math.min(imgIdx, serverImages.length - 1)].id)
      : "";

  return (
    <div className="space-y-6 page-enter">
      <div className="result-hero glass p-5">
        <div className="flex flex-wrap items-center gap-3">
          <div>
            <p className="text-[11px] font-bold tracking-[0.25em] text-cyan-300/80">INSPECTION RESULT</p>
            <h2 className="mt-1 text-3xl font-extrabold tracking-tight">
              {overall === "COMPLIANT" ? "Compliant screening" : overall === "POTENTIAL_VIOLATION" ? "Potential non-compliance" : overall === "REVIEW_REQUIRED" ? "Review required" : "Analysis Result"}
            </h2>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs ${statusBadge(overall)}`}>
            {overall === "COMPLIANT" ? "🟢 " : overall === "POTENTIAL_VIOLATION" ? "🔴 " : "🟠 "}{statusLabel(overall)}
          </span>
          {isDemoRecord && <span className="badge-demo rounded-full px-2.5 py-1 text-[11px] font-bold">DEMO</span>}
          <Link to={`/inspections/${id}`} className="btn-ghost ml-auto text-sm">Open details</Link>
        </div>
        <p className="mt-2 text-xs text-slate-400">
          AI-assisted screening — officer verification required.
          {provider && <span className="ml-1">Extraction: <b>OCR confidence</b> via {isDemoProvider ? "Demo / Simulated OCR" : "Live OCR / Vision"}.</span>}
        </p>
      </div>

      <section className="glass p-4" aria-label="Analysis summary">
        <h3 className="mb-2 text-sm font-bold tracking-widest text-slate-300">ANALYSIS</h3>
        <div className="grid grid-cols-2 gap-2 text-sm md:grid-cols-5">
          <div><div className="metric-number">{imagesProcessed ?? "—"}</div><div className="metric-label">Images processed</div></div>
          <div><div className="metric-number">{isDemoProvider ? "Demo" : "Live"}</div><div className="metric-label">OCR provider</div></div>
          <div><div className="metric-number">{detected}</div><div className="metric-label">Fields detected</div></div>
          <div><div className="metric-number">{needReview}</div><div className="metric-label">Fields needing review</div></div>
          <div><div className="metric-number">{attention ? attention.level : (findings ? (findings.some((f: any) => f.level === "HIGH" && f.status === "OPEN") ? "HIGH" : "—") : "—")}</div><div className="metric-label">Attention</div></div>
        </div>
      </section>

      {findings && findings.length > 0 && (
        <section className="space-y-2" aria-label="Cross-view findings">
          <h3 className="text-2xl font-extrabold tracking-tight">Findings Requiring Review</h3>
          {findings.map((f: any) => (
            <div key={f.id || f.title} className={`glass border-l-4 p-4 ${f.level === "HIGH" ? "border-l-red-400" : "border-l-amber-300"}`}>
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full px-2 py-0.5 text-xs ${f.level === "HIGH" ? "badge-violation" : "badge-review"}`}>
                  {f.level === "HIGH" ? "HIGH ATTENTION" : "REVIEW"}
                </span>
                <b className="text-sm">{f.title}</b>
                {f.status && f.status !== "OPEN" && (
                  <span className="rounded-full px-2 py-0.5 text-xs badge-compliant">{f.status}</span>
                )}
              </div>
              <p className="mt-1 text-sm text-slate-300">{f.detail}</p>
              <div className="mt-2 grid gap-1 text-sm md:grid-cols-2">
                {(f.evidence || f.values || []).map((v: any, i: number) => (
                  <div key={i} className="rounded-lg border border-white/10 p-2 text-xs">
                    <span className="font-mono text-slate-400">view {String(v.image_id || "").slice(0, 8)}</span>
                    <span className="ml-2 font-semibold">{v.value || "—"}</span>
                    {v.confidence != null && <span className="ml-2 text-slate-400">OCR {Math.round(v.confidence * 100)}%</span>}
                  </div>
                ))}
              </div>
              {f.id && f.status === "OPEN" && (
                <div className="mt-2 flex gap-2">
                  <button type="button" className="btn-ghost text-xs"
                    onClick={() => api.resolveFinding(id!, f.id, { actor: "officer@gov.in", decision: "VERIFIED", reason: "verified against images" }).then(() => api.findings(id!).then(setFindings))}>
                    Mark verified
                  </button>
                  <button type="button" className="btn-ghost text-xs"
                    onClick={() => api.resolveFinding(id!, f.id, { actor: "officer@gov.in", decision: "FALSE_POSITIVE", reason: "OCR misread" }).then(() => api.findings(id!).then(setFindings))}>
                    False positive
                  </button>
                </div>
              )}
            </div>
          ))}
        </section>
      )}

      {coverage && coverage.length > 0 && (
        <section className="glass p-4" aria-label="Information coverage">
          <h3 className="mb-2 text-sm font-bold tracking-widest text-slate-300">INFORMATION COVERAGE</h3>
          <div className="flex flex-wrap gap-1.5">
            {coverage.map((c: any) => (
              <span key={c.field} title={`${c.field}: ${c.state}${c.value ? ` — ${c.value}` : ""}`}
                className={`rounded-full px-2 py-0.5 text-[11px] ${c.state === "FOUND" ? "badge-compliant" : c.state === "MISSING" ? "badge-pending" : "badge-review"}`}>
                {c.field}: {c.state.replace("_", " ")}
              </span>
            ))}
          </div>
          <p className="mt-2 text-[11px] text-slate-500">Missing is not a violation by itself — applicability is decided by the verified rules below.</p>
        </section>
      )}

      <div className="grid items-start gap-6 lg:grid-cols-[45%_55%]">
        <div className="glass space-y-3 p-4 lg:sticky lg:top-24">
          <div className="flex items-center gap-2">
            <h3 className="font-bold">Package Image</h3>
            {totalImgs > 1 && (
              <span className="ml-auto flex items-center gap-1 text-xs text-slate-300">
                <button type="button" className="ev-tool" aria-label="Previous image"
                  onClick={() => setImgIdx((i) => (i - 1 + totalImgs) % totalImgs)}>‹</button>
                <span className="tabular-nums" aria-live="polite">IMAGE {imgIdx + 1} / {totalImgs}</span>
                <button type="button" className="ev-tool" aria-label="Next image"
                  onClick={() => setImgIdx((i) => (i + 1) % totalImgs)}>›</button>
              </span>
            )}
          </div>
          {activeUrl ? (
            <EvidenceViewer
              imageUrl={activeUrl}
              boxes={fields.map((f: any) => ({
                field: f.field, value: f.value, bbox: f.bbox,
                highlighted: selected === f.field, selected: selected === f.field,
              }))}
              onFieldHover={setSelected}
              onFieldUnhover={() => setSelected(null)}
              onSelect={(f) => setSelected(f)}
            />
          ) : (
            <div className="flex h-64 items-center justify-center text-sm text-slate-400">No image available</div>
          )}
        </div>

        <div className="glass p-4">
          <h3 className="mb-3 font-bold">Extracted Information <span className="text-xs font-normal text-slate-400">(click a card to locate it on the image)</span></h3>
          <div className="grid gap-2 sm:grid-cols-2">
            {fields.map((f: any) => {
              const c = Number(f.confidence || 0);
              return (
                <button type="button" key={f.field}
                  onClick={() => setSelected((s) => (s === f.field ? null : f.field))}
                  aria-pressed={selected === f.field}
                  className={`field-card rounded-xl border p-3 text-left transition ${selected === f.field ? "border-cyan-400/60 bg-cyan-500/[0.08]" : "border-white/10 bg-white/[0.02] hover:border-white/25"}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[11px] font-bold tracking-widest text-slate-400">{f.field}</span>
                    <span className={`rounded-full px-1.5 py-0.5 text-[10px] ${confTone(c, f.status)}`}>{confWord(c, f.status)}</span>
                  </div>
                  <div className="mt-1 truncate text-sm font-semibold text-slate-100" title={f.value || f.status}>{f.value || `— ${f.status}`}</div>
                  {f.normalized && f.normalized !== f.value && (
                    <div className="truncate text-[11px] text-slate-400" title={f.normalized}>Norm: {f.normalized}</div>
                  )}
                  <div className="mt-2 h-1 overflow-hidden rounded bg-white/10" aria-hidden>
                    <div className={`h-full rounded transition-all ${c >= 0.75 ? "bg-emerald-400" : c >= 0.45 ? "bg-amber-300" : "bg-slate-500"}`} style={{ width: `${Math.round(c * 100)}%` }} />
                  </div>
                  <div className="mt-1 flex justify-between text-[10px] text-slate-500">
                    <span>OCR {Math.round(c * 100)}%</span>
                    <span>{f.bbox?.image_id ? `Src: ${String(f.bbox.image_id).slice(0, 8)}` : (f.source_image_id ? `Src: ${String(f.source_image_id).slice(0, 8)}` : f.source || "")}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <h3 className="text-2xl font-extrabold tracking-tight">Compliance Screening</h3>
        {results.map((r: any) => {
          const open = openRule === r.rule_code;
          return (
            <div key={r.rule_code} className="glass overflow-hidden">
              <button type="button" className="flex w-full items-center gap-3 p-4 text-left"
                aria-expanded={open} onClick={() => setOpenRule(open ? null : r.rule_code)}>
                <span className={`rule-dot ${r.status === "PASS" ? "pass" : r.status === "FAIL" ? "fail" : "review"}`} aria-hidden>
                  {r.status === "PASS" ? "✓" : r.status === "FAIL" ? "!" : "?"}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-bold">{r.title || r.rule_code}</span>
                  <span className="block truncate text-xs text-slate-400">{r.rule_code} · v{r.rule_version} · {r.rule_status || "UNVERIFIED"}</span>
                </span>
                <span className={`rounded-full px-2 py-0.5 text-xs ${r.status === "PASS" ? "badge-compliant" : r.status === "FAIL" ? "badge-violation" : "badge-review"}`}>{r.status}</span>
                <span className="text-slate-500" aria-hidden>{open ? "▾" : "▸"}</span>
              </button>
              {open && (
                <div className="grid gap-2 border-t border-white/10 p-4 text-sm md:grid-cols-2">
                  <div><span className="text-slate-400">Observed: </span>{r.observed || "—"}</div>
                  <div><span className="text-slate-400">Expected: </span>{r.expected}</div>
                  <div className="md:col-span-2"><span className="text-slate-400">Why: </span>{r.explanation}</div>
                  <div className="md:col-span-2 text-xs text-slate-400">
                    Ref: {r.source_reference || r.evidence?.source_reference}
                    {r.source_url && <> · <a className="underline" href={r.source_url} target="_blank" rel="noreferrer">official source</a></>}
                    {r.field && fields.some((f: any) => f.field === r.field && f.bbox?.w) && (
                      <> · <button type="button" className="underline" onClick={() => setSelected(r.field)}>View evidence</button></>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="flex flex-wrap gap-2">
        <Link to={`/inspections/${id}`} className="btn-primary text-sm">Review &amp; verify</Link>
      </div>
    </div>
  );
}
