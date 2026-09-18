import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, friendlyError } from "../api/client";
import { useAppMode } from "../store/appMode";

type ScanTab = "camera" | "upload";
/** Single authoritative camera state — no scattered booleans. */
type CameraState =
  | "idle" | "starting" | "scanning" | "capturing" | "captured"
  | "quality" | "analyzing" | "error" | "cancelled";

const ACCEPT = "image/jpeg,image/jpg,image/png,image/webp";
const VIDEO_STATES: CameraState[] = ["starting", "scanning", "capturing"];

function validImage(f: File): string {
  if (!["image/jpeg", "image/jpg", "image/png", "image/webp"].includes(f.type)) return "Unsupported type. Use JPG / PNG / WebP.";
  if (f.size > 10 * 1024 * 1024) return "File too large. Max 10 MB.";
  return "";
}

type Quality = {
  width: number; height: number; brightness: number; contrast: number; blur: number;
  warnings: string[];
};

/** Real, computed image-quality signals (advisory only — never blocks). */
function measureQuality(blob: Blob): Promise<Quality> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob);
    const img = new Image();
    img.onload = () => {
      try {
        const W = 160, H = Math.max(1, Math.round((160 * img.height) / img.width));
        const cv = document.createElement("canvas");
        cv.width = W; cv.height = H;
        const ctx = cv.getContext("2d", { willReadFrequently: true });
        if (!ctx) throw new Error("no 2d context");
        ctx.drawImage(img, 0, 0, W, H);
        const d = ctx.getImageData(0, 0, W, H).data;
        const luma: number[] = [];
        for (let i = 0; i < d.length; i += 4) luma.push(0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]);
        const mean = luma.reduce((a, b) => a + b, 0) / luma.length;
        const variance = luma.reduce((a, b) => a + (b - mean) ** 2, 0) / luma.length;
        const contrast = Math.sqrt(variance);
        // Laplacian variance (blur proxy) on the downscaled luma grid
        let lap = 0, lapMean = 0; const laps: number[] = [];
        for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
          const i = y * W + x;
          const v = luma[i - 1] + luma[i + 1] + luma[i - W] + luma[i + W] - 4 * luma[i];
          laps.push(v); lapMean += v;
        }
        lapMean /= Math.max(1, laps.length);
        lap = laps.reduce((a, b) => a + (b - lapMean) ** 2, 0) / Math.max(1, laps.length);
        const warnings: string[] = [];
        if (mean < 45) warnings.push("Image is dark — add light and retake if text is hard to read.");
        if (contrast < 22) warnings.push("Image has low contrast — avoid glare and shadows.");
        if (lap < 60) warnings.push("Image may be blurry — hold steady and retake.");
        URL.revokeObjectURL(url);
        resolve({ width: img.width, height: img.height, brightness: Math.round(mean), contrast: Math.round(contrast), blur: Math.round(lap), warnings });
      } catch (e) { URL.revokeObjectURL(url); reject(e); }
    };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("Could not decode captured image.")); };
    img.src = url;
  });
}

const STAGES = ["Image received", "OCR extraction", "Field structuring", "Rule screening", "Evidence mapping"];

type KeptFrame = { blob: Blob; url: string; w: number; h: number; hash: string; verdict: string; dupOf: number };

/** Deterministic duplicate detection: 64-bit dHash over a 9×8 grayscale thumb. */
function dhashFromBlob(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob);
    const img = new Image();
    img.onload = () => {
      try {
        const cv = document.createElement("canvas");
        cv.width = 9; cv.height = 8;
        const ctx = cv.getContext("2d", { willReadFrequently: true });
        if (!ctx) throw new Error("no ctx");
        ctx.drawImage(img, 0, 0, 9, 8);
        const d = ctx.getImageData(0, 0, 9, 8).data;
        const g: number[] = [];
        for (let i = 0; i < d.length; i += 4) g.push(0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]);
        let bits = "";
        for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x++)
          bits += g[y * 9 + x] > g[y * 9 + x + 1] ? "1" : "0";
        let hex = "";
        for (let i = 0; i < 64; i += 4) hex += parseInt(bits.slice(i, i + 4), 2).toString(16);
        URL.revokeObjectURL(url);
        resolve(hex);
      } catch (e) { URL.revokeObjectURL(url); reject(e); }
    };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("decode")); };
    img.src = url;
  });
}
function hamming(a: string, b: string): number {
  let n = 0;
  for (let i = 0; i < Math.min(a.length, b.length); i++)
    n += ((parseInt(a[i], 16) ^ parseInt(b[i], 16)).toString(2).match(/1/g) || []).length;
  return n;
}

