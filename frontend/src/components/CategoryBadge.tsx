const CATEGORY_CONFIG: Record<string, { emoji: string; color: string }> = {
  politics: { emoji: "🏛️", color: "#ef4444" },
  national: { emoji: "🇮🇳", color: "#f97316" },
  business: { emoji: "💼", color: "#22c55e" },
  sports: { emoji: "⚽", color: "#3b82f6" },
  technology: { emoji: "💻", color: "#8b5cf6" },
  tech: { emoji: "💻", color: "#8b5cf6" },
  world: { emoji: "🌍", color: "#06b6d4" },
  entertainment: { emoji: "🎬", color: "#ec4899" },
  science: { emoji: "🔬", color: "#14b8a6" },
  startup: { emoji: "🚀", color: "#a855f7" },
  automobile: { emoji: "🚗", color: "#eab308" },
};

interface Props {
  category: string;
  showCount?: number;
}

export default function CategoryBadge({ category, showCount }: Props) {
  const config = CATEGORY_CONFIG[category.toLowerCase()] || {
    emoji: "📰",
    color: "#6b7280",
  };

  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider"
      style={{
        background: `${config.color}15`,
        color: config.color,
        border: `1px solid ${config.color}30`,
      }}
    >
      <span>{config.emoji}</span>
      <span>{category}</span>
      {showCount != null && (
        <span
          className="ml-1 px-1.5 py-0.5 rounded-full text-[10px]"
          style={{ background: `${config.color}20` }}
        >
          {showCount}
        </span>
      )}
    </span>
  );
}
