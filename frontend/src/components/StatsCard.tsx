import { type LucideIcon } from "lucide-react";

interface StatsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  color?: "blue" | "red" | "yellow" | "green" | "purple";
}

const colorMap = {
  blue: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  red: "bg-red-500/10 text-red-400 border-red-500/20",
  yellow: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  green: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  purple: "bg-purple-500/10 text-purple-400 border-purple-500/20",
};

const iconColorMap = {
  blue: "text-blue-400",
  red: "text-red-400",
  yellow: "text-amber-400",
  green: "text-emerald-400",
  purple: "text-purple-400",
};

export default function StatsCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color = "blue",
}: StatsCardProps) {
  return (
    <div
      className={`rounded-xl border p-6 ${colorMap[color]} transition-all hover:scale-[1.02]`}
    >
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-medium text-slate-400">{title}</span>
        <Icon className={`w-5 h-5 ${iconColorMap[color]}`} />
      </div>
      <div className="text-3xl font-bold">{value}</div>
      {subtitle && (
        <p className="text-xs text-slate-500 mt-1">{subtitle}</p>
      )}
    </div>
  );
}
