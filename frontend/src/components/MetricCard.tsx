"use client";

interface MetricCardProps {
  icon: string;
  label: string;
  value: string;
  tooltip?: string;
}

export default function MetricCard({ icon, label, value }: MetricCardProps) {
  return (
    <div className="metric-card text-center">
      <div className="flex items-center justify-center gap-1.5 mb-2">
        <span className="text-sm">{icon}</span>
        <span className="text-sm text-gray-400 font-medium">{label}</span>
      </div>
      <div className="text-lg font-bold text-white">{value}</div>
    </div>
  );
}
