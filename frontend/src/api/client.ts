import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

// ── Types ──

export interface Review {
  id: number;
  repo_name: string;
  pr_number: number;
  pr_title: string;
  pr_author: string;
  pr_url: string;
  total_issues: number;
  critical_count: number;
  warning_count: number;
  suggestion_count: number;
  files_reviewed: number;
  llm_provider: string;
  model_used: string;
  review_duration_ms: number;
  status: string;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface Issue {
  id: number;
  file_path: string;
  line_number: number | null;
  end_line_number: number | null;
  severity: "critical" | "warning" | "suggestion";
  category: "bug" | "security" | "performance" | "style" | "error_handling";
  title: string;
  description: string;
  suggestion: string;
  code_snippet: string;
  confidence: number;
  posted_to_github: boolean;
}

export interface ReviewDetail extends Review {
  issues: Issue[];
}

export interface PaginatedReviews {
  reviews: Review[];
  total: number;
  limit: number;
  offset: number;
}

export interface AnalyticsSummary {
  total_reviews: number;
  total_issues: number;
  avg_issues_per_review: number;
  avg_review_duration_ms: number;
  severity_breakdown: Record<string, number>;
  category_breakdown: Record<string, number>;
  daily_reviews: { date: string; count: number }[];
  top_repos: { repo: string; count: number }[];
}

export interface Repo {
  id: number;
  full_name: string;
  owner: string;
  name: string;
  is_active: boolean;
  installed_at: string;
}

export interface AppSettings {
  llm_provider: string;
  groq_model: string;
  ollama_model: string;
  ollama_base_url: string;
  min_inline_severity: string;
  max_files_per_review: number;
  max_diff_lines_per_file: number;
}

export interface HealthStatus {
  status: string;
  provider?: string;
  model?: string;
  error?: string;
}

// ── API Functions ──

export const fetchReviews = async (
  params: { repo_id?: number; limit?: number; offset?: number } = {}
): Promise<PaginatedReviews> => {
  const { data } = await api.get("/reviews", { params });
  return data;
};

export const fetchReview = async (id: number): Promise<ReviewDetail> => {
  const { data } = await api.get(`/reviews/${id}`);
  return data;
};

export const fetchAnalytics = async (
  days: number = 30
): Promise<AnalyticsSummary> => {
  const { data } = await api.get("/analytics/summary", { params: { days } });
  return data;
};

export const fetchRepos = async (): Promise<Repo[]> => {
  const { data } = await api.get("/analytics/repos");
  return data;
};

export const fetchSettings = async (): Promise<AppSettings> => {
  const { data } = await api.get("/settings");
  return data;
};

export const updateSettings = async (
  settings: Partial<AppSettings>
): Promise<AppSettings> => {
  const { data } = await api.put("/settings", settings);
  return data;
};

export const fetchHealth = async (): Promise<HealthStatus> => {
  const { data } = await api.get("/settings/health");
  return data;
};

export default api;
