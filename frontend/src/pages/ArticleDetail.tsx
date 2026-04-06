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
} from "lucide-react";

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
        <Loader2 className="w-8 h-8 animate-spin" style={{ color: "var(--color-accent)" }} />
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="text-center py-32">
        <p style={{ color: "var(--color-red)" }}>Article not found</p>
        <Link
          to="/"
          className="mt-4 inline-flex items-center gap-2 text-sm"
          style={{ color: "var(--color-accent)" }}
        >
          <ArrowLeft className="w-4 h-4" /> Back to feed
        </Link>
      </div>
    );
  }

  const verdictIcon = (verdict: string) => {
    switch (verdict) {
      case "SUPPORTS":
        return <CheckCircle className="w-4 h-4" style={{ color: "var(--color-green)" }} />;
      case "REFUTES":
        return <XCircle className="w-4 h-4" style={{ color: "var(--color-red)" }} />;
      default:
        return <HelpCircle className="w-4 h-4" style={{ color: "var(--color-yellow)" }} />;
    }
  };

  return (
    <div className="max-w-4xl mx-auto animate-fade-in">
      {/* Back */}
      <Link
        to="/"
        className="inline-flex items-center gap-2 mb-6 text-sm transition-colors hover:text-white"
        style={{ color: "var(--color-text-secondary)" }}
      >
        <ArrowLeft className="w-4 h-4" /> Back to feed
      </Link>

      {/* Header card */}
      <div
        className="rounded-2xl overflow-hidden mb-6"
        style={{
          background: "var(--color-bg-card)",
          boxShadow: "var(--shadow-card)",
          border: "1px solid var(--color-border)",
        }}
      >
        {/* Image */}
        {article.image_url && (
          <div className="relative h-64 sm:h-80">
            <img
              src={article.image_url}
              alt={article.title}
              className="w-full h-full object-cover"
            />
            <div
              className="absolute inset-0"
              style={{
                background: "linear-gradient(to top, var(--color-bg-card) 0%, transparent 50%)",
              }}
            />
          </div>
        )}

        <div className="p-6 sm:p-8">
          {/* Category + source */}
          <div className="flex items-center gap-3 mb-4 flex-wrap">
            {article.category && <CategoryBadge category={article.category} />}
            {article.source_name && (
              <span
                className="text-sm font-medium"
                style={{ color: "var(--color-text-secondary)" }}
              >
                via {article.source_name}
              </span>
            )}
            <span className="text-sm" style={{ color: "var(--color-text-muted)" }}>
              {timeAgo(article.published_at || article.scraped_at)}
            </span>
          </div>

          <h1
            className="text-2xl sm:text-3xl font-bold mb-4 leading-tight"
            style={{ color: "var(--color-text-primary)" }}
          >
            {article.title}
          </h1>

          {/* Synopsis with flagged tokens highlighted */}
          <p
            className="text-base leading-relaxed mb-6"
            style={{ color: "var(--color-text-secondary)" }}
          >
            {article.flagged_tokens && article.flagged_tokens.length > 0
              ? highlightFlaggedTokens(article.synopsis, article.flagged_tokens)
              : article.synopsis}
          </p>

          {/* Reliability */}
          <div className="mb-4">
            <p
              className="text-xs uppercase tracking-wider mb-2 font-medium"
              style={{ color: "var(--color-text-muted)" }}
            >
              Reliability Score
            </p>
            <ReliabilityMeter score={article.reliability_score} size="md" />
          </div>

          {/* External links */}
          <div className="flex gap-3 mt-4">
            {article.source_url && (
              <a
                href={article.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-all hover:opacity-80"
                style={{
                  background: "rgba(99, 102, 241, 0.1)",
                  color: "var(--color-accent)",
                  border: "1px solid rgba(99, 102, 241, 0.2)",
                }}
              >
                <ExternalLink className="w-4 h-4" /> Original Source
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Analysis breakdown */}
      {article.analysis_status === "complete" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Bias Analysis */}
          <div
            className="rounded-2xl p-6"
            style={{
              background: "var(--color-bg-card)",
              boxShadow: "var(--shadow-card)",
              border: "1px solid var(--color-border)",
            }}
          >
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-5 h-5" style={{ color: "var(--color-accent)" }} />
              <h2 className="text-lg font-bold" style={{ color: "var(--color-text-primary)" }}>
                Bias Analysis
              </h2>
            </div>

            {/* Bias score */}
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
                  Bias Score
                </span>
                <span
                  className="text-lg font-bold"
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

              <div className="flex justify-between items-center">
                <span className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
                  Bias Label
                </span>
                <span
                  className={cn(
                    "px-3 py-1 rounded-full text-xs font-bold uppercase",
                    biasColor(article.bias_label),
                  )}
                  style={{
                    background: "rgba(255,255,255,0.06)",
                    border: "1px solid rgba(255,255,255,0.08)",
                  }}
                >
                  {article.bias_label || "Unclassified"}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
                  Sentiment
                </span>
                <span
                  className="text-sm font-medium"
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

              {/* Bias types */}
              {article.bias_types && article.bias_types.length > 0 && (
                <div>
                  <span
                    className="text-sm block mb-2"
                    style={{ color: "var(--color-text-secondary)" }}
                  >
                    Detected Bias Types
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {article.bias_types.map((type: string) => (
                      <span
                        key={type}
                        className="px-2 py-1 rounded-lg text-xs font-medium"
                        style={{
                          background: "rgba(239, 68, 68, 0.1)",
                          color: "var(--color-red)",
                          border: "1px solid rgba(239, 68, 68, 0.2)",
                        }}
                      >
                        <AlertTriangle className="w-3 h-3 inline mr-1" />
                        {type}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Trust & Fact Check */}
          <div
            className="rounded-2xl p-6"
            style={{
              background: "var(--color-bg-card)",
              boxShadow: "var(--shadow-card)",
              border: "1px solid var(--color-border)",
            }}
          >
            <div className="flex items-center gap-2 mb-4">
              <Target className="w-5 h-5" style={{ color: "var(--color-cyan)" }} />
              <h2 className="text-lg font-bold" style={{ color: "var(--color-text-primary)" }}>
                Trust & Fact Check
              </h2>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
                  Trust Score
                </span>
                <span
                  className={cn("text-lg font-bold", scoreColor((article.trust_score ?? 0) * 100))}
                >
                  {((article.trust_score ?? 0) * 100).toFixed(0)}%
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
                  Source Credibility
                </span>
                <span
                  className="px-3 py-1 rounded-full text-xs font-bold uppercase"
                  style={{
                    background:
                      article.source_credibility_tier === "high"
                        ? "rgba(34, 197, 94, 0.1)"
                        : article.source_credibility_tier === "medium"
                          ? "rgba(234, 179, 8, 0.1)"
                          : "rgba(239, 68, 68, 0.1)",
                    color:
                      article.source_credibility_tier === "high"
                        ? "var(--color-green)"
                        : article.source_credibility_tier === "medium"
                          ? "var(--color-yellow)"
                          : "var(--color-red)",
                    border: "1px solid rgba(255,255,255,0.08)",
                  }}
                >
                  {article.source_credibility_tier || "Unknown"}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Claims */}
      {article.top_claims && article.top_claims.length > 0 && (
        <div
          className="rounded-2xl p-6 mb-6"
          style={{
            background: "var(--color-bg-card)",
            boxShadow: "var(--shadow-card)",
            border: "1px solid var(--color-border)",
          }}
        >
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-5 h-5" style={{ color: "var(--color-yellow)" }} />
            <h2 className="text-lg font-bold" style={{ color: "var(--color-text-primary)" }}>
              Check-Worthy Claims
            </h2>
          </div>

          <div className="space-y-4">
            {article.top_claims.map((claim: Claim, i: number) => (
              <div
                key={i}
                className="rounded-xl p-4"
                style={{
                  background: "var(--color-bg-secondary)",
                  border: "1px solid var(--color-border)",
                }}
              >
                <div className="flex items-start gap-3">
                  {verdictIcon(claim.verdict)}
                  <div className="flex-1">
                    <p
                      className="text-sm font-medium mb-2"
                      style={{ color: "var(--color-text-primary)" }}
                    >
                      "{claim.text}"
                    </p>
                    <div className="flex items-center gap-4 text-xs">
                      <span style={{ color: "var(--color-text-muted)" }}>
                        Check-worthiness:{" "}
                        <strong>{(claim.checkworthiness * 100).toFixed(0)}%</strong>
                      </span>
                      <span
                        style={{
                          color:
                            claim.verdict === "SUPPORTS"
                              ? "var(--color-green)"
                              : claim.verdict === "REFUTES"
                                ? "var(--color-red)"
                                : "var(--color-yellow)",
                        }}
                      >
                        {claim.verdict}
                      </span>
                      <span style={{ color: "var(--color-text-muted)" }}>
                        Confidence: {(claim.confidence * 100).toFixed(0)}%
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
                            className="text-xs flex items-center gap-1 hover:underline"
                            style={{ color: "var(--color-accent)" }}
                          >
                            <ExternalLink className="w-3 h-3" />
                            Evidence {j + 1}
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
        <div
          className="rounded-2xl p-6"
          style={{
            background: "var(--color-bg-card)",
            boxShadow: "var(--shadow-card)",
            border: "1px solid var(--color-border)",
          }}
        >
          <h2 className="text-lg font-bold mb-4" style={{ color: "var(--color-text-primary)" }}>
            Flagged Biased Tokens
          </h2>
          <div className="space-y-2">
            {article.flagged_tokens.map(
              (token: { word: string; suggestion: string }, i: number) => (
                <div
                  key={i}
                  className="flex items-center gap-3 px-4 py-2 rounded-lg"
                  style={{ background: "var(--color-bg-secondary)" }}
                >
                  <span
                    className="px-2 py-0.5 rounded text-sm font-medium line-through"
                    style={{
                      background: "rgba(239, 68, 68, 0.1)",
                      color: "var(--color-red)",
                    }}
                  >
                    {token.word}
                  </span>
                  <span style={{ color: "var(--color-text-muted)" }}>→</span>
                  <span
                    className="px-2 py-0.5 rounded text-sm font-medium"
                    style={{
                      background: "rgba(34, 197, 94, 0.1)",
                      color: "var(--color-green)",
                    }}
                  >
                    {token.suggestion || "—"}
                  </span>
                </div>
              ),
            )}
          </div>
        </div>
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
          className="px-1 rounded cursor-help"
          style={{
            background: "rgba(239, 68, 68, 0.15)",
            borderBottom: "2px dashed var(--color-red)",
            color: "var(--color-red)",
          }}
          title={`Biased token: "${word}"`}
        >
          {word}
        </span>
      );
    }
    return word;
  });
}
