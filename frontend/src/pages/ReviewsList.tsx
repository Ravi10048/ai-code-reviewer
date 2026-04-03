import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ExternalLink, ChevronLeft, ChevronRight } from "lucide-react";
import StatusBadge from "../components/StatusBadge";
import SeverityBadge from "../components/SeverityBadge";
import { fetchReviews, type Review } from "../api/client";

export default function ReviewsList() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const limit = 20;

  useEffect(() => {
    setLoading(true);
    fetchReviews({ limit, offset: page * limit }).then((data) => {
      setReviews(data.reviews);
      setTotal(data.total);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [page]);

  const totalPages = Math.ceil(total / limit);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Reviews</h1>
        <p className="text-slate-400 mt-1">{total} total reviews</p>
      </div>

      <div className="bg-slate-800/50 rounded-xl border border-slate-700 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-700 text-left">
              <th className="px-6 py-3 text-xs font-medium text-slate-400 uppercase">PR</th>
              <th className="px-6 py-3 text-xs font-medium text-slate-400 uppercase">Repository</th>
              <th className="px-6 py-3 text-xs font-medium text-slate-400 uppercase">Status</th>
              <th className="px-6 py-3 text-xs font-medium text-slate-400 uppercase">Issues</th>
              <th className="px-6 py-3 text-xs font-medium text-slate-400 uppercase">Date</th>
              <th className="px-6 py-3 text-xs font-medium text-slate-400 uppercase"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50">
            {reviews.map((review) => (
              <tr key={review.id} className="hover:bg-slate-800/50 transition-colors">
                <td className="px-6 py-4">
                  <Link
                    to={`/reviews/${review.id}`}
                    className="text-sm font-medium text-slate-200 hover:text-blue-400 transition-colors"
                  >
                    {review.pr_title}
                  </Link>
                  <div className="text-xs text-slate-500 mt-0.5">
                    #{review.pr_number} by {review.pr_author}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className="text-sm text-slate-400">{review.repo_name}</span>
                </td>
                <td className="px-6 py-4">
                  <StatusBadge status={review.status} />
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-1.5">
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
                      <span className="text-xs text-emerald-400">No issues</span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-slate-500">
                  {new Date(review.created_at).toLocaleDateString()}
                </td>
                <td className="px-6 py-4">
                  {review.pr_url && (
                    <a
                      href={review.pr_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-slate-500 hover:text-blue-400"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-slate-700 flex items-center justify-between">
            <span className="text-sm text-slate-400">
              Page {page + 1} of {totalPages}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="p-2 rounded-lg text-slate-400 hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="p-2 rounded-lg text-slate-400 hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
