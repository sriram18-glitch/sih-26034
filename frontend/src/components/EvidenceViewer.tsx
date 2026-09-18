import { useState } from "react";

export type EvBox = {
  field: string;
  bbox?: { x: number; y: number; w: number; h: number; image_id?: string };
  value?: string;
  highlighted?: boolean;
  selected?: boolean;
};

export default function EvidenceViewer({
  imageUrl,
  boxes,
  onFieldHover,
  onFieldUnhover,
  onSelect,
  showToggle = true,
}: {
  imageUrl?: string;
  boxes: EvBox[];
  onFieldHover?: (field: string) => void;
  onFieldUnhover?: () => void;
  onSelect?: (field: string | null) => void;
  showToggle?: boolean;
}) {
  const [zoom, setZoom] = useState(1);
  const [showEvidence, setShowEvidence] = useState(true);
  if (!imageUrl) return <div className="glass p-6 text-sm text-slate-300">No image uploaded. Text evidence shown beside.</div>;
  const visible = boxes.filter((b) => b.bbox && (b.bbox.w || 0) > 0);

  return (
    <div className="overflow-hidden rounded-xl border border-white/10 bg-black/40">
      <div className="flex items-center gap-1 border-b border-white/10 px-2 py-1.5 text-xs">
        <button type="button" className="ev-tool" onClick={() => setZoom((z) => Math.max(1, +(z - 0.25).toFixed(2)))} aria-label="Zoom out">−</button>
        <span className="min-w-12 text-center tabular-nums text-slate-300" aria-live="polite">{Math.round(zoom * 100)}%</span>
        <button type="button" className="ev-tool" onClick={() => setZoom((z) => Math.min(3, +(z + 0.25).toFixed(2)))} aria-label="Zoom in">+</button>
        <button type="button" className="ev-tool" onClick={() => setZoom(1)} aria-label="Reset zoom">Reset</button>
        {showToggle && (
          <button type="button" className="ev-tool ml-auto" aria-pressed={showEvidence}
            onClick={() => setShowEvidence((s) => !s)}>
            {showEvidence ? "Hide evidence" : "Show evidence"}
          </button>
        )}
      </div>
      <div className="ev-zoomwrap relative">
        <img src={imageUrl} alt="Package under inspection"
          className="w-full rounded-none object-contain transition-transform duration-200"
          style={{ transform: `scale(${zoom})` }} />
        {showEvidence && visible.map((box, i) => {
          const active = box.selected || box.highlighted;
          return (
            <div
              key={`${box.field}-${i}`}
              role="button" tabIndex={0}
              title={`${box.field}: ${box.value || ""}`}
              aria-label={`Evidence for ${box.field}${box.value ? `: ${box.value}` : ""}`}
              onClick={() => onSelect?.(box.selected ? null : box.field)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect?.(box.selected ? null : box.field); } }}
              onMouseEnter={() => onFieldHover?.(box.field)}
              onMouseLeave={() => onFieldUnhover?.()}
              className={`ev-box ${active ? "ev-active" : ""}`}
              style={{
                left: `${(box.bbox?.x || 0) * 100}%`,
                top: `${(box.bbox?.y || 0) * 100}%`,
                width: `${Math.max(0.02, box.bbox?.w || 0) * 100}%`,
                height: `${Math.max(0.02, box.bbox?.h || 0) * 100}%`,
              }}
            >
              {active && <span className="ev-tag">{box.field}</span>}
            </div>
          );
        })}
      </div>
      <p className="p-2 text-xs text-slate-400">
        {visible.length > 0
          ? "Click a highlighted region (or a field card) to inspect where the value was read."
          : "No located regions — text evidence only."}
      </p>
    </div>
  );
}
