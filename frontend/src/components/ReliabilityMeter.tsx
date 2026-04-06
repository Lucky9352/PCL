import { cn } from "@/lib/utils";

interface Props {
  score: number | null | undefined;
  showLabel?: boolean;
  size?: "sm" | "md";
}

export default function ReliabilityMeter({ score, showLabel = true, size = "md" }: Props) {
  const pct = score != null ? Math.min(Math.max(score, 0), 100) : 0;
  const isAnalyzed = score != null;

  const label = !isAnalyzed
    ? "Pending"
    : pct >= 75
      ? "Reliable"
      : pct >= 50
        ? "Moderate"
        : pct >= 25
          ? "Questionable"
          : "Unreliable";

  return (
    <div className="flex items-center gap-3">
      {/* Bar */}
      <div
        className={cn("flex-1 rounded-full overflow-hidden", size === "sm" ? "h-1.5" : "h-2")}
        style={{ background: "rgba(255,255,255,0.06)" }}
      >
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{
            width: isAnalyzed ? `${pct}%` : "0%",
            background: isAnalyzed ? "var(--gradient-reliability)" : "var(--color-text-muted)",
            backgroundSize: "400% 100%",
            backgroundPosition: `${100 - pct}% 0`,
          }}
        />
      </div>

      {/* Score + label */}
      {showLabel && (
        <div className="flex items-center gap-2 shrink-0">
          <span
            className={cn("font-bold tabular-nums", size === "sm" ? "text-xs" : "text-sm")}
            style={{
              color: isAnalyzed
                ? pct >= 75
                  ? "var(--color-green)"
                  : pct >= 50
                    ? "var(--color-yellow)"
                    : pct >= 25
                      ? "var(--color-orange)"
                      : "var(--color-red)"
                : "var(--color-text-muted)",
            }}
          >
            {isAnalyzed ? pct.toFixed(0) : "—"}
          </span>
          <span
            className={cn("font-medium", size === "sm" ? "text-[10px]" : "text-xs")}
            style={{ color: "var(--color-text-muted)" }}
          >
            {label}
          </span>
        </div>
      )}
    </div>
  );
}
