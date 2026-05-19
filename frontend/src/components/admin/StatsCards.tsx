import { MessageSquare, TrendingUp, Clock, DollarSign } from 'lucide-react';
import type { AdminStats, CostStats } from '../../api/types';

interface Props {
  stats: AdminStats;
  cost: CostStats;
}

export function StatsCards({ stats, cost }: Props) {
  const cards = [
    {
      label: 'Total Queries',
      value: (stats.total_queries ?? 0).toLocaleString(),
      icon: MessageSquare,
      color: 'text-indigo-600',
      bg: 'bg-indigo-50',
    },
    {
      label: 'Avg Confidence',
      value: stats.avg_confidence != null ? `${Number(stats.avg_confidence).toFixed(1)}%` : '—',
      icon: TrendingUp,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50',
    },
    {
      label: 'Avg Response Time',
      value: stats.avg_response_time != null ? `${Number(stats.avg_response_time).toFixed(2)}s` : '—',
      icon: Clock,
      color: 'text-amber-600',
      bg: 'bg-amber-50',
    },
    {
      label: "Today's Cost",
      value: cost.daily != null ? `$${Number(cost.daily).toFixed(4)}` : '—',
      icon: DollarSign,
      color: 'text-purple-600',
      bg: 'bg-purple-50',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c) => (
        <div key={c.label} className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm">
          <div className="flex items-start justify-between mb-3">
            <p className="text-sm text-slate-500">{c.label}</p>
            <div className={`p-2 rounded-lg ${c.bg}`}>
              <c.icon className={`w-4 h-4 ${c.color}`} />
            </div>
          </div>
          <p className="text-2xl font-bold text-slate-800">{c.value}</p>
        </div>
      ))}
    </div>
  );
}
