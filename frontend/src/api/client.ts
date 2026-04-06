import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "";

export const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
});

// ── Types ────────────────────────────────────────

export interface ArticleCard {
  id: string;
  title: string;
  synopsis: string;
  author: string | null;
  published_at: string | null;
  category: string | null;
  source_name: string | null;
  image_url: string | null;
  reliability_score: number | null;
  bias_score: number | null;
  bias_label: string | null;
  trust_score: number | null;
  sentiment_label: string | null;
  analysis_status: string | null;
  scraped_at: string;
}

export interface ArticleDetail extends ArticleCard {
  source_url: string | null;
  inshorts_url: string | null;
  content_hash: string;
  status: string;
  entities: Record<string, string[]> | null;
  noun_phrases: string[] | null;
  language: string | null;
  is_duplicate: boolean;
  sentiment_score: number | null;
  bias_types: string[] | null;
  flagged_tokens: { word: string; suggestion: string }[] | null;
  source_credibility_tier: string | null;
  top_claims: Claim[] | null;
  analyzed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Claim {
  text: string;
  checkworthiness: number;
  verdict: string;
  evidence_urls: string[];
  confidence: number;
}

export interface PaginationMeta {
  next_cursor: string | null;
  has_more: boolean;
  total_count: number | null;
}

export interface CategoryInfo {
  name: string;
  count: number;
}

export interface DashboardStats {
  total_articles: number;
  analyzed_articles: number;
  avg_bias_score: number | null;
  avg_trust_score: number | null;
  avg_reliability_score: number | null;
  articles_by_category: {
    category: string;
    count: number;
    avg_bias_score: number | null;
    avg_trust_score: number | null;
    avg_reliability_score: number | null;
  }[];
  top_sources: {
    source_name: string;
    count: number;
    credibility_tier: string | null;
    avg_reliability_score: number | null;
  }[];
  bias_distribution: Record<string, number>;
  trust_distribution: Record<string, number>;
}

// ── API functions ────────────────────────────────

export async function fetchArticles(params?: {
  page_size?: number;
  cursor?: string;
  category?: string;
  bias?: string;
  trust_min?: number;
  search?: string;
}) {
  const res = await api.get<{
    success: boolean;
    data: ArticleCard[];
    meta: PaginationMeta;
  }>("/articles", { params });
  return res.data;
}

export async function fetchArticle(id: string) {
  const res = await api.get<{
    success: boolean;
    data: ArticleDetail;
  }>(`/articles/${id}`);
  return res.data.data;
}

export async function fetchArticleAnalysis(id: string) {
  const res = await api.get<{
    success: boolean;
    data: Record<string, unknown> | null;
    message?: string;
  }>(`/articles/${id}/analysis`);
  return res.data;
}

export async function fetchCategories() {
  const res = await api.get<{
    success: boolean;
    data: CategoryInfo[];
  }>("/categories");
  return res.data.data;
}

export async function fetchStats() {
  const res = await api.get<{
    success: boolean;
    data: DashboardStats;
  }>("/stats");
  return res.data.data;
}

export async function triggerScrape() {
  const res = await api.post<{
    success: boolean;
    data: { message: string; task_id: string | null };
  }>("/scrape/trigger");
  return res.data.data;
}
