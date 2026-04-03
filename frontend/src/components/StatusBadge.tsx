interface StatusBadgeProps {
  status: string;
}

const statusConfig: Record<string, { bg: string; text: string; label: string }> = {
  completed: { bg: "bg-emerald-500/15", text: "text-emerald-400", label: "Completed" },
  in_progress: { bg: "bg-blue-500/15", text: "text-blue-400", label: "In Progress" },
  pending: { bg: "bg-slate-500/15", text: "text-slate-400", label: "Pending" },
  failed: { bg: "bg-red-500/15", text: "text-red-400", label: "Failed" },
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.pending;

  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}
    >
      {config.label}
    </span>
  );
}