export default function Scan() {
  const [tab, setTab] = useState<ScanTab>("camera");
  const [product, setProduct] = useState("");
  const [hint, setHint] = useState("compliant");
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const [stage, setStage] = useState(0);
  const nav = useNavigate();
  const { mode, isDemo } = useAppMode();

  // ---- camera (single state machine) ----
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const startIdRef = useRef(0);
  const [camState, setCamState] = useState<CameraState>("idle");
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [videoReady, setVideoReady] = useState(false);
  const [camErr, setCamErr] = useState("");
  const [camInfo, setCamInfo] = useState({ facing: "", resolution: "" });
  const [videoStats, setVideoStats] = useState("");
  const [captured, setCaptured] = useState<{ blob: Blob; url: string; w: number; h: number } | null>(null);
  const [quality, setQuality] = useState<Quality | null>(null);
  const [deviceIds, setDeviceIds] = useState<string[]>([]);
  const [deviceIdx, setDeviceIdx] = useState(0);
  // Smart Scan session: useful frames the system retains across captures.
  const [session, setSession] = useState<KeptFrame[]>([]);
  const [guidance, setGuidance] = useState("Center the package label inside the frame.");
  const lastKeptRef = useRef<string | null>(null);

  const stopTracks = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => { try { t.stop(); } catch { /* noop */ } });
    streamRef.current = null;
    setStream(null);
    if (videoRef.current) videoRef.current.srcObject = null;
    setVideoReady(false);
    setVideoStats("");
  }, []);

  const toIdle = useCallback(() => {
    startIdRef.current += 1; // invalidate any in-flight start
    stopTracks();
    setCamState("idle");
    setCamErr("");
  }, [stopTracks]);

  // Attach stream to the (always-mounted during video states) video element.
  useEffect(() => {
    const v = videoRef.current;
    if (!v || !stream) return;
    v.muted = true;
    (v as any).playsInline = true;
    v.srcObject = stream;
    let live = true;
    const onMeta = () => { if (live) { setVideoReady(v.videoWidth > 0); } };
    v.addEventListener("loadedmetadata", onMeta);
    v.play().then(() => {
      if (!live) return;
      setVideoReady(v.videoWidth > 0);
      const t = stream.getVideoTracks()[0];
      const s: any = t?.getSettings?.() || {};
      setCamInfo({
        facing: s.facingMode ? String(s.facingMode) : (deviceIds.length > 1 ? `Camera ${deviceIdx + 1} of ${deviceIds.length}` : "Available camera"),
        resolution: s.width && s.height ? `${s.width}×${s.height}` : (v.videoWidth ? `${v.videoWidth}×${v.videoHeight}` : ""),
      });
    }).catch(() => { if (live) setCamErr("Camera stream could not be played by this browser."); });
    const watchdog = window.setTimeout(() => {
      if (live && !(videoRef.current && videoRef.current.videoWidth > 0)) {
        setVideoStats(`readyState=${v.readyState} video=${v.videoWidth}×${v.videoHeight} track=${stream.getVideoTracks()[0]?.readyState}`);
      }
    }, 8000);
    return () => { live = false; v.removeEventListener("loadedmetadata", onMeta); window.clearTimeout(watchdog); };
  }, [stream, deviceIds.length, deviceIdx]);

  // Unmount + tab-leave cleanup: no leaked streams, no stray animation.
  useEffect(() => () => { startIdRef.current += 1; stopTracks(); }, [stopTracks]);
  useEffect(() => {
    if (tab !== "camera") { toIdle(); setCaptured((o) => { if (o) URL.revokeObjectURL(o.url); return null; }); setQuality(null); }
  }, [tab, toIdle]);

  async function startCamera(devIdx?: number) {
    const myStart = ++startIdRef.current;
    setCamErr(""); setQuality(null);
    setCaptured((o) => { if (o) URL.revokeObjectURL(o.url); return null; });
    if (!navigator.mediaDevices?.getUserMedia) {
      setCamState("error");
      setCamErr("Camera API unavailable in this browser. Use HTTPS or a modern browser, or upload an image instead.");
      return;
    }
    setCamState("starting");
    try {
      const devices = await navigator.mediaDevices.enumerateDevices().catch(() => [] as MediaDeviceInfo[]);
      const vids = devices.filter((d) => d.kind === "videoinput");
      if (myStart !== startIdRef.current) return; // cancelled while enumerating
      setDeviceIds(vids.map((d) => d.deviceId).filter(Boolean));
      const idx = devIdx ?? deviceIdx;
      const wantId = vids.map((d) => d.deviceId).filter(Boolean)[idx];
      const constraints: MediaStreamConstraints = {
        audio: false,
        video: wantId
          ? { deviceId: { exact: wantId }, width: { ideal: 1920 }, height: { ideal: 1080 } }
          : { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } },
      };
      const s = await navigator.mediaDevices.getUserMedia(constraints);
      if (myStart !== startIdRef.current) { s.getTracks().forEach((t) => t.stop()); return; } // cancelled mid-request
      streamRef.current = s;
      setStream(s);
      setCamState("scanning"); // scan beam tied to this state only
    } catch (e: any) {
      if (myStart !== startIdRef.current) return;
      // deviceId exact may fail on some browsers → retry with facingMode
      if (e?.name === "OverconstrainedError") {
        try {
          const s = await navigator.mediaDevices.getUserMedia({ audio: false, video: { facingMode: { ideal: "environment" } } });
          if (myStart !== startIdRef.current) { s.getTracks().forEach((t) => t.stop()); return; }
          streamRef.current = s; setStream(s); setCamState("scanning"); return;
        } catch { /* fall through to error */ }
      }
      setCamState("error");
      const n = e?.name || "";
      setCamErr(
        n === "NotAllowedError" || n === "SecurityError"
          ? "Camera permission denied. Allow camera access in the browser address bar, then retry — or upload an image instead."
          : n === "NotFoundError" || n === "DevicesNotFoundError"
            ? "No camera device found on this device. Please upload an image instead."
            : n === "NotReadableError" || n === "TrackStartError"
              ? "Camera is busy or unavailable. Close other apps using it and retry — or upload an image instead."
              : `Camera unavailable (${n || "unknown error"}). Check HTTPS/device support, or upload an image instead.`
      );
    }
  }

  function cancelCamera(e?: React.SyntheticEvent) {
    e?.preventDefault?.();
    toIdle();
    setCaptured((o) => { if (o) URL.revokeObjectURL(o.url); return null; });
    setQuality(null);
    setCamState("idle");
  }

  async function switchCamera() {
    if (deviceIds.length < 2 && !stream) { await startCamera(); return; }
    const next = deviceIds.length > 1 ? (deviceIdx + 1) % deviceIds.length : deviceIdx + 1;
    setDeviceIdx(next);
    stopTracks();
    await startCamera(next);
  }

  function captureFrame() {
    const video = videoRef.current;
    // Root-cause guard: never capture from an unready element (prevents black frames).
    if (!video || video.readyState < 2 || video.videoWidth === 0) {
      setCamErr("Camera feed is not ready yet — wait a moment and try again.");
      return;
    }
    setCamState("capturing"); // scan beam unmounts immediately (tied to "scanning" only)
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth; // full sensor resolution, not CSS size
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) { setCamState("scanning"); return; }
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(async (blob) => {
      stopTracks(); // stream ends the moment the frame is frozen
      if (!blob) { setCamState("scanning"); return; }
      const url = URL.createObjectURL(blob);
      setCaptured((o) => { if (o) URL.revokeObjectURL(o.url); return { blob, url, w: canvas.width, h: canvas.height }; });
      setCamState("quality");
      // Smart Scan: automatically retain the frame with a measured verdict.
      try {
        const [q, hash] = await Promise.all([measureQuality(blob), dhashFromBlob(blob).catch(() => "")]);
        setQuality(q);
        setSession((prev) => {
          let dupOf = -1;
          if (hash) {
            for (let i = 0; i < prev.length; i++) {
              if (prev[i].hash && hamming(prev[i].hash, hash) < 6) { dupOf = i; break; }
            }
          }
          const verdict = q.warnings.length ? "Needs attention" : "Good";
          lastKeptRef.current = url;
          const next = [...prev, { blob, url, w: canvas.width, h: canvas.height, hash, verdict, dupOf }];
          setGuidance(
            dupOf >= 0 ? `View ${next.length} looks like view ${dupOf + 1} — rotate the package to capture a different surface.`
            : next.length === 1 ? "View 1 kept. Rotate the package — back panel next."
            : "Sufficient label coverage — analyze when ready, or add more views."
          );
          return next;
        });
        setCamState("captured");
      } catch {
        setQuality(null);
        setCamState("captured");
      }
    }, "image/jpeg", 0.93);
  }

  function retake() {
    // Remove the session frame this capture added, then restart the camera.
    const url = lastKeptRef.current;
    if (url) {
      setSession((prev) => {
        const victim = prev.find((f) => f.url === url);
        if (victim) URL.revokeObjectURL(victim.url);
        return prev.filter((f) => f.url !== url);
      });
      lastKeptRef.current = null;
    }
    setCaptured((o) => { if (o) URL.revokeObjectURL(o.url); return null; });
    setQuality(null);
    setGuidance("Center the package label inside the frame.");
    startCamera();
  }

  function removeSessionFrame(url: string) {
    setSession((prev) => {
      const victim = prev.find((f) => f.url === url);
      if (victim) URL.revokeObjectURL(victim.url);
      if (lastKeptRef.current === url) lastKeptRef.current = null;
      return prev.filter((f) => f.url !== url);
    });
  }

  // ---- upload state ----
  const [files, setFiles] = useState<{ file: File; url: string }[]>([]);
  function addFiles(list: FileList | null) {
    if (!list) return;
    setErr("");
    const next = [...files];
    for (const f of Array.from(list)) {
      const problem = validImage(f);
      if (problem) { setErr(`${f.name}: ${problem}`); continue; }
      next.push({ file: f, url: URL.createObjectURL(f) });
    }
    setFiles(next);
  }
  function removeFile(url: string) {
    setFiles((fs) => {
      const victim = fs.find((x) => x.url === url);
      if (victim) URL.revokeObjectURL(victim.url);
      return fs.filter((x) => x.url !== url);
    });
  }

  async function runAnalysis(images: { blob: Blob; name: string }[]) {
    if (!images.length) { setErr("No image to analyze yet."); return; }
    try {
      setErr(""); setCamState((s) => (tab === "camera" ? "analyzing" : s));
      setStage(0); setBusy("Creating inspection…");
      const insp = await api.createInspection({
        officer_email: "officer@gov.in",
        product_name: product.trim(),
        is_demo: isDemo,
        demo_hint: isDemo ? hint : "",
      });
      for (let i = 0; i < images.length; i++) {
        setStage(1);
        setBusy(`Uploading image ${i + 1} of ${images.length}…`);
        const img = images[i];
        await api.upload(insp.id, new File([img.blob], img.name, { type: img.blob.type || "image/jpeg" }));
      }
      setStage(2); setBusy("OCR extraction running…");
      const res = await api.analyze(insp.id);
      setStage(4); setBusy("Preparing result…");
      const previewUrl = URL.createObjectURL(images[0].blob);
      setBusy("");
      if (tab === "camera") { toIdle(); }
      setSession((prev) => { prev.forEach((f) => URL.revokeObjectURL(f.url)); return []; });
      lastKeptRef.current = null;
      nav(`/inspections/${insp.id}/result`, {
        state: { preloaded: res, preview: previewUrl, appMode: mode },
      });
    } catch (e: any) {
      setBusy("");
      setErr(friendlyError(e, "analysis"));
      if (tab === "camera") setCamState(captured ? "captured" : "idle");
    }
  }

  const showVideo = tab === "camera" && VIDEO_STATES.includes(camState);
  const analyzing = camState === "analyzing" && !!busy;

  return (
    <div className="mx-auto max-w-6xl space-y-5 page-enter">
      <div>
        <p className="text-[11px] font-bold tracking-[0.25em] text-cyan-300/80">CAPTURE → ANALYZE → REVIEW → REPORT</p>
        <h2 className="mt-1 text-3xl font-extrabold tracking-tight">New Inspection</h2>
        <p className="mt-1 text-sm text-slate-400">Capture or upload packaged commodity labels for AI-assisted compliance screening.</p>
        {isDemo && (
          <p className="mt-2 inline-block rounded-full border border-amber-400/40 bg-amber-400/10 px-3 py-1 text-xs font-semibold text-amber-200">
            DEMO MODE — extraction is simulated (Demo OCR), records labelled DEMO
          </p>
        )}
      </div>

      <label className="block max-w-xl text-sm text-slate-300">
        Product name <span className="text-slate-500">(optional)</span>
        <input className="input mt-1" value={product} onChange={(e) => setProduct(e.target.value)} placeholder="e.g. Whole Wheat Atta 5 kg" />
      </label>

      {isDemo && (
        <label className="block max-w-sm text-sm text-slate-300">
          Demo scenario <span className="text-amber-200">(Demo Mode only)</span>
          <select className="input mt-1" value={hint} onChange={(e) => setHint(e.target.value)}>
            <option value="compliant">Compliant sample</option>
            <option value="violation">Potential violation sample</option>
            <option value="review">Review-required sample</option>
          </select>
        </label>
      )}

      <div className="grid gap-3 sm:grid-cols-2" role="tablist" aria-label="Input method">
        <button type="button" role="tab" aria-selected={tab === "camera"}
          onClick={() => setTab("camera")}
          className={`tab-card rounded-2xl border p-5 text-left transition ${tab === "camera" ? "border-cyan-400/50 bg-cyan-500/[0.07]" : "border-white/10 bg-white/[0.03] hover:bg-white/[0.06]"}`}>
          <div className="text-lg font-bold">Scan with Camera</div>
          <div className="text-sm text-slate-400">Capture product label live</div>
        </button>
        <button type="button" role="tab" aria-selected={tab === "upload"}
          onClick={() => setTab("upload")}
          className={`tab-card rounded-2xl border p-5 text-left transition ${tab === "upload" ? "border-cyan-400/50 bg-cyan-500/[0.07]" : "border-white/10 bg-white/[0.03] hover:bg-white/[0.06]"}`}>
          <div className="text-lg font-bold">Upload Images</div>
          <div className="text-sm text-slate-400">Upload product / label photos</div>
        </button>
      </div>

      {tab === "camera" ? (
        <section className="glass overflow-hidden" aria-label="Camera workspace">
          <div className="grid lg:grid-cols-[1fr_260px]">
            {/* ---- main camera pane ---- */}
            <div className="p-4 sm:p-5">
              <div className="mb-3 flex items-center gap-2 text-xs">
                <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-bold tracking-widest ${camState === "scanning" ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-200" : "border-white/15 text-slate-300"}`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${camState === "scanning" ? "bg-emerald-300 animate-pulse" : "bg-slate-500"}`} />
                  {camState === "scanning" ? "CAMERA ACTIVE" : camState.toUpperCase().replace("_", " ")}
                </span>
                {isDemo
                  ? <span className="rounded-full border border-amber-400/40 bg-amber-400/10 px-2 py-0.5 font-bold text-amber-200">DEMO</span>
                  : <span className="rounded-full border border-cyan-400/40 bg-cyan-400/10 px-2 py-0.5 font-bold text-cyan-200">LIVE</span>}
              </div>

              {camState === "idle" && !captured && (
                <div className="py-10 text-center">
                  <div className="cam-idle-illus mx-auto mb-4" aria-hidden />
                  <p className="text-sm text-slate-300">Live camera preview appears here. Permission is requested only when you start.</p>
                  <button type="button" className="btn-primary mt-4" onClick={() => startCamera()}>Start Camera</button>
                </div>
              )}

              {camState === "starting" && (
                <div className="py-10 text-center" role="status">
                  <div className="shimmer mx-auto mb-4 h-40 max-w-md rounded-xl" />
                  <p className="animate-pulse text-sm text-indigo-200">Requesting camera… you may be asked for permission.</p>
                  <button type="button" className="btn-ghost mt-4 text-sm" onClick={cancelCamera}>Cancel</button>
                </div>
              )}

              {camState === "error" && (
                <div className="space-y-3 py-6 text-center" role="alert">
                  <p className="text-sm font-bold tracking-widest text-red-300">CAMERA UNAVAILABLE</p>
                  <p className="mx-auto max-w-md text-sm text-slate-300">{camErr || "Your browser could not display the camera feed."}</p>
                  {videoStats && <p className="font-mono text-[11px] text-slate-500">{videoStats}</p>}
                  <div className="flex justify-center gap-2">
                    <button type="button" className="btn-ghost text-sm" onClick={() => startCamera()}>Try Again</button>
                    <button type="button" className="btn-ghost text-sm" onClick={() => setTab("upload")}>Upload Image Instead</button>
                  </div>
                </div>
              )}

              {showVideo && (
                <div>
                  {/* Video element is ALWAYS mounted in these states — the black-preview fix. */}
                  <div className="cam-viewport relative overflow-hidden rounded-xl border border-white/15 bg-black">
                    <video ref={videoRef} playsInline muted autoPlay
                      className="max-h-[52vh] min-h-[280px] w-full object-contain" />
                    {/* darkened surround + corner brackets */}
                    <div className="pointer-events-none absolute inset-0" aria-hidden>
                      <div className="absolute inset-x-6 top-6 bottom-6 rounded-lg shadow-[inset_0_0_0_999px_rgba(2,6,18,0.55)]" />
                      <span className="cam-corner tl" /><span className="cam-corner tr" />
                      <span className="cam-corner bl" /><span className="cam-corner br" />
                    </div>
                    {camState === "scanning" && <div className="scan-line" aria-hidden />}
                    {camState === "capturing" && <div className="absolute inset-0 bg-white/25" aria-hidden />}
                  </div>
                  {!videoReady && camState !== "starting" && (
                    <p className="mt-2 text-center text-xs text-slate-400" role="status">Waiting for video frames…</p>
                  )}
                  <p className="mt-2 text-center text-xs tracking-widest text-slate-400">ALIGN PACKAGE WITH FRAME</p>
                  <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
                    <button type="button" className="btn-ghost text-sm" onClick={switchCamera}>Switch Camera</button>
                    <button type="button" className="btn-capture" onClick={captureFrame}
                      disabled={camState !== "scanning" || !videoReady}
                      aria-label="Capture package photo">
                      <span aria-hidden>●</span> CAPTURE
                    </button>
                    <button type="button" className="btn-ghost text-sm" onClick={cancelCamera}>Cancel</button>
                  </div>
                </div>
              )}

              {(camState === "captured" || camState === "quality" || analyzing) && captured && (
                <div>
                  <p className="mb-2 text-xs font-bold tracking-widest text-emerald-200">IMAGE CAPTURED — {captured.w}×{captured.h}</p>
                  <div className="relative overflow-hidden rounded-xl border border-emerald-400/25">
                    <img src={captured.url} alt="Captured package label" className="max-h-[52vh] w-full object-contain" />
                    {analyzing && <div className="analysis-sweep" aria-hidden />}
                  </div>
                  {camState === "quality" && <p className="mt-2 text-center text-xs text-slate-400">Checking image quality…</p>}
                  {quality && (quality.warnings.length > 0 ? (
                    <div className="mt-2 rounded-xl border border-amber-400/30 bg-amber-400/[0.07] p-3 text-xs text-amber-100" role="note">
                      <b>Image may be difficult to read.</b>
                      <ul className="ml-4 list-disc">{quality.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
                    </div>
                  ) : (
                    <p className="mt-2 text-center text-xs text-emerald-200">Image quality: ready for analysis ({quality.width}×{quality.height}).</p>
                  ))}
                  {analyzing ? (
                    <div className="mt-3 rounded-xl border border-white/10 p-4" role="status" aria-live="polite">
                      <p className="text-sm font-bold tracking-widest text-indigo-200">ANALYZING PACKAGE</p>
                      <ul className="mt-2 space-y-1.5 text-sm">
                        {STAGES.map((s, i) => (
                          <li key={s} className="flex items-center gap-2">
                            <span className={`stage-dot ${i < stage ? "done" : i === stage ? "now" : ""}`} aria-hidden />
                            <span className={i <= stage ? "text-slate-100" : "text-slate-500"}>{s}</span>
                          </li>
                        ))}
                      </ul>
                      <div className="indeterminate mt-3" aria-hidden />
                    </div>
                  ) : (
                    <div className="mt-3 flex flex-wrap justify-center gap-2">
                      <button type="button" className="btn-ghost text-sm" onClick={retake}>Retake</button>
                      <button type="button" className="btn-ghost text-sm" onClick={() => { lastKeptRef.current = null; setCaptured((o) => { if (o) URL.revokeObjectURL(o.url); return null; }); setQuality(null); startCamera(); }}>
                        Keep + capture next view
                      </button>
                      <button type="button" className="btn-primary text-sm" disabled={!!busy}
                        onClick={() => {
                          const frames = session.length > 0
                            ? session.map((f, i) => ({ blob: f.blob, name: `view-${i + 1}.jpg` }))
                            : [{ blob: captured.blob, name: "camera-capture.jpg" }];
                          runAnalysis(frames);
                        }}>
                        Analyze {session.length > 1 ? `${session.length} views` : "Image"}
                      </button>
                    </div>
                  )}
                </div>
              )}
              {session.length > 0 && !analyzing && (
                <div className="mt-4 rounded-xl border border-white/10 p-3" aria-live="polite">
                  <p className="text-[11px] font-bold tracking-widest text-slate-300">
                    SMART SCAN SESSION — {session.length} VIEW{session.length > 1 ? "S" : ""} KEPT
                  </p>
                  <p className="mt-1 text-xs text-cyan-200">{guidance}</p>
                  <div className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-4">
                    {session.map((f, i) => (
                      <div key={f.url} className="relative overflow-hidden rounded-lg border border-white/10">
                        <img src={f.url} alt={`Kept view ${i + 1}`} className="h-20 w-full object-cover" />
                        <span className="absolute left-1 top-1 rounded bg-black/70 px-1 text-[10px] font-bold">V{i + 1}</span>
                        <button type="button" onClick={() => removeSessionFrame(f.url)} aria-label={`Remove view ${i + 1}`}
                          className="absolute right-1 top-1 rounded bg-black/70 px-1.5 text-xs">✕</button>
                        <span className={`absolute bottom-1 left-1 rounded px-1 text-[10px] ${f.dupOf >= 0 ? "bg-amber-500/80 text-black" : f.verdict === "Good" ? "bg-emerald-500/80 text-black" : "bg-amber-500/80 text-black"}`}>
                          {f.dupOf >= 0 ? `Dup of V${f.dupOf + 1}` : f.verdict}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* ---- sidebar (desktop) ---- */}
            <aside className="hidden border-l border-white/10 p-4 text-xs lg:block" aria-label="Capture guidance">
              <h3 className="font-bold tracking-widest text-slate-300">CAPTURE TIPS</h3>
              <ul className="mt-2 space-y-1.5 text-slate-400">
                <li>Keep the label inside the frame</li>
                <li>Use good lighting, avoid glare</li>
                <li>Hold steady until capture</li>
                <li>Fill the frame with the label</li>
              </ul>
              <h3 className="mt-5 font-bold tracking-widest text-slate-300">CAMERA STATUS</h3>
              <dl className="mt-2 space-y-1.5 text-slate-400">
                <div className="flex justify-between gap-2"><dt>Camera</dt><dd className="text-right text-slate-200">{camInfo.facing || "—"}</dd></div>
                <div className="flex justify-between gap-2"><dt>Resolution</dt><dd className="text-right text-slate-200">{camInfo.resolution || (captured ? `${captured.w}×${captured.h}` : "—")}</dd></div>
                <div className="flex justify-between gap-2"><dt>State</dt><dd className="text-right text-slate-200">{camState.toUpperCase()}</dd></div>
              </dl>
              <p className="mt-4 text-slate-500">Preview uses fit-to-frame, so what you see is what gets captured and sent to OCR.</p>
            </aside>
          </div>
        </section>
      ) : (
        <section className="glass p-5" aria-label="File upload">
          <label
            className="block cursor-pointer rounded-xl border border-dashed border-white/20 p-8 text-center text-sm text-slate-300 hover:border-indigo-400/60"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => { e.preventDefault(); addFiles(e.dataTransfer.files); }}
          >
            Drop images here or <span className="text-indigo-300 underline">browse files</span>
            <div className="mt-1 text-xs text-slate-500">JPG / JPEG / PNG / WebP · max 10 MB each · multiple allowed</div>
            <input type="file" accept={ACCEPT} multiple className="hidden" onChange={(e) => { addFiles(e.target.files); e.target.value = ""; }} />
          </label>
          {files.length > 0 && (
            <div className="mt-3">
              <div className="mb-2 text-xs text-slate-400">{files.length} image{files.length > 1 ? "s" : ""} selected</div>
              <div className="grid grid-cols-3 gap-2 md:grid-cols-5">
                {files.map((f) => (
                  <div key={f.url} className="img-thumb relative overflow-hidden rounded-lg border border-white/10">
                    <img src={f.url} alt={f.file.name} className="h-24 w-full object-cover" />
                    <button type="button" onClick={() => removeFile(f.url)} aria-label={`Remove ${f.file.name}`} className="absolute right-1 top-1 rounded bg-black/70 px-1.5 text-xs">✕</button>
                  </div>
                ))}
              </div>
              <button type="button" className="btn-primary mt-4 w-full" disabled={!!busy} onClick={() => runAnalysis(files.map((f) => ({ blob: f.file, name: f.file.name })))}>
                {busy ? "Processing…" : `Analyze ${files.length} image${files.length > 1 ? "s" : ""}`}
              </button>
            </div>
          )}
        </section>
      )}

      {busy && tab === "upload" && (
        <div className="glass p-4" role="status">
          <div className="animate-pulse text-sm text-indigo-200">{busy}</div>
          <div className="indeterminate mt-2" aria-hidden />
        </div>
      )}
      {err && <div className="glass border-red-500/30 p-4 text-sm text-red-300" role="alert">{err}</div>}
      <p className="text-xs text-slate-500">
        {isDemo ? "Demo Mode: deterministic simulated extraction, clearly labelled DEMO DATA." : "Live Mode: image goes through the real analysis pipeline (OCR provider as configured on the server)."}
      </p>
    </div>
  );
}
