import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAppMode } from "../store/appMode";

export default function Settings() {
  const [h, setH] = useState<any>(null);
  const [err, setErr] = useState("");
  const { mode, setMode } = useAppMode();
  useEffect(() => { api.health().then(setH).catch(() => setErr("Inspection service is unreachable.")); }, []);
  const ocrOk = h?.providers?.tesseract?.available;
  const dbOk = !!h && !err;
  const dot = (ok: boolean | undefined) => (
    <span className={`inline-block h-2 w-2 rounded-full ${ok ? "bg-emerald-400" : "bg-red-400"}`} aria-hidden />
  );
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h2 className="text-3xl font-extrabold tracking-tight">Settings</h2>
      <section className="glass p-5" aria-label="Application mode">
        <h3 className="font-bold">Application Mode</h3>
        <p className="mt-1 text-sm text-slate-400">Live Mode is the default. Demo Mode loads clearly-labelled simulated records for presentations — never mixed with real data.</p>
        <div className="mt-3 grid gap-2 md:grid-cols-2" role="radiogroup" aria-label="Application mode">
          {(["live", "demo"] as const).map((m) => (
            <button key={m} role="radio" aria-checked={mode === m} onClick={() => setMode(m)}
              className={`rounded-xl border p-4 text-left ${mode === m ? "border-indigo-400/60 bg-indigo-500/10" : "border-white/10 hover:bg-white/5"}`}>
              <div className="font-bold">{m === "live" ? "○ Live Mode" : "○ Demo Mode"}</div>
              <div className="text-xs text-slate-400">{m === "live" ? "Real inspections, real pipeline." : "Simulated data for demonstration."}</div>
            </button>
          ))}
        </div>
      </section>
      <section className="glass space-y-2 p-5 text-sm" aria-label="System status">
        <h3 className="font-bold">System Status</h3>
        {err && <p className="text-red-300">{err}</p>}
        <div className="flex items-center gap-2">{dot(ocrOk)} OCR Service <span className="text-slate-400">— {ocrOk ? "Available" : "Unavailable"}</span></div>
        <div className="flex items-center gap-2">{dot(dbOk)} Database <span className="text-slate-400">— {dbOk ? "Connected" : "Unreachable"}</span></div>
        <div className="flex items-center gap-2">{dot(dbOk)} Rule Engine <span className="text-slate-400">— {dbOk ? "Active" : "Unknown"}</span></div>
      </section>
    </div>
  );
}
