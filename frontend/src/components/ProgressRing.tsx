"use client";
interface ProgressRingProps {
  pct: number;
  size?: number;
  stroke?: number;
  color?: string;
  label?: string;
}

export function ProgressRing({ pct, size = 56, stroke = 5, color = "#6366f1", label }: ProgressRingProps) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth={stroke} />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke={color} strokeWidth={stroke}
          strokeDasharray={circ} strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.5s ease" }}
        />
      </svg>
      <span className="absolute text-[10px] font-bold text-slate-700" style={{ fontSize: size < 48 ? 8 : 10 }}>
        {label ?? `${pct}%`}
      </span>
    </div>
  );
}
