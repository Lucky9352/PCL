const CATEGORY_COLORS: Record<string, string> = {
  politics: "#ef4444",
  national: "#f97316",
  business: "#10b981",
  sports: "#3b82f6",
  technology: "#8b5cf6",
  tech: "#8b5cf6",
  world: "#06b6d4",
  entertainment: "#ec4899",
  science: "#14b8a6",
  startup: "#8b5cf6",
  automobile: "#f59e0b",
};

interface Props {
  category: string;
  showCount?: number;
}

export default function CategoryBadge({ category, showCount }: Props) {
  const color = CATEGORY_COLORS[category.toLowerCase()] || "#64748b";

  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider"
      style={{
        background: `${color}12`,
        color,
        border: `1px solid ${color}20`,
      }}
    >
      {category}
      {showCount != null && (
        <span className="ml-0.5 font-mono" style={{ opacity: 0.7 }}>
          {showCount}
        </span>
      )}
    </span>
  );
}
