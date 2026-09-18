import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";

const STEPS = [
  ["01", "SCAN", "Capture the package label with guided camera framing."],
  ["02", "EXTRACT", "OCR reads declarations into structured fields with confidence."],
  ["03", "CHECK", "Versioned rules screen every required declaration."],
  ["04", "VERIFY", "The officer reviews evidence and confirms findings."],
  ["05", "REPORT", "An auditable screening report is generated."],
];

/** Purely illustrative product visual — not connected to any inspection data. */
function HeroIllustration() {
  return (
    <div className="hero-illus" aria-hidden="true" role="presentation" aria-label="Illustrative inspection visual">
      <div className="hero-pkg float-slow">
        <div className="hero-pkg-title">PACKAGE LABEL</div>
        <div className="hero-ocrbox b1"><span>MRP ₹120</span></div>
        <div className="hero-ocrbox b2"><span>NET QTY 500 g</span></div>
        <div className="hero-scanbeam" />
      </div>
      <div className="hero-tag t1 float-a">OCR 96%</div>
      <div className="hero-tag t2 float-b">FIELDS 11</div>
      <div className="hero-tag t3 float-a">RULES VERIFIED</div>
      <div className="hero-tag t4 float-b">EVIDENCE READY</div>
    </div>
  );
}

function Reveal({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (es) => es.forEach((e) => { if (e.isIntersecting) { el.classList.add("revealed"); io.disconnect(); } }),
      { threshold: 0.2 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return <div ref={ref} className="reveal" style={{ transitionDelay: `${delay}ms` }}>{children}</div>;
}

export default function Landing() {
  const heroRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const el = heroRef.current;
    if (!el) return;
    const onMove = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      el.style.setProperty("--mx", `${((e.clientX - r.left) / r.width) * 100}%`);
      el.style.setProperty("--my", `${((e.clientY - r.top) / r.height) * 100}%`);
    };
    el.addEventListener("pointermove", onMove);
    return () => el.removeEventListener("pointermove", onMove);
  }, []);

  return (
    <div className="space-y-14">
      <section ref={heroRef} className="hero-reactive relative overflow-hidden rounded-3xl border border-white/10 px-6 py-14 md:py-20">
        <div className="hero-grid absolute inset-0" aria-hidden />
        <div className="relative z-10 grid items-center gap-10 lg:grid-cols-2">
          <div>
            <p className="mb-3 inline-block rounded-full border border-indigo-400/30 bg-indigo-500/10 px-3 py-1 text-[11px] font-bold tracking-[0.25em] text-indigo-200">
              LEGAL METROLOGY • AI-ASSISTED INSPECTION
            </p>
            <h1 className="text-4xl font-extrabold leading-[1.05] tracking-tight md:text-6xl">
              Inspect smarter.<br /><span className="wave-text">Verify with evidence.</span>
            </h1>
            <p className="mt-4 max-w-xl text-slate-300">
              AI-assisted packaged commodity compliance screening for faster inspection, structured evidence, and officer verification.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link to="/scan" className="btn-primary">Start Inspection</Link>
              <Link to="/dashboard" className="btn-ghost">Explore Workflow</Link>
            </div>
          </div>
          <HeroIllustration />
        </div>
      </section>

      <section aria-label="Workflow">
        <Reveal>
          <h2 className="text-center text-2xl font-extrabold tracking-tight">From capture to auditable report</h2>
        </Reveal>
        <div className="workflow mt-6 grid gap-3 md:grid-cols-5">
          {STEPS.map(([n, t, d], i) => (
            <Reveal key={t} delay={i * 90}>
              <div className="glass workflow-step relative h-full p-4">
                <div className="text-[11px] font-bold tracking-[0.25em] text-cyan-300/80">{n}</div>
                <div className="mt-1 font-extrabold tracking-wide">{t}</div>
                <p className="mt-1 text-xs leading-relaxed text-slate-400">{d}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      <section aria-label="Illustrative artifacts">
        <Reveal>
          <h2 className="text-center text-2xl font-extrabold tracking-tight">What an inspection produces</h2>
          <p className="mt-1 text-center text-xs text-slate-500">Illustrative mock artifacts — not real inspection records.</p>
        </Reveal>
        <div className="tunnel mt-4 overflow-hidden rounded-3xl border border-white/10" aria-hidden="true">
          <div className="tunnel-inner flex items-stretch justify-between gap-2 px-8 py-10 text-center text-[11px] tracking-widest text-indigo-200">
            {["PACKAGE IMAGE", "OCR LAYER", "EXTRACTED FIELDS", "COMPLIANCE RESULT", "EVIDENCE"].map((s) => (
              <div key={s} className="rounded-lg border border-white/10 bg-black/40 px-3 py-4">{s}</div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {[
          ["Deterministic rules", "Versioned PASS / FAIL / REVIEW checks. AI reads, rules decide — never the reverse."],
          ["Image evidence", "Bounding boxes link MRP, quantity and maker to the label photo; text evidence otherwise."],
          ["Officer review", "Edit, verify, confirm or mark false-positive. Originals preserved, full audit trail."],
        ].map(([t, d], i) => (
          <Reveal key={t} delay={i * 80}>
            <div className="glass feat-card h-full p-5">
              <h3 className="font-bold">{t}</h3>
              <p className="mt-1 text-sm text-slate-300">{d}</p>
            </div>
          </Reveal>
        ))}
      </section>
    </div>
  );
}
