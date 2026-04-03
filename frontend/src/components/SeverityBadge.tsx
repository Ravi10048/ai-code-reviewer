interface SeverityBadgeProps {
  severity: "critical" | "warning" | "suggestion";
  count?: number;
}

const severityConfig = {
  critical: {
    bg: "bg-red-500/15",
    text: "text-red-400",
    border: "border-red-500/30",
    dot: "bg-red-400",
  },
  warning: {
    bg: "bg-amber-500/15",
    text: "text-amber-400",
    border: "border-amber-500/30",
    dot: "bg-amber-400",
  },
  suggestion: {
    bg: "bg-blue-500/15",
    text: "text-blue-400",
    border: "border-blue-500/30",
    dot: "bg-blue-400",
  },
};

export default function SeverityBadge({ severity, count }: SeverityBadgeProps) {
  const config = severityConfig[severity];

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${config.bg} ${config.text} ${config.border}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
      {severity}
      {count !== undefined && <span className="font-bold ml-0.5">{count}</span>}
    </span>
  );
}
