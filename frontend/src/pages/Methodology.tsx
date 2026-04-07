import { useQuery } from "@tanstack/react-query";
import { BookOpen, Brain, Database, Scale, Search, Shield } from "lucide-react";
import { fetchMethodology } from "@/api/client";

const STAGE_ICONS: Record<string, typeof BookOpen> = {
  "Scraping & Ingestion": Database,
  Preprocessing: Search,
  "unBIAS Module (HOW)": Scale,
  "ClaimBuster Module (WHAT)": Shield,
  Aggregator: Brain,
};

export default function Methodology() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["methodology"],
    queryFn: fetchMethodology,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin h-6 w-6 border-2 border-accent border-t-transparent rounded-full" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-20 text-sm text-(--color-text-muted)">
        Failed to load methodology data.
      </div>
    );
  }

  const { pipeline, methodology, datasets_used_for_evaluation } = data;
  const specVersion =
    methodology && typeof methodology === "object" && "version" in methodology
      ? String((methodology as { version: string }).version)
      : null;

  const meth =
    methodology && typeof methodology === "object"
      ? (methodology as Record<string, unknown>)
      : null;
  const apiCheckworthiness =
    meth?.checkworthiness && typeof meth.checkworthiness === "object"
      ? (meth.checkworthiness as Record<string, unknown>)
      : null;
  const apiBiasThresholdsRaw =
    meth?.bias_score && typeof meth.bias_score === "object"
      ? (meth.bias_score as Record<string, unknown>).bias_type_thresholds
      : null;
  const apiBiasThresholds =
    apiBiasThresholdsRaw && typeof apiBiasThresholdsRaw === "object"
      ? (apiBiasThresholdsRaw as Record<string, string | number>)
      : null;

  return (
    <div className="max-w-4xl mx-auto animate-fade-in">
      {/* Hero */}
      <div className="mb-10">
        <h1 className="text-2xl font-bold mb-2 text-text-primary">How IndiaGround Works</h1>
        <p className="text-sm text-text-secondary">{pipeline.overview}</p>
      </div>

      {/* Pipeline Stages */}
      <section className="mb-12">
        <h2 className="text-lg font-bold mb-5 text-text-primary">Analysis Pipeline</h2>
        <div className="space-y-3">
          {pipeline.stages.map((stage, i) => {
            const Icon = STAGE_ICONS[stage.name] || BookOpen;
            return (
              <div
                key={i}
                className="rounded-lg p-5 border transition-all duration-150 bg-bg-card border-border hover:border-border-hover"
              >
                <div className="flex items-start gap-3">
                  <div className="shrink-0 w-9 h-9 rounded-lg flex items-center justify-center bg-accent">
                    <Icon className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-bg-hover text-(--color-text-muted)">
                        Stage {i + 1}
                      </span>
                      <h3 className="text-sm font-semibold text-text-primary">{stage.name}</h3>
                    </div>
                    <p className="text-xs mb-2.5 text-text-secondary">{stage.description}</p>
                    {stage.models.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {stage.models.map((model, j) => (
                          <span
                            key={j}
                            className="text-[10px] px-2 py-0.5 rounded font-mono bg-accent-muted text-accent"
                          >
                            {model}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Scoring Formulas */}
      <section className="mb-12">
        <h2 className="text-lg font-bold mb-5 text-text-primary">Scoring Formulas</h2>

        {/* Reliability Score */}
        <div className="rounded-lg p-5 mb-4 border bg-bg-card border-border">
          <h3 className="text-sm font-bold mb-2 text-text-primary">Reliability Score (0–100)</h3>
          <div className="font-mono text-xs p-3 rounded-md mb-3 bg-bg-hover text-accent">
            R = [(1−B) × 0.35 + T × 0.35 + (1−S) × 0.15 + (1−F) × 0.15] × 100
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {[
              { label: "Bias Inversion (1−B)", weight: "35%", desc: "Lower bias → higher score" },
              { label: "Trust Score (T)", weight: "35%", desc: "Higher trust → higher score" },
              {
                label: "Anti-Sensationalism (1−S)",
                weight: "15%",
                desc: "Non-sensational writing",
              },
              { label: "Framing Neutrality (1−F)", weight: "15%", desc: "Neutral reporting style" },
            ].map((item, i) => (
              <div key={i} className="p-2.5 rounded-md bg-bg-hover">
                <div className="text-[10px] font-semibold mb-0.5 text-accent">{item.weight}</div>
                <div className="text-xs font-medium mb-0.5 text-text-primary">{item.label}</div>
                <div className="text-[10px] text-(--color-text-muted)">{item.desc}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Bias Score */}
        <div className="rounded-lg p-5 mb-4 border bg-bg-card border-border">
          <h3 className="text-sm font-bold mb-2 text-text-primary">Bias Score (0–1)</h3>
          <div className="font-mono text-xs p-3 rounded-md mb-3 bg-bg-hover text-accent">
            B = s × 0.15 + t × 0.35 + d × 0.20 + f × 0.30
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {[
              { label: "Sentiment Extremity", weight: "15%", desc: "|combined_sentiment|" },
              { label: "Bias Type Severity", weight: "35%", desc: "BART-MNLI multi-label" },
              { label: "Token Bias Density", weight: "20%", desc: "Flagged words ratio" },
              { label: "Framing Deviation", weight: "30%", desc: "1 − P(neutral)" },
            ].map((item, i) => (
              <div key={i} className="p-2.5 rounded-md bg-bg-hover">
                <div className="text-[10px] font-semibold mb-0.5 text-accent">{item.weight}</div>
                <div className="text-xs font-medium mb-0.5 text-text-primary">{item.label}</div>
                <div className="text-[10px] text-(--color-text-muted)">{item.desc}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Trust Score */}
        <div className="rounded-lg p-5 border bg-bg-card border-border">
          <h3 className="text-sm font-bold mb-2 text-text-primary">Trust Score (0–1)</h3>
          <div className="font-mono text-xs p-3 rounded-md mb-3 bg-bg-hover text-accent">
            T = e × 0.50 + s × 0.30 + c × 0.20
          </div>
          <div className="grid grid-cols-3 gap-2">
            {[
              { label: "Evidence Trust", weight: "50%", desc: "NLI verification results" },
              { label: "Source Trust", weight: "30%", desc: "Source credibility tier" },
              { label: "Coverage Score", weight: "20%", desc: "Verified / total claims" },
            ].map((item, i) => (
              <div key={i} className="p-2.5 rounded-md bg-bg-hover">
                <div className="text-[10px] font-semibold mb-0.5 text-accent">{item.weight}</div>
                <div className="text-xs font-medium mb-0.5 text-text-primary">{item.label}</div>
                <div className="text-[10px] text-(--color-text-muted)">{item.desc}</div>
              </div>
            ))}
          </div>
        </div>

        {(apiBiasThresholds != null || apiCheckworthiness != null) && (
          <div className="rounded-lg p-5 mt-4 border bg-bg-card border-border">
            <h3 className="text-sm font-bold mb-1.5 text-text-primary">
              Live Thresholds (from API)
            </h3>
            <p className="text-[11px] mb-3 text-(--color-text-muted)">
              Served by <code className="font-mono text-accent">GET /api/v1/methodology</code> —
              stays in sync with the backend.
            </p>
            {apiBiasThresholds != null && (
              <div className="mb-3">
                <p className="text-[11px] font-semibold mb-1.5 text-text-secondary">
                  Bias-type thresholds (BART-MNLI)
                </p>
                <pre className="text-[10px] font-mono p-3 rounded-md overflow-x-auto bg-bg-hover text-text-secondary">
                  {JSON.stringify(apiBiasThresholds, null, 2)}
                </pre>
              </div>
            )}
            {apiCheckworthiness != null && (
              <div>
                <p className="text-[11px] font-semibold mb-1.5 text-text-secondary">
                  Check-worthiness (two-pass)
                </p>
                <pre className="text-[10px] font-mono p-3 rounded-md overflow-x-auto bg-bg-hover text-text-secondary">
                  {JSON.stringify(apiCheckworthiness, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Source Credibility */}
      <section className="mb-12">
        <h2 className="text-lg font-bold mb-5 text-text-primary">Source Credibility Database</h2>
        <div className="rounded-lg p-5 border bg-bg-card border-border">
          <p className="text-xs mb-3 text-text-secondary">
            {pipeline.source_credibility.description}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {Object.entries(pipeline.source_credibility.tier_mapping).map(([tier, desc]) => (
              <div key={tier} className="flex items-start gap-2.5 p-2.5 rounded-md bg-bg-hover">
                <span
                  className="text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase"
                  style={{
                    background:
                      tier === "high"
                        ? "var(--color-green-muted)"
                        : tier === "medium"
                          ? "var(--color-yellow-muted)"
                          : tier === "low"
                            ? "var(--color-red-muted)"
                            : "rgba(100,116,139,0.12)",
                    color:
                      tier === "high"
                        ? "var(--color-green)"
                        : tier === "medium"
                          ? "var(--color-yellow)"
                          : tier === "low"
                            ? "var(--color-red)"
                            : "#64748b",
                  }}
                >
                  {tier}
                </span>
                <span className="text-xs text-text-secondary">{desc}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Evaluation Datasets */}
      <section className="mb-12">
        <h2 className="text-lg font-bold mb-5 text-text-primary">Evaluation Datasets</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {datasets_used_for_evaluation.map((ds, i) => (
            <div key={i} className="rounded-lg p-4 border bg-bg-card border-border">
              <h4 className="text-sm font-semibold mb-0.5 text-text-primary">{ds.name}</h4>
              <p className="text-[10px] mb-1.5 text-(--color-text-muted)">{ds.full_name}</p>
              <div className="space-y-0.5 text-xs text-text-secondary">
                <div>
                  Size: <span className="font-mono">{ds.size}</span>
                </div>
                <div>Task: {ds.task}</div>
                <div className="text-[10px] italic text-(--color-text-muted)">{ds.citation}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Political Lean Note */}
      <section className="mb-8">
        <div className="rounded-lg p-5 border border-amber-500/15 bg-amber-500/3">
          <h3 className="text-sm font-bold mb-1.5 text-yellow">
            Note on Political Lean Classification
          </h3>
          <p className="text-xs text-text-secondary">
            Political lean (left/center/right) is determined using a{" "}
            <strong>source-first approach</strong> (60% source known bias + 40% article framing
            analysis). Sentiment is <em>not</em> used to determine political orientation —
            positive/negative sentiment does not correlate with left/right leaning.
          </p>
        </div>
      </section>

      {specVersion && (
        <p className="text-center text-[10px] pb-6 text-(--color-text-muted)">
          Scoring specification v{specVersion} · API:{" "}
          <code className="font-mono text-accent">/api/v1/methodology</code>
        </p>
      )}
    </div>
  );
}
