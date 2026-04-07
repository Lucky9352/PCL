import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ExternalLink, Layers, Loader2 } from "lucide-react";
import { fetchStory } from "@/api/client";
import ReliabilityMeter from "@/components/ReliabilityMeter";
import { cn, biasColor, scoreColor, timeAgo } from "@/lib/utils";

export default function StoryDetail() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, error } = useQuery({
    queryKey: ["story", id],
    queryFn: () => fetchStory(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-6 h-6 animate-spin text-accent" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-32 max-w-lg mx-auto">
        <p className="mb-3 text-sm text-(--color-text-muted)">Story not found or still indexing.</p>
        <Link to="/stories" className="text-xs text-accent">
          ← Back to stories
        </Link>
      </div>
    );
  }

  const { cluster, articles } = data;

  return (
    <div className="max-w-5xl mx-auto animate-fade-in">
      <Link
        to="/stories"
        className="inline-flex items-center gap-1.5 mb-5 text-xs text-text-secondary hover:text-text-primary transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> All stories
      </Link>

      <div className="rounded-xl p-5 sm:p-7 mb-6 bg-bg-card border border-border">
        <div className="flex items-start gap-2.5 mb-3">
          <Layers className="w-6 h-6 shrink-0 text-accent" />
          <div>
            <h1 className="text-lg sm:text-xl font-bold text-text-primary">
              {cluster.representative_title}
            </h1>
            <p className="text-xs mt-1.5 text-(--color-text-muted)">
              {cluster.article_count} articles · {cluster.unique_sources?.length ?? 0} sources
            </p>
          </div>
        </div>
        {cluster.avg_reliability_score != null && (
          <div className="max-w-md">
            <p className="text-[10px] uppercase tracking-wider mb-1.5 text-(--color-text-muted)">
              Avg reliability (cross-source)
            </p>
            <ReliabilityMeter score={cluster.avg_reliability_score} />
          </div>
        )}
      </div>

      <h2 className="text-sm font-semibold mb-3 text-text-primary">Coverage by outlet</h2>

      <div className="space-y-3">
        {articles.map((a) => (
          <div
            key={a.id}
            className="rounded-lg p-4 border transition-all duration-150 bg-bg-card border-border hover:border-border-hover"
          >
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
              <div className="flex-1 min-w-0">
                <Link
                  to={`/article/${a.id}`}
                  className="font-semibold text-sm hover:underline line-clamp-2 text-text-primary"
                >
                  {a.title}
                </Link>
                <p className="text-[11px] mt-1.5 line-clamp-2 text-text-secondary">{a.synopsis}</p>
                <div className="flex flex-wrap items-center gap-2 mt-2 text-[11px] text-(--color-text-muted)">
                  <span className="font-medium text-text-secondary">
                    {a.source_name ?? "Unknown"}
                  </span>
                  {a.source_type && a.source_type !== "inshorts" && (
                    <span className="px-1.5 py-0.5 rounded text-[9px] uppercase font-semibold bg-bg-hover">
                      {a.source_type}
                    </span>
                  )}
                  {a.published_at && <span>{timeAgo(a.published_at)}</span>}
                  {a.cluster_similarity != null && (
                    <span>sim {a.cluster_similarity.toFixed(2)}</span>
                  )}
                </div>
              </div>
              <div className="flex flex-row sm:flex-col items-center sm:items-end gap-2 shrink-0">
                {a.reliability_score != null && (
                  <div className="w-32">
                    <ReliabilityMeter score={a.reliability_score} size="sm" />
                  </div>
                )}
                <div className="flex gap-1.5">
                  {a.bias_label && (
                    <span
                      className={cn(
                        "px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase",
                        biasColor(a.bias_label),
                      )}
                      style={{ background: "rgba(255,255,255,0.05)" }}
                    >
                      {a.bias_label}
                    </span>
                  )}
                  {a.trust_score != null && (
                    <span
                      className={cn(
                        "px-1.5 py-0.5 rounded text-[10px] font-semibold tabular-nums",
                        scoreColor(a.trust_score * 100),
                      )}
                      style={{ background: "rgba(255,255,255,0.05)" }}
                    >
                      T:{(a.trust_score * 100).toFixed(0)}
                    </span>
                  )}
                </div>
                {a.source_url && (
                  <a
                    href={a.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[11px] font-medium text-accent"
                  >
                    Original <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
