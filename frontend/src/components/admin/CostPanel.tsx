import { DollarSign, TrendingUp, Info } from 'lucide-react';
import type { CostStats } from '../../api/types';

interface Props {
  cost: CostStats;
}

export function CostPanel({ cost }: Props) {
  return (
    <div className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <DollarSign className="w-4 h-4 text-purple-600" />
        <h3 className="text-sm font-semibold text-slate-700">Cost Analytics</h3>
        <div className="ml-auto group relative">
          <Info className="w-3.5 h-3.5 text-slate-400 cursor-help" />
          <div className="absolute right-0 bottom-5 w-48 bg-slate-800 text-white text-xs rounded-lg p-2 opacity-0 group-hover:opacity-100 transition-opacity z-10 pointer-events-none">
            GPT-4o pricing: $0.005/1K input tokens, $0.015/1K output tokens
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="p-3 rounded-xl bg-purple-50">
          <p className="text-xs text-purple-600 font-medium mb-1">Today</p>
          <p className="text-xl font-bold text-purple-800">{cost.daily != null ? `$${Number(cost.daily).toFixed(4)}` : '—'}</p>
          <p className="text-xs text-purple-500 mt-1">USD</p>
        </div>
        <div className="p-3 rounded-xl bg-slate-50">
          <p className="text-xs text-slate-600 font-medium mb-1">Lifetime</p>
          <p className="text-xl font-bold text-slate-800">{cost.lifetime != null ? `$${Number(cost.lifetime).toFixed(4)}` : '—'}</p>
          <p className="text-xs text-slate-500 mt-1">USD</p>
        </div>
      </div>

      <div className="mt-3 flex items-center gap-1.5 text-xs text-slate-400">
        <TrendingUp className="w-3.5 h-3.5" />
        <span>Tracked per company · Redis-backed counters</span>
      </div>
    </div>
  );
}
