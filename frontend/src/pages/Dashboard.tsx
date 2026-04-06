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

const PIE_COLORS = ["#3b82f6", "#22c55e", "#ef4444", "#6b7280"];

export default function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: fetchStats,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-8 h-8 animate-spin" style={{ color: "var(--color-accent)" }} />
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center py-32">
        <p style={{ color: "var(--color-text-muted)" }}>No stats available yet</p>
      </div>
    );
  }

  // Prepare chart data
  const categoryData = stats.articles_by_category.map((c) => ({
    name: c.category,
    count: c.count,
    bias: c.avg_bias_score ? +(c.avg_bias_score * 100).toFixed(0) : 0,
    trust: c.avg_trust_score ? +(c.avg_trust_score * 100).toFixed(0) : 0,
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
      <h1 className="text-3xl font-bold mb-2" style={{ color: "var(--color-text-primary)" }}>
        Dashboard
      </h1>
      <p className="mb-8" style={{ color: "var(--color-text-secondary)" }}>
        Platform analytics and insights
      </p>

      {/* Stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        <StatsCard
          title="Total Articles"
          value={stats.total_articles}
          subtitle={`${stats.analyzed_articles} analyzed`}
          icon={<Newspaper className="w-6 h-6 text-white" />}
          color="var(--color-accent)"
          glowColor="var(--color-accent-glow)"
        />
        <StatsCard
          title="Avg Reliability"
          value={stats.avg_reliability_score ? `${stats.avg_reliability_score.toFixed(0)}` : "—"}
          subtitle="out of 100"
          icon={<BarChart3 className="w-6 h-6 text-white" />}
          color="var(--color-green)"
          glowColor="var(--color-green-glow)"
        />
        <StatsCard
          title="Avg Bias"
          value={stats.avg_bias_score ? `${(stats.avg_bias_score * 100).toFixed(0)}%` : "—"}
          subtitle="lower is better"
          icon={<Shield className="w-6 h-6 text-white" />}
          color="var(--color-yellow)"
          glowColor="var(--color-yellow-glow)"
        />
        <StatsCard
          title="Avg Trust"
          value={stats.avg_trust_score ? `${(stats.avg_trust_score * 100).toFixed(0)}%` : "—"}
          subtitle="higher is better"
          icon={<Target className="w-6 h-6 text-white" />}
          color="var(--color-cyan)"
          glowColor="rgba(6, 182, 212, 0.2)"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
        {/* Reliability by category */}
        <div
          className="rounded-2xl p-6"
          style={{
            background: "var(--color-bg-card)",
            boxShadow: "var(--shadow-card)",
            border: "1px solid var(--color-border)",
          }}
        >
          <h3 className="text-base font-bold mb-4" style={{ color: "var(--color-text-primary)" }}>
            Reliability by Category
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={categoryData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="name"
                stroke="var(--color-text-muted)"
                fontSize={11}
                tickLine={false}
              />
              <YAxis stroke="var(--color-text-muted)" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{
                  background: "var(--color-bg-secondary)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "8px",
                  color: "var(--color-text-primary)",
                  fontSize: "12px",
                }}
              />
              <Bar dataKey="reliability" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Bias distribution pie */}
        <div
          className="rounded-2xl p-6"
          style={{
            background: "var(--color-bg-card)",
            boxShadow: "var(--shadow-card)",
            border: "1px solid var(--color-border)",
          }}
        >
          <h3 className="text-base font-bold mb-4" style={{ color: "var(--color-text-primary)" }}>
            Bias Label Distribution
          </h3>
          {biasDistData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={biasDistData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {biasDistData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "var(--color-bg-secondary)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "8px",
                    color: "var(--color-text-primary)",
                    fontSize: "12px",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div
              className="flex items-center justify-center h-[280px] text-sm"
              style={{ color: "var(--color-text-muted)" }}
            >
              No bias data yet
            </div>
          )}
          {/* Legend */}
          <div className="flex flex-wrap justify-center gap-4 mt-2">
            {biasDistData.map((entry, i) => (
              <div key={entry.name} className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ background: PIE_COLORS[i % PIE_COLORS.length] }}
                />
                <span
                  className="text-xs capitalize"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  {entry.name} ({entry.value})
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Trust distribution */}
      <div
        className="rounded-2xl p-6 mb-10"
        style={{
          background: "var(--color-bg-card)",
          boxShadow: "var(--shadow-card)",
          border: "1px solid var(--color-border)",
        }}
      >
        <h3 className="text-base font-bold mb-4" style={{ color: "var(--color-text-primary)" }}>
          Trust Score Distribution
        </h3>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={trustDistData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey="name" stroke="var(--color-text-muted)" fontSize={11} tickLine={false} />
            <YAxis stroke="var(--color-text-muted)" fontSize={11} tickLine={false} />
            <Tooltip
              contentStyle={{
                background: "var(--color-bg-secondary)",
                border: "1px solid var(--color-border)",
                borderRadius: "8px",
                color: "var(--color-text-primary)",
                fontSize: "12px",
              }}
            />
            <Bar dataKey="count" fill="#06b6d4" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Top sources table */}
      {stats.top_sources.length > 0 && (
        <div
          className="rounded-2xl p-6"
          style={{
            background: "var(--color-bg-card)",
            boxShadow: "var(--shadow-card)",
            border: "1px solid var(--color-border)",
          }}
        >
          <h3 className="text-base font-bold mb-4" style={{ color: "var(--color-text-primary)" }}>
            Top Sources by Article Count
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                  <th
                    className="text-left py-3 px-4 font-medium"
                    style={{ color: "var(--color-text-muted)" }}
                  >
                    Source
                  </th>
                  <th
                    className="text-center py-3 px-4 font-medium"
                    style={{ color: "var(--color-text-muted)" }}
                  >
                    Articles
                  </th>
                  <th
                    className="text-center py-3 px-4 font-medium"
                    style={{ color: "var(--color-text-muted)" }}
                  >
                    Avg Reliability
                  </th>
                </tr>
              </thead>
              <tbody>
                {stats.top_sources.map((src) => (
                  <tr
                    key={src.source_name}
                    className="transition-colors hover:bg-white/2"
                    style={{ borderBottom: "1px solid var(--color-border)" }}
                  >
                    <td
                      className="py-3 px-4 font-medium"
                      style={{ color: "var(--color-text-primary)" }}
                    >
                      {src.source_name}
                    </td>
                    <td
                      className="py-3 px-4 text-center"
                      style={{ color: "var(--color-text-secondary)" }}
                    >
                      {src.count}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span
                        className="font-bold"
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
