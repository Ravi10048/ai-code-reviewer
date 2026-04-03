import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ListChecks,
  AlertTriangle,
  Clock,
  GitPullRequest,
  ArrowRight,
} from "lucide-react";
import StatsCard from "../components/StatsCard";
import StatusBadge from "../components/StatusBadge";
import SeverityBadge from "../components/SeverityBadge";
import {
  fetchAnalytics,
  fetchReviews,
  type AnalyticsSummary,
  type Review,
} from "../api/client";

export default function Dashboard() {
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [recentReviews, setRecentReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchAnalytics(30), fetchReviews({ limit: 5 })]).then(
      ([analyticsData, reviewsData]) => {
        setAnalytics(analyticsData);
        setRecentReviews(reviewsData.reviews);
        setLoading(false);
      }
    ).catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Dashboard</h1>
        <p className="text-slate-400 mt-1">Overview of your code review activity</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Reviews"
          value={analytics?.total_reviews ?? 0}
          subtitle="Last 30 days"
          icon={ListChecks}
          color="blue"
        />
        <StatsCard
          title="Issues Found"
          value={analytics?.total_issues ?? 0}
          subtitle={`${analytics?.avg_issues_per_review ?? 0} avg per review`}
          icon={AlertTriangle}
          color="yellow"
        />
        <StatsCard
          title="Critical Issues"
          value={analytics?.severity_breakdown?.critical ?? 0}
          subtitle="Needs immediate attention"
          icon={AlertTriangle}
          color="red"
        />
        <StatsCard
          title="Avg Duration"
          value={formatDuration(analytics?.avg_review_duration_ms ?? 0)}
          subtitle="Per review"
          icon={Clock}
          color="green"
        />
      </div>

      {/* Recent Reviews */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-100">Recent Reviews</h2>
          <Link
            to="/reviews"
            className="text-sm text-blue-400 hover:text-blue-300 flex items-center gap-1"
          >
            View all <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {recentReviews.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <GitPullRequest className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-400">No reviews yet</p>
            <p className="text-sm text-slate-500 mt-1">
              Install the GitHub App on a repository to get started
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-700">
            {recentReviews.map((review) => (
              <Link
                key={review.id}
                to={`/reviews/${review.id}`}
                className="flex items-center justify-between px-6 py-4 hover:bg-slate-800 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-200 truncate">
                      {review.pr_title}
                    </span>
                    <StatusBadge status={review.status} />
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                    <span>{review.repo_name}</span>
                    <span>#{review.pr_number}</span>
                    <span>by {review.pr_author}</span>
                    <span>
                      {new Date(review.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  {review.critical_count > 0 && (
                    <SeverityBadge severity="critical" count={review.critical_count} />
                  )}
                  {review.warning_count > 0 && (
                    <SeverityBadge severity="warning" count={review.warning_count} />
                  )}
                  {review.suggestion_count > 0 && (
                    <SeverityBadge severity="suggestion" count={review.suggestion_count} />
                  )}
                  {review.total_issues === 0 && review.status === "completed" && (
                    <span className="text-xs text-emerald-400">Clean</span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
