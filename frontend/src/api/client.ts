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

export interface PoliticalLean {
  lean_score: number;
  lean_label: string;
  source_bias: string;
  source_bias_numeric: number;
  framing_lean: number;
  method: string;
}

export interface ArticleCard {
  id: string;
  title: string;
  synopsis: string;
  author: string | null;
  published_at: string | null;
  category: string | null;
  source_name: string | null;
  source_type: string;
  source_url?: string | null;
  image_url: string | null;
  reliability_score: number | null;
  bias_score: number | null;
  bias_label: string | null;
  bias_types: string[] | null;
  trust_score: number | null;
  sentiment_label: string | null;
  source_credibility_tier: string | null;
  analysis_status: string | null;
  story_cluster_id: string | null;
  scraped_at: string;
  cluster_similarity?: number | null;
  political_lean?: PoliticalLean | null;
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
  flagged_tokens: { word: string; suggestion: string; source?: string }[] | null;
  source_credibility_tier: string | null;
  top_claims: Claim[] | null;
  framing: FramingResult | null;
  political_lean: PoliticalLean | null;
  bias_score_components: ScoreComponents | null;
  trust_score_components: TrustComponents | null;
  reliability_components: ReliabilityComponents | null;
  model_confidence: number | null;
  story_cluster_id: string | null;
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

export interface FramingResult {
  primary_frame: string;
  confidence: number;
  framing_deviation: number;
  all_frames: { frame: string; probability: number }[];
}

export interface ScoreComponents {
  sentiment_extremity: number;
  bias_type_severity: number;
  token_bias_density: number;
  framing_deviation: number;
  weights: Record<string, number>;
}

export interface TrustComponents {
  evidence_trust: number;
  source_trust: number;
  coverage_score: number;
  weights: Record<string, number>;
}

export interface ReliabilityComponents {
  bias_inversion: number;
  trust: number;
  sensationalism_penalty: number;
  framing_neutrality: number;
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

export interface StoryCluster {
  id: string;
  representative_title: string;
  category: string | null;
  article_count: number;
  source_diversity: number | null;
  bias_spectrum: Record<string, number> | null;
  avg_reliability_score: number | null;
  avg_trust_score: number | null;
  unique_sources: string[] | null;
  created_at: string | null;
}

export interface StoryDetail {
  cluster: StoryCluster;
  articles: ArticleCard[];
}

export interface MethodologyData {
  methodology: Record<string, unknown>;
  pipeline: {
    overview: string;
    stages: {
      name: string;
      description: string;
      models: string[];
    }[];
    source_credibility: {
      description: string;
      tier_mapping: Record<string, string>;
    };
  };
  datasets_used_for_evaluation: {
    name: string;
    full_name: string;
    size: string;
    task: string;
    citation: string;
  }[];
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

export async function fetchStories(params?: {
  page_size?: number;
  category?: string;
  min_sources?: number;
}) {
  const res = await api.get<{
    success: boolean;
    data: StoryCluster[];
  }>("/stories", { params });
  return res.data.data;
}

export async function fetchStory(id: string) {
  const res = await api.get<{
    success: boolean;
    data: StoryDetail;
  }>(`/stories/${id}`);
  return res.data.data;
}

export async function fetchMethodology() {
  const res = await api.get<{
    success: boolean;
    data: MethodologyData;
  }>("/methodology");
  return res.data.data;
}
