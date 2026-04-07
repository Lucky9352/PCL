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
    <div className="relative rounded-xl p-5 bg-bg-card border border-border transition-all duration-200 hover:border-border-hover">
      <div
        className="absolute top-0 left-0 right-0 h-0.5 rounded-t-xl"
        style={{ background: color }}
      />
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-wider mb-1.5 text-(--color-text-muted)">
            {title}
          </p>
          <p className="text-2xl font-bold tabular-nums" style={{ color }}>
            {value}
          </p>
          {subtitle && <p className="text-[11px] mt-0.5 text-text-secondary">{subtitle}</p>}
        </div>
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center"
          style={{ background: glowColor }}
        >
          {icon}
        </div>
      </div>
    </div>
  );
}
