const BASE = import.meta.env.VITE_API_BASE || "";
async function req(path: string, opts: RequestInit = {}) {
  const r = await fetch(BASE + path, opts);
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || `Request failed ${r.status}`);
  }
  const ct = r.headers.get("content-type") || "";
  return ct.includes("application/json") ? r.json() : r.text();
}
export const api = {
  health: () => req("/api/health"),
  rules: () => req("/api/rules"),
  createInspection: (body: any) =>
    req("/api/inspections", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  upload: (id: string, file: File) => {
    const fd = new FormData(); fd.append("file", file);
    return req(`/api/inspections/${id}/upload`, { method: "POST", body: fd });
  },
  analyze: (id: string) => req(`/api/inspections/${id}/analyze`, { method: "POST" }),
  get: (id: string) => req(`/api/inspections/${id}`),
  list: (params = "", demo?: "live" | "demo") => {
    const sep = params ? "&" : "?";
    const scope = demo ? `${params ? params : "?"}${params ? sep : ""}demo=${demo === "demo" ? "true" : "false"}` : params;
    return req(`/api/inspections${scope}`);
  },
  evidence: (id: string) => req(`/api/inspections/${id}/evidence`),
  review: (id: string, body: any) =>
    req(`/api/inspections/${id}/review`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  stats: (demo?: "live" | "demo") =>
    req(`/api/dashboard/stats${demo ? `?demo=${demo === "demo" ? "true" : "false"}` : ""}`),
  auditOne: (id: string) => req(`/api/audit/${id}`),
  auditAll: (demo?: "live" | "demo") =>
    req(`/api/audit${demo ? `?demo=${demo === "demo" ? "true" : "false"}` : ""}`),
  imageUrl: (imageId: string) => `${BASE}/api/images/${imageId}`,
  genReport: (id: string) => req(`/api/inspections/${id}/reports`, { method: "POST" }),
  reportUrl: (id: string) => `${BASE}/api/inspections/${id}/report.pdf`,
  findings: (id: string) => req(`/api/inspections/${id}/findings`),
  resolveFinding: (id: string, fid: string, body: any) =>
    req(`/api/inspections/${id}/findings/${fid}/resolve`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  attention: (demo?: "live" | "demo") =>
    req(`/api/dashboard/attention${demo ? `?demo=${demo === "demo" ? "true" : "false"}` : ""}`),
  compare: (ids: string[]) => req(`/api/inspections/compare?ids=${ids.map(encodeURIComponent).join(",")}`),
};
export function statusBadge(s: string) {
  if (s === "COMPLIANT") return "badge-compliant";
  if (s === "POTENTIAL_VIOLATION") return "badge-violation";
  if (s === "REVIEW_REQUIRED") return "badge-review";
  return "badge-pending";
}
export function statusLabel(s: string) {
  if (s === "COMPLIANT") return "Compliant screening";
  if (s === "POTENTIAL_VIOLATION") return "Potential violation";
  if (s === "REVIEW_REQUIRED") return "Review required";
  return s || "Pending";
}

/** Inspector-facing errors: never leak URLs, paths, or stack traces. */
export function friendlyError(e: any, what = "request"): string {
  const raw = String(e?.message || e || "");
  if (/failed to fetch|networkerror|network error/i.test(raw))
    return "Unable to reach the inspection service. Please check the connection and try again.";
  if (/^4\d\d/.test(raw) || /not found/i.test(raw))
    return "The requested inspection could not be found. It may have been removed.";
  if (/503|ocr.*unavailable/i.test(raw))
    return "Live OCR is currently unavailable. Please check the inspection service and try again, or use Demo Mode for a guided demonstration.";
  if (/502|analysis unavailable/i.test(raw))
    return "Unable to analyze the image. Please check the inspection service and try again.";
  if (/too large|max/i.test(raw) && /mb/i.test(raw))
    return "The image is too large. Please use an image under 10 MB.";
  if (/invalid file|unsupported/i.test(raw))
    return "That file type is not supported. Please use JPG, PNG, or WebP.";
  // eslint-disable-next-line no-console
  if (typeof console !== "undefined") console.error(`[${what}]`, raw.slice(0, 500));
  return "Something went wrong. Please try again.";
}
