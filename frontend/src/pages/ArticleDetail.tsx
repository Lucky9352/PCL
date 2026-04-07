import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchArticle, type Claim } from "@/api/client";
import ReliabilityMeter from "@/components/ReliabilityMeter";
import CategoryBadge from "@/components/CategoryBadge";
import { cn, biasColor, scoreColor, timeAgo } from "@/lib/utils";
import {
  ArrowLeft,
  ExternalLink,
  AlertTriangle,
  CheckCircle,
  XCircle,
  HelpCircle,
  Loader2,
  Shield,
  Target,
  Zap,
  Layers,
  BarChart3,
  Info,
} from "lucide-react";

function ScoreBar({
  label,
  value,
  max = 1,
  color,
}: {
  label: string;
  value: number;
  max?: number;
  color: string;
}) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[11px]">
        <span className="text-text-secondary">{label}</span>
        <span className="font-mono font-medium" style={{ color }}>
          {(value * 100).toFixed(0)}%
        </span>
      </div>
      <div className="h-1 rounded-full overflow-hidden bg-white/5">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

export default function ArticleDetail() {
  const { id } = useParams<{ id: string }>();

  const {
    data: article,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["article", id],
    queryFn: () => fetchArticle(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-6 h-6 animate-spin text-accent" />
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="text-center py-32">
        <p className="text-(--color-red) text-sm">Article not found</p>
        <Link to="/" className="mt-4 inline-flex items-center gap-2 text-xs text-accent">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to feed
        </Link>
      </div>
    );
  }

  const verdictIcon = (verdict: string) => {
    switch (verdict) {
      case "SUPPORTS":
        return <CheckCircle className="w-4 h-4 text-(--color-green)" />;
      case "REFUTES":
        return <XCircle className="w-4 h-4 text-(--color-red)" />;
      default:
        return <HelpCircle className="w-4 h-4 text-yellow" />;
    }
  };

  const biasComponents = article.bias_score_components;
  const trustComponents = article.trust_score_components;

  return (
    <div className="max-w-4xl mx-auto animate-fade-in">
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 mb-5 text-xs text-text-secondary hover:text-text-primary transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> Back to feed
      </Link>

      {/* Header card */}
      <div className="rounded-xl overflow-hidden mb-5 bg-bg-card border border-border">
        {article.image_url && (
          <div className="relative h-56 sm:h-72">
            <img
              src={article.image_url}
              alt={article.title}
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-linear-to-t from-bg-card via-transparent to-transparent" />
          </div>
        )}

        <div className="p-5 sm:p-7">
          <div className="flex items-center gap-2.5 mb-3 flex-wrap">
            {article.category && <CategoryBadge category={article.category} />}
            {article.source_name && (
              <span className="text-xs font-medium flex items-center gap-1.5 text-text-secondary">
                {article.source_credibility_tier && (
                  <span
                    className="inline-block w-1.5 h-1.5 rounded-full"
                    style={{
                      background:
                        article.source_credibility_tier === "high"
                          ? "#10b981"
                          : article.source_credibility_tier === "medium"
                            ? "#f59e0b"
                            : "#64748b",
                    }}
                  />
                )}
                via {article.source_name}
              </span>
            )}
            <span className="text-xs text-(--color-text-muted)">
              {timeAgo(article.published_at || article.scraped_at)}
            </span>
          </div>

          <h1 className="text-xl sm:text-2xl font-bold mb-3 leading-tight text-text-primary">
            {article.title}
          </h1>

          <p className="text-sm leading-relaxed mb-5 text-text-secondary">
            {article.flagged_tokens && article.flagged_tokens.length > 0
              ? highlightFlaggedTokens(article.synopsis, article.flagged_tokens)
              : article.synopsis}
          </p>

          <div className="mb-3">
            <p className="text-[10px] uppercase tracking-wider mb-1.5 font-medium text-(--color-text-muted)">
              Reliability Score
            </p>
            <ReliabilityMeter score={article.reliability_score} size="md" />
          </div>

          <div className="flex flex-wrap gap-2.5 mt-4">
            {article.source_url && (
              <a
                href={article.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                           bg-accent-muted text-accent border border-accent-border
                           transition-colors hover:bg-accent hover:text-white"
              >
                <ExternalLink className="w-3.5 h-3.5" /> Original Source
              </a>
            )}
            {article.story_cluster_id && (
              <Link
                to={`/story/${article.story_cluster_id}`}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                           bg-green-muted text-(--color-green) border border-green-500/20
                           transition-colors hover:bg-(--color-green) hover:text-white"
              >
                <Layers className="w-3.5 h-3.5" /> Compare sources
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Analysis */}
      {article.analysis_status === "complete" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
          {/* Bias Analysis */}
          <div className="rounded-xl p-5 bg-bg-card border border-border">
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-4 h-4 text-accent" />
              <h2 className="text-sm font-bold text-text-primary">Bias Analysis</h2>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-xs text-text-secondary">Overall Bias</span>
                <span
                  className="text-lg font-bold tabular-nums"
                  style={{
                    color:
                      (article.bias_score ?? 0) < 0.3
                        ? "var(--color-green)"
                        : (article.bias_score ?? 0) < 0.6
                          ? "var(--color-yellow)"
                          : "var(--color-red)",
                  }}
                >
                  {((article.bias_score ?? 0) * 100).toFixed(0)}%
                </span>
              </div>

              {biasComponents && (
                <div className="space-y-2 pt-3 border-t border-border">
                  <p className="text-[10px] uppercase tracking-wider font-medium text-(--color-text-muted)">
                    Component Breakdown
                  </p>
                  <ScoreBar
                    label="Sentiment Extremity (15%)"
                    value={biasComponents.sentiment_extremity}
                    color="#06b6d4"
                  />
                  <ScoreBar
                    label="Bias Type Severity (35%)"
                    value={biasComponents.bias_type_severity}
                    color="#0ea5e9"
                  />
                  <ScoreBar
                    label="Token Bias Density (20%)"
                    value={biasComponents.token_bias_density}
                    color="#f97316"
                  />
                  <ScoreBar
                    label="Framing Deviation (30%)"
                    value={biasComponents.framing_deviation}
                    color="#f59e0b"
                  />
                </div>
              )}

              <div className="flex justify-between items-center pt-3 border-t border-border">
                <span className="text-xs text-text-secondary">Political Lean</span>
                <span
                  className={cn(
                    "px-2 py-0.5 rounded text-[10px] font-semibold uppercase",
                    biasColor(article.bias_label),
                  )}
                  style={{ background: "rgba(255,255,255,0.05)" }}
                >
                  {article.bias_label || "Unclassified"}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-xs text-text-secondary">Sentiment</span>
                <span
                  className="text-xs font-medium"
                  style={{
                    color:
                      article.sentiment_label === "positive"
                        ? "var(--color-green)"
                        : article.sentiment_label === "negative"
                          ? "var(--color-red)"
                          : "var(--color-text-secondary)",
                  }}
                >
                  {article.sentiment_label || "—"}{" "}
                  {article.sentiment_score != null
                    ? `(${article.sentiment_score > 0 ? "+" : ""}${article.sentiment_score.toFixed(2)})`
                    : ""}
                </span>
              </div>

              {article.framing?.primary_frame && (
                <div className="flex justify-between items-center">
                  <span className="text-xs text-text-secondary">Primary Framing</span>
                  <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-accent-muted text-accent">
                    {article.framing.primary_frame}
                  </span>
                </div>
              )}

              {article.bias_types && article.bias_types.length > 0 && (
                <div className="pt-3 border-t border-border">
                  <span className="text-[10px] uppercase tracking-wider font-medium block mb-2 text-(--color-text-muted)">
                    Detected Bias Types
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {article.bias_types.map((type: string) => (
                      <span
                        key={type}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-red-muted text-(--color-red) border border-red-500/10"
                      >
                        <AlertTriangle className="w-3 h-3" /> {type}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {article.bias_types && article.bias_types.length === 0 && (
                <div className="pt-3 border-t border-border">
                  <span className="text-[11px] flex items-center gap-1.5 text-(--color-green)">
                    <CheckCircle className="w-3.5 h-3.5" /> No significant bias types detected
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Trust & Fact Check */}
          <div className="rounded-xl p-5 bg-bg-card border border-border">
            <div className="flex items-center gap-2 mb-4">
              <Target className="w-4 h-4 text-cyan" />
              <h2 className="text-sm font-bold text-text-primary">Trust & Fact Check</h2>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-xs text-text-secondary">Overall Trust</span>
                <span
                  className={cn(
                    "text-lg font-bold tabular-nums",
                    scoreColor((article.trust_score ?? 0) * 100),
                  )}
                >
                  {((article.trust_score ?? 0) * 100).toFixed(0)}%
                </span>
              </div>

              {trustComponents && (
                <div className="space-y-2 pt-3 border-t border-border">
                  <p className="text-[10px] uppercase tracking-wider font-medium text-(--color-text-muted)">
                    Component Breakdown
                  </p>
                  <ScoreBar
                    label="Evidence Trust (50%)"
                    value={trustComponents.evidence_trust}
                    color="#10b981"
                  />
                  <ScoreBar
                    label="Source Trust (30%)"
                    value={trustComponents.source_trust}
                    color="#06b6d4"
                  />
                  <ScoreBar
                    label="Coverage Score (20%)"
                    value={trustComponents.coverage_score}
                    color="#0ea5e9"
                  />
                </div>
              )}

              <div className="flex justify-between items-center pt-3 border-t border-border">
                <span className="text-xs text-text-secondary">Source Credibility</span>
                <span
                  className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase"
                  style={{
                    background:
                      article.source_credibility_tier === "high"
                        ? "var(--color-green-muted)"
                        : article.source_credibility_tier === "medium"
                          ? "var(--color-yellow-muted)"
                          : "rgba(100, 116, 139, 0.12)",
                    color:
                      article.source_credibility_tier === "high"
                        ? "var(--color-green)"
                        : article.source_credibility_tier === "medium"
                          ? "var(--color-yellow)"
                          : "var(--color-text-muted)",
                  }}
                >
                  {article.source_credibility_tier || "Unknown"}
                </span>
              </div>

              {article.model_confidence != null && (
                <div className="flex justify-between items-center">
                  <span className="text-xs flex items-center gap-1 text-text-secondary">
                    Model Confidence
                    <Info className="w-3 h-3 text-(--color-text-muted)" />
                  </span>
                  <span className="text-xs font-mono font-medium text-text-secondary">
                    {(article.model_confidence * 100).toFixed(0)}%
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Reliability breakdown */}
      {article.analysis_status === "complete" && article.reliability_components && (
        <div className="rounded-xl p-5 mb-5 bg-bg-card border border-border">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-4 h-4 text-accent" />
            <h2 className="text-sm font-bold text-text-primary">Reliability Breakdown</h2>
            <span
              className="ml-auto text-xl font-bold tabular-nums"
              style={{
                color:
                  (article.reliability_score ?? 0) >= 75
                    ? "var(--color-green)"
                    : (article.reliability_score ?? 0) >= 50
                      ? "var(--color-yellow)"
                      : (article.reliability_score ?? 0) >= 25
                        ? "var(--color-orange)"
                        : "var(--color-red)",
              }}
            >
              {article.reliability_score?.toFixed(1)}
            </span>
          </div>
          <p className="text-[11px] font-mono mb-4 text-(--color-text-muted)">
            R = [(1−B)×0.35 + T×0.35 + (1−S)×0.15 + (1−F)×0.15] × 100
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
            {[
              {
                label: "Bias Inversion",
                value: article.reliability_components.bias_inversion,
                weight: "35%",
                color: "#0ea5e9",
              },
              {
                label: "Trust",
                value: article.reliability_components.trust,
                weight: "35%",
                color: "#06b6d4",
              },
              {
                label: "Anti-Sensationalism",
                value: article.reliability_components.sensationalism_penalty,
                weight: "15%",
                color: "#f59e0b",
              },
              {
                label: "Framing Neutrality",
                value: article.reliability_components.framing_neutrality,
                weight: "15%",
                color: "#10b981",
              },
            ].map((item, i) => (
              <div key={i} className="rounded-lg p-3 text-center bg-bg-hover">
                <div className="text-[10px] uppercase tracking-wider font-medium mb-1 text-(--color-text-muted)">
                  {item.weight}
                </div>
                <div
                  className="text-lg font-bold tabular-nums mb-0.5"
                  style={{ color: item.color }}
                >
                  {(item.value * 100).toFixed(0)}%
                </div>
                <div className="text-[11px] text-text-secondary">{item.label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Claims */}
      {article.top_claims && article.top_claims.length > 0 && (
        <div className="rounded-xl p-5 mb-5 bg-bg-card border border-border">
          <div className="flex items-center gap-2 mb-3">
            <Zap className="w-4 h-4 text-yellow" />
            <h2 className="text-sm font-bold text-text-primary">Check-Worthy Claims</h2>
          </div>
          <p className="text-[11px] mb-4 text-(--color-text-muted)">
            Claims extracted and verified against external evidence via NLI.
          </p>

          <div className="space-y-3">
            {article.top_claims.map((claim: Claim, i: number) => (
              <div key={i} className="rounded-lg p-3.5 bg-bg-secondary border border-border">
                <div className="flex items-start gap-2.5">
                  {verdictIcon(claim.verdict)}
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium mb-2 text-text-primary">
                      &ldquo;{claim.text}&rdquo;
                    </p>
                    <div className="flex items-center gap-3 text-[11px] flex-wrap">
                      <span className="text-(--color-text-muted)">
                        Worth: <strong>{(claim.checkworthiness * 100).toFixed(0)}%</strong>
                      </span>
                      <span
                        className="font-semibold"
                        style={{
                          color:
                            claim.verdict === "SUPPORTS"
                              ? "var(--color-green)"
                              : claim.verdict === "REFUTES"
                                ? "var(--color-red)"
                                : "var(--color-yellow)",
                        }}
                      >
                        {claim.verdict === "SUPPORTS"
                          ? "Supported"
                          : claim.verdict === "REFUTES"
                            ? "Refuted"
                            : "Insufficient Evidence"}
                      </span>
                      <span className="text-(--color-text-muted)">
                        Conf: {(claim.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    {claim.evidence_urls && claim.evidence_urls.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {claim.evidence_urls.slice(0, 3).map((url: string, j: number) => (
                          <a
                            key={j}
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[11px] flex items-center gap-1 text-accent hover:underline"
                          >
                            <ExternalLink className="w-3 h-3" /> Evidence {j + 1}
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Flagged tokens */}
      {article.flagged_tokens && article.flagged_tokens.length > 0 && (
        <div className="rounded-xl p-5 mb-5 bg-bg-card border border-border">
          <h2 className="text-sm font-bold mb-1.5 text-text-primary">Flagged Biased Language</h2>
          <p className="text-[11px] mb-3 text-(--color-text-muted)">
            Words detected as biased, with neutral alternatives.
          </p>
          <div className="space-y-1.5">
            {article.flagged_tokens.map(
              (token: { word: string; suggestion: string }, i: number) => (
                <div
                  key={i}
                  className="flex items-center gap-2.5 px-3 py-1.5 rounded-md bg-bg-secondary"
                >
                  <span className="px-1.5 py-0.5 rounded text-xs font-medium line-through bg-red-muted text-(--color-red)">
                    {token.word}
                  </span>
                  <span className="text-(--color-text-muted) text-xs">→</span>
                  <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-green-muted text-(--color-green)">
                    {token.suggestion || "—"}
                  </span>
                </div>
              ),
            )}
          </div>
        </div>
      )}

      {article.analysis_status === "complete" && article.analyzed_at && (
        <p className="text-center text-[11px] pb-4 text-(--color-text-muted)">
          Analysis completed {timeAgo(article.analyzed_at)} · Language: {article.language || "en"}
        </p>
      )}
    </div>
  );
}

function highlightFlaggedTokens(
  text: string,
  tokens: { word: string; suggestion: string }[],
): React.ReactNode {
  if (!tokens.length) return text;
  const flaggedWords = new Set(tokens.map((t) => t.word.toLowerCase()));
  const words = text.split(/(\s+)/);
  return words.map((word, i) => {
    if (flaggedWords.has(word.toLowerCase().replace(/[.,!?;:'"]/g, ""))) {
      return (
        <span
          key={i}
          className="px-0.5 rounded cursor-help bg-red-500/10 text-(--color-red)"
          style={{ borderBottom: "1px dashed var(--color-red)" }}
          title={`Biased: "${word}"`}
        >
          {word}
        </span>
      );
    }
    return word;
  });
}
