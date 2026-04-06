import { cn, scoreColor, biasColor, timeAgo } from "@/lib/utils";
import type { ArticleCard as ArticleCardType } from "@/api/client";
import ReliabilityMeter from "./ReliabilityMeter";
import CategoryBadge from "./CategoryBadge";
import { Clock } from "lucide-react";
import { Link } from "react-router-dom";

interface Props {
  article: ArticleCardType;
  index?: number;
}

export default function ArticleCard({ article, index = 0 }: Props) {
  return (
    <Link
      to={`/article/${article.id}`}
      className="block group animate-fade-in"
      style={{ animationDelay: `${index * 0.05}s` }}
    >
      <article
        className="relative rounded-2xl overflow-hidden transition-all duration-300 hover:-translate-y-1"
        style={{
          background: "var(--color-bg-card)",
          boxShadow: "var(--shadow-card)",
          border: "1px solid var(--color-border)",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.boxShadow = "var(--shadow-hover)";
          e.currentTarget.style.borderColor = "var(--color-border-hover)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.boxShadow = "var(--shadow-card)";
          e.currentTarget.style.borderColor = "var(--color-border)";
        }}
      >
        {/* Image */}
        {article.image_url && (
          <div className="relative h-44 overflow-hidden">
            <img
              src={article.image_url}
              alt={article.title}
              className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
              loading="lazy"
            />
            <div
              className="absolute inset-0"
              style={{
                background: "linear-gradient(to top, var(--color-bg-card) 0%, transparent 60%)",
              }}
            />
            {/* Category badge overlay */}
            {article.category && (
              <div className="absolute top-3 left-3">
                <CategoryBadge category={article.category} />
              </div>
            )}
          </div>
        )}

        {/* Content */}
        <div className="p-5">
          {/* Category if no image */}
          {!article.image_url && article.category && (
            <div className="mb-3">
              <CategoryBadge category={article.category} />
            </div>
          )}

          {/* Title */}
          <h3
            className="text-base font-semibold leading-snug mb-2 line-clamp-2 transition-colors duration-200 group-hover:text-white"
            style={{ color: "var(--color-text-primary)" }}
          >
            {article.title}
          </h3>

          {/* Synopsis */}
          <p
            className="text-sm leading-relaxed mb-4 line-clamp-3"
            style={{ color: "var(--color-text-secondary)" }}
          >
            {article.synopsis}
          </p>

          {/* Reliability meter */}
          <ReliabilityMeter score={article.reliability_score} />

          {/* Bottom row: source, time, scores */}
          <div className="mt-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* Source */}
              {article.source_name && (
                <span className="text-xs font-medium" style={{ color: "var(--color-text-muted)" }}>
                  {article.source_name}
                </span>
              )}

              {/* Time */}
              <span
                className="flex items-center gap-1 text-xs"
                style={{ color: "var(--color-text-muted)" }}
              >
                <Clock className="w-3 h-3" />
                {timeAgo(article.published_at || article.scraped_at)}
              </span>
            </div>

            {/* Score chips */}
            <div className="flex items-center gap-2">
              {article.bias_label && article.bias_label !== "unclassified" && (
                <span
                  className={cn(
                    "px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider",
                    biasColor(article.bias_label),
                  )}
                  style={{
                    background: "rgba(255,255,255,0.06)",
                    border: "1px solid rgba(255,255,255,0.08)",
                  }}
                >
                  {article.bias_label}
                </span>
              )}

              {article.trust_score != null && (
                <span
                  className={cn(
                    "px-2 py-0.5 rounded-full text-[10px] font-bold",
                    scoreColor(article.trust_score * 100),
                  )}
                  style={{
                    background: "rgba(255,255,255,0.06)",
                    border: "1px solid rgba(255,255,255,0.08)",
                  }}
                >
                  T:{(article.trust_score * 100).toFixed(0)}
                </span>
              )}
            </div>
          </div>
        </div>
      </article>
    </Link>
  );
}
