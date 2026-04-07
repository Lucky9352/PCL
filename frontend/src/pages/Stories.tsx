import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Eye, Layers, Newspaper, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { fetchStories, type StoryCluster } from "@/api/client";
import ReliabilityMeter from "@/components/ReliabilityMeter";

function BiasSpectrum({ spectrum }: { spectrum: Record<string, number> | null }) {
  if (!spectrum) return null;
  const total = Object.values(spectrum).reduce((a, b) => a + b, 0);
  if (total === 0) return null;

  const colors: Record<string, string> = {
    left: "#3b82f6",
    center: "#10b981",
    right: "#ef4444",
    unclassified: "#64748b",
  };

  return (
    <div className="flex h-2 rounded-full overflow-hidden w-full">
      {Object.entries(spectrum).map(([label, count]) => {
        const pct = (count / total) * 100;
        if (pct === 0) return null;
        return (
          <div
            key={label}
            className="h-full"
            style={{ width: `${pct}%`, background: colors[label] || "#64748b" }}
            title={`${label}: ${count} (${Math.round(pct)}%)`}
          />
        );
      })}
    </div>
  );
}

function StoryCard({ story }: { story: StoryCluster }) {
  return (
    <Link
      to={`/story/${story.id}`}
      className="block rounded-lg p-4 border transition-all duration-150
                 bg-bg-card border-border
                 hover:border-border-hover"
    >
      <div className="flex items-start justify-between gap-2 mb-2.5">
        <h3 className="font-semibold line-clamp-2 text-sm leading-snug flex-1 text-text-primary">
          {story.representative_title}
        </h3>
        <ArrowRight className="w-3.5 h-3.5 shrink-0 mt-0.5 text-(--color-text-muted)" />
      </div>

      {story.unique_sources && story.unique_sources.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2.5">
          {story.unique_sources.slice(0, 5).map((src) => (
            <span
              key={src}
              className="text-[10px] px-1.5 py-0.5 rounded bg-bg-hover text-text-secondary"
            >
              {src}
            </span>
          ))}
          {story.unique_sources.length > 5 && (
            <span className="text-[10px] px-1.5 py-0.5 text-(--color-text-muted)">
              +{story.unique_sources.length - 5}
            </span>
          )}
        </div>
      )}

      <div className="mb-2.5">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] uppercase tracking-wider text-(--color-text-muted)">
            Bias Spectrum
          </span>
          <div className="flex gap-2 text-[9px] text-(--color-text-muted)">
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500" /> Left
            </span>
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Center
            </span>
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500" /> Right
            </span>
          </div>
        </div>
        <BiasSpectrum spectrum={story.bias_spectrum} />
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-[11px] text-(--color-text-muted)">
          <span className="flex items-center gap-1">
            <Newspaper className="w-3 h-3" /> {story.article_count}
          </span>
          <span className="flex items-center gap-1">
            <Users className="w-3 h-3" /> {story.unique_sources?.length || 0} sources
          </span>
        </div>
        {story.avg_reliability_score != null && (
          <div className="w-24">
            <ReliabilityMeter score={story.avg_reliability_score} showLabel={false} size="sm" />
          </div>
        )}
      </div>
    </Link>
  );
}

export default function Stories() {
  const {
    data: stories,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["stories"],
    queryFn: () => fetchStories({ page_size: 30, min_sources: 2 }),
  });

  return (
    <div className="max-w-5xl mx-auto animate-fade-in">
      <div className="mb-7">
        <div className="flex items-center gap-2.5 mb-1">
          <Layers className="w-5 h-5 text-accent" />
          <h1 className="text-2xl font-bold text-text-primary">Story Comparison</h1>
        </div>
        <p className="text-sm text-text-secondary">
          Same events covered by different sources — see how bias and framing differ.
        </p>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center min-h-[40vh]">
          <div className="animate-spin h-6 w-6 border-2 border-accent border-t-transparent rounded-full" />
        </div>
      )}

      {error && (
        <div className="text-center py-20 text-sm text-(--color-text-muted)">
          Failed to load stories. Make sure articles have been scraped and analyzed.
        </div>
      )}

      {stories && stories.length === 0 && (
        <div className="text-center py-20 rounded-xl bg-bg-card border border-border">
          <Eye className="w-10 h-10 mx-auto mb-3 text-(--color-text-muted)" />
          <h3 className="text-sm font-semibold mb-1.5 text-text-primary">
            No Multi-Source Stories Yet
          </h3>
          <p className="text-xs max-w-md mx-auto text-(--color-text-muted)">
            Stories appear when the same event is covered by at least two different outlets. Trigger
            a scrape from the home page, then check back after analysis.
          </p>
        </div>
      )}

      {stories && stories.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {stories.map((story) => (
            <StoryCard key={story.id} story={story} />
          ))}
        </div>
      )}
    </div>
  );
}
