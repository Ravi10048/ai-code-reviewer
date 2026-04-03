import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  ExternalLink,
  FileCode,
  Clock,
  Cpu,
  CheckCircle,
} from "lucide-react";
import SeverityBadge from "../components/SeverityBadge";
import StatusBadge from "../components/StatusBadge";
import { fetchReview, type ReviewDetail as ReviewDetailType, type Issue } from "../api/client";

const categoryLabels: Record<string, string> = {
  bug: "Bug",
  security: "Security",
  performance: "Performance",
  style: "Style",
  error_handling: "Error Handling",
};

function IssueCard({ issue }: { issue: Issue }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`border rounded-lg p-4 cursor-pointer transition-all ${
        issue.severity === "critical"
          ? "border-red-500/30 bg-red-500/5"
          : issue.severity === "warning"
          ? "border-amber-500/30 bg-amber-500/5"
          : "border-blue-500/30 bg-blue-500/5"
      }`}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <SeverityBadge severity={issue.severity} />
            <span className="text-xs text-slate-500 px-2 py-0.5 bg-slate-800 rounded">
              {categoryLabels[issue.category] || issue.category}
            </span>
            {issue.posted_to_github && (
              <CheckCircle className="w-3.5 h-3.5 text-emerald-400" title="Posted to GitHub" />
            )}
          </div>
          <h3 className="text-sm font-medium text-slate-200 mt-2">{issue.title}</h3>
          <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
            <FileCode className="w-3.5 h-3.5" />
            <span>{issue.file_path}</span>
            {issue.line_number && <span>Line {issue.line_number}</span>}
          </div>
        </div>
        <span className="text-xs text-slate-500">
          {Math.round(issue.confidence * 100)}%
        </span>
      </div>

      {expanded && (
        <div className="mt-4 space-y-3 border-t border-slate-700 pt-3">
          <div>
            <p className="text-sm text-slate-300">{issue.description}</p>
          </div>

          {issue.suggestion && (
            <div>
              <h4 className="text-xs font-medium text-emerald-400 mb-1">Suggestion</h4>
              <p className="text-sm text-slate-300">{issue.suggestion}</p>
            </div>
          )}

          {issue.code_snippet && (
            <div>
              <h4 className="text-xs font-medium text-slate-400 mb-1">Code</h4>
              <pre className="bg-slate-900 rounded-lg p-3 text-xs text-slate-300 overflow-x-auto">
                <code>{issue.code_snippet}</code>
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ReviewDetail() {
  const { id } = useParams<{ id: string }>();
  const [review, setReview] = useState<ReviewDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    if (id) {
      fetchReview(parseInt(id)).then((data) => {
        setReview(data);
        setLoading(false);
      }).catch(() => setLoading(false));
    }
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (!review) {
    return <div className="text-center text-slate-400 py-12">Review not found</div>;
  }

  const filteredIssues =
    filter === "all"
      ? review.issues
      : review.issues.filter((i) => i.severity === filter);

  // Group issues by file
  const issuesByFile = filteredIssues.reduce<Record<string, Issue[]>>((acc, issue) => {
    const key = issue.file_path;
    if (!acc[key]) acc[key] = [];
    acc[key].push(issue);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          to="/reviews"
          className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-blue-400 mb-4"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Reviews
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">{review.pr_title}</h1>
            <div className="flex items-center gap-3 mt-2 text-sm text-slate-400">
              <span>{review.repo_name}</span>
              <span>#{review.pr_number}</span>
              <span>by {review.pr_author}</span>
              <StatusBadge status={review.status} />
            </div>
          </div>
          {review.pr_url && (
            <a
              href={review.pr_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm text-slate-200 transition-colors"
            >
              <ExternalLink className="w-4 h-4" /> View on GitHub
            </a>
          )}
        </div>
      </div>

      {/* Review Meta */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-4">
          <div className="flex items-center gap-2 text-slate-400 mb-1">
            <FileCode className="w-4 h-4" />
            <span className="text-xs">Files Reviewed</span>
          </div>
          <span className="text-xl font-bold text-slate-100">{review.files_reviewed}</span>
        </div>
        <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-4">
          <div className="flex items-center gap-2 text-slate-400 mb-1">
            <Clock className="w-4 h-4" />
            <span className="text-xs">Duration</span>
          </div>
          <span className="text-xl font-bold text-slate-100">
            {review.review_duration_ms < 1000
              ? `${review.review_duration_ms}ms`
              : `${(review.review_duration_ms / 1000).toFixed(1)}s`}
          </span>
        </div>
        <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-4">
          <div className="flex items-center gap-2 text-slate-400 mb-1">
            <Cpu className="w-4 h-4" />
            <span className="text-xs">Model</span>
          </div>
          <span className="text-sm font-medium text-slate-100">
            {review.model_used || "N/A"}
          </span>
        </div>
        <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-4">
          <div className="text-xs text-slate-400 mb-1">Issues</div>
          <div className="flex items-center gap-2">
            <SeverityBadge severity="critical" count={review.critical_count} />
            <SeverityBadge severity="warning" count={review.warning_count} />
            <SeverityBadge severity="suggestion" count={review.suggestion_count} />
          </div>
        </div>
      </div>

      {/* Error message */}
      {review.error_message && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-sm text-red-400">
          {review.error_message}
        </div>
      )}

      {/* Filter */}
      {review.issues.length > 0 && (
        <div className="flex items-center gap-2">
          {["all", "critical", "warning", "suggestion"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filter === f
                  ? "bg-blue-600 text-white"
                  : "bg-slate-800 text-slate-400 hover:bg-slate-700"
              }`}
            >
              {f === "all" ? `All (${review.issues.length})` : f}
            </button>
          ))}
        </div>
      )}

      {/* Issues grouped by file */}
      {Object.keys(issuesByFile).length === 0 ? (
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-8 text-center">
          <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
          <p className="text-emerald-400 font-medium">No issues found!</p>
          <p className="text-sm text-slate-400 mt-1">The code looks clean.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(issuesByFile).map(([filePath, issues]) => (
            <div key={filePath}>
              <h3 className="text-sm font-mono text-slate-400 mb-3 flex items-center gap-2">
                <FileCode className="w-4 h-4" />
                {filePath}
                <span className="text-xs text-slate-600">({issues.length} issues)</span>
              </h3>
              <div className="space-y-3">
                {issues.map((issue) => (
                  <IssueCard key={issue.id} issue={issue} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
