import { cn, scoreColor, biasColor, timeAgo } from "@/lib/utils";
import type { ArticleCard as ArticleCardType } from "@/api/client";
import ReliabilityMeter from "./ReliabilityMeter";
import CategoryBadge from "./CategoryBadge";
import { Clock, Layers } from "lucide-react";
import { Link } from "react-router-dom";

interface Props {
  article: ArticleCardType;
  index?: number;
}

const CREDIBILITY_COLORS: Record<string, string> = {
  high: "#10b981",
  medium: "#f59e0b",
  low: "#ef4444",
  unknown: "#64748b",
};

export default function ArticleCard({ article, index = 0 }: Props) {
  return (
    <Link
      to={`/article/${article.id}`}
      className="block group animate-fade-in"
      style={{ animationDelay: `${index * 0.03}s` }}
    >
      <article
        className="relative rounded-xl overflow-hidden transition-all duration-200 h-full flex flex-col
                   bg-bg-card border border-border
                   hover:border-border-hover hover:shadow-(--shadow-hover)"
      >
        {article.image_url && (
          <div className="relative h-40 overflow-hidden">
            <img
              src={article.image_url}
              alt={article.title}
              className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
              loading="lazy"
            />
            <div className="absolute inset-0 bg-linear-to-t from-bg-card via-transparent to-transparent" />
            {article.category && (
              <div className="absolute top-2.5 left-2.5">
                <CategoryBadge category={article.category} />
              </div>
            )}
          </div>
        )}

        <div className="p-4 flex flex-col flex-1">
          {!article.image_url && article.category && (
            <div className="mb-2.5">
              <CategoryBadge category={article.category} />
            </div>
          )}

          <h3 className="text-sm font-semibold leading-snug mb-1.5 line-clamp-2 text-text-primary group-hover:text-white transition-colors">
            {article.title}
          </h3>

          <p className="text-xs leading-relaxed mb-3 line-clamp-2 text-text-secondary">
            {article.synopsis}
          </p>

          <div className="mt-auto space-y-2.5">
            <ReliabilityMeter score={article.reliability_score} />

            {/* Bias type chips */}
            {article.bias_types && article.bias_types.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {article.bias_types.slice(0, 3).map((type) => (
                  <span
                    key={type}
                    className="px-1.5 py-0.5 rounded text-[10px] font-medium
                               bg-red-muted text-(--color-red)
                               border border-red-500/10"
                  >
                    {type}
                  </span>
                ))}
              </div>
            )}

            {/* Bottom row */}
            <div className="flex items-center justify-between pt-2 border-t border-border">
              <div className="flex items-center gap-2 min-w-0">
                {article.source_name && (
                  <span className="text-[11px] font-medium flex items-center gap-1.5 text-(--color-text-muted) truncate">
                    <span
                      className="inline-block w-1.5 h-1.5 rounded-full shrink-0"
                      style={{
                        background:
                          CREDIBILITY_COLORS[article.source_credibility_tier || "unknown"],
                      }}
                    />
                    {article.source_name}
                  </span>
                )}
                <span className="flex items-center gap-1 text-[11px] text-(--color-text-muted) shrink-0">
                  <Clock className="w-3 h-3" />
                  {timeAgo(article.published_at || article.scraped_at)}
                </span>
              </div>

              <div className="flex items-center gap-1.5 shrink-0">
                {article.story_cluster_id && (
                  <span title="Multi-source story">
                    <Layers className="w-3 h-3 text-emerald-500" />
                  </span>
                )}
                {article.bias_label && article.bias_label !== "unclassified" && (
                  <span
                    className={cn(
                      "px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase",
                      biasColor(article.bias_label),
                    )}
                    style={{ background: "rgba(255,255,255,0.05)" }}
                  >
                    {article.bias_label}
                  </span>
                )}
                {article.trust_score != null && (
                  <span
                    className={cn(
                      "px-1.5 py-0.5 rounded text-[10px] font-semibold tabular-nums",
                      scoreColor(article.trust_score * 100),
                    )}
                    style={{ background: "rgba(255,255,255,0.05)" }}
                  >
                    T:{(article.trust_score * 100).toFixed(0)}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </article>
    </Link>
  );
}
