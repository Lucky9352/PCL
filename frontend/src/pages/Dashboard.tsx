import { useQuery } from "@tanstack/react-query";
import { fetchStats } from "@/api/client";
import StatsCard from "@/components/StatsCard";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { Newspaper, BarChart3, Shield, Target, Loader2 } from "lucide-react";

const PIE_COLORS = ["#3b82f6", "#10b981", "#ef4444", "#64748b"];

const TOOLTIP_STYLE = {
  background: "#1a2332",
  border: "1px solid rgba(148, 163, 184, 0.08)",
  borderRadius: "8px",
  color: "#f1f5f9",
  fontSize: "11px",
};

export default function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: fetchStats,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-6 h-6 animate-spin text-accent" />
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center py-32 text-(--color-text-muted)">No stats available yet</div>
    );
  }

  const categoryData = stats.articles_by_category.map((c) => ({
    name: c.category,
    count: c.count,
    reliability: c.avg_reliability_score ? +c.avg_reliability_score.toFixed(0) : 0,
  }));

  const biasDistData = Object.entries(stats.bias_distribution).map(([label, count]) => ({
    name: label,
    value: count,
  }));

  const trustDistData = Object.entries(stats.trust_distribution).map(([bracket, count]) => ({
    name: bracket,
    count,
  }));

  return (
    <div className="animate-fade-in">
      <h1 className="text-2xl font-bold mb-1 text-text-primary">Dashboard</h1>
      <p className="text-sm mb-7 text-text-secondary">Platform analytics</p>

      {/* Stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatsCard
          title="Total Articles"
          value={stats.total_articles}
          subtitle={`${stats.analyzed_articles} analyzed`}
          icon={<Newspaper className="w-5 h-5 text-white" />}
          color="var(--color-accent)"
          glowColor="var(--color-accent-muted)"
        />
        <StatsCard
          title="Avg Reliability"
          value={stats.avg_reliability_score ? `${stats.avg_reliability_score.toFixed(0)}` : "—"}
          subtitle="out of 100"
          icon={<BarChart3 className="w-5 h-5 text-white" />}
          color="var(--color-green)"
          glowColor="var(--color-green-muted)"
        />
        <StatsCard
          title="Avg Bias"
          value={stats.avg_bias_score ? `${(stats.avg_bias_score * 100).toFixed(0)}%` : "—"}
          subtitle="lower is better"
          icon={<Shield className="w-5 h-5 text-white" />}
          color="var(--color-yellow)"
          glowColor="var(--color-yellow-muted)"
        />
        <StatsCard
          title="Avg Trust"
          value={stats.avg_trust_score ? `${(stats.avg_trust_score * 100).toFixed(0)}%` : "—"}
          subtitle="higher is better"
          icon={<Target className="w-5 h-5 text-white" />}
          color="var(--color-cyan)"
          glowColor="rgba(6, 182, 212, 0.12)"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-8">
        <div className="rounded-xl p-5 bg-bg-card border border-border">
          <h3 className="text-sm font-semibold mb-4 text-text-primary">Reliability by Category</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={categoryData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.06)" />
              <XAxis dataKey="name" stroke="#64748b" fontSize={10} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={10} tickLine={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Bar dataKey="reliability" fill="#0ea5e9" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-xl p-5 bg-bg-card border border-border">
          <h3 className="text-sm font-semibold mb-4 text-text-primary">Bias Label Distribution</h3>
          {biasDistData.length > 0 ? (
            <div className="relative">
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={biasDistData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={90}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {biasDistData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                </PieChart>
              </ResponsiveContainer>
              <div
                className="absolute inset-0 flex items-center justify-center pointer-events-none"
                style={{ paddingBottom: "20px" }}
              >
                <div className="text-center">
                  <div className="text-xl font-bold text-text-primary">
                    {biasDistData.reduce((a, b) => a + b.value, 0)}
                  </div>
                  <div className="text-[10px] uppercase tracking-wider text-(--color-text-muted)">
                    total
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-[260px] text-xs text-(--color-text-muted)">
              No bias data yet
            </div>
          )}
          <div className="flex flex-wrap justify-center gap-3 mt-2">
            {biasDistData.map((entry, i) => (
              <div key={entry.name} className="flex items-center gap-1.5">
                <div
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ background: PIE_COLORS[i % PIE_COLORS.length] }}
                />
                <span className="text-[11px] capitalize text-text-secondary">
                  {entry.name} ({entry.value})
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Trust distribution */}
      <div className="rounded-xl p-5 mb-8 bg-bg-card border border-border">
        <h3 className="text-sm font-semibold mb-4 text-text-primary">Trust Score Distribution</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={trustDistData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.06)" />
            <XAxis dataKey="name" stroke="#64748b" fontSize={10} tickLine={false} />
            <YAxis stroke="#64748b" fontSize={10} tickLine={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Bar dataKey="count" fill="#06b6d4" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Top sources table */}
      {stats.top_sources.length > 0 && (
        <div className="rounded-xl p-5 bg-bg-card border border-border">
          <h3 className="text-sm font-semibold mb-4 text-text-primary">Top Sources</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2.5 px-3 font-medium text-(--color-text-muted)">
                    Source
                  </th>
                  <th className="text-center py-2.5 px-3 font-medium text-(--color-text-muted)">
                    Credibility
                  </th>
                  <th className="text-center py-2.5 px-3 font-medium text-(--color-text-muted)">
                    Articles
                  </th>
                  <th className="text-center py-2.5 px-3 font-medium text-(--color-text-muted)">
                    Avg Reliability
                  </th>
                </tr>
              </thead>
              <tbody>
                {stats.top_sources.map((src) => (
                  <tr key={src.source_name} className="border-b border-border hover:bg-bg-hover">
                    <td className="py-2.5 px-3 font-medium text-text-primary">{src.source_name}</td>
                    <td className="py-2.5 px-3 text-center">
                      <span
                        className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase"
                        style={{
                          background:
                            src.credibility_tier === "high"
                              ? "var(--color-green-muted)"
                              : src.credibility_tier === "medium"
                                ? "var(--color-yellow-muted)"
                                : "rgba(100, 116, 139, 0.12)",
                          color:
                            src.credibility_tier === "high"
                              ? "var(--color-green)"
                              : src.credibility_tier === "medium"
                                ? "var(--color-yellow)"
                                : "#94a3b8",
                        }}
                      >
                        {src.credibility_tier || "unknown"}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-center text-text-secondary">{src.count}</td>
                    <td className="py-2.5 px-3 text-center">
                      <span
                        className="font-semibold tabular-nums"
                        style={{
                          color: src.avg_reliability_score
                            ? src.avg_reliability_score >= 75
                              ? "var(--color-green)"
                              : src.avg_reliability_score >= 50
                                ? "var(--color-yellow)"
                                : "var(--color-red)"
                            : "var(--color-text-muted)",
                        }}
                      >
                        {src.avg_reliability_score?.toFixed(0) ?? "—"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
