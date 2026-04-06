interface Props {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  color: string;
  glowColor: string;
}

export default function StatsCard({ title, value, subtitle, icon, color, glowColor }: Props) {
  return (
    <div
      className="relative rounded-2xl p-6 transition-all duration-300 hover:-translate-y-1"
      style={{
        background: "var(--color-bg-card)",
        boxShadow: "var(--shadow-card)",
        border: "1px solid var(--color-border)",
      }}
    >
      {/* Glow accent */}
      <div
        className="absolute top-0 left-0 right-0 h-1 rounded-t-2xl"
        style={{ background: color }}
      />

      <div className="flex items-start justify-between">
        <div>
          <p
            className="text-xs font-medium uppercase tracking-wider mb-2"
            style={{ color: "var(--color-text-muted)" }}
          >
            {title}
          </p>
          <p className="text-3xl font-bold" style={{ color }}>
            {value}
          </p>
          {subtitle && (
            <p className="text-xs mt-1" style={{ color: "var(--color-text-secondary)" }}>
              {subtitle}
            </p>
          )}
        </div>

        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center"
          style={{
            background: glowColor,
            boxShadow: `0 0 20px ${glowColor}`,
          }}
        >
          {icon}
        </div>
      </div>
    </div>
  );
}
