import { useState } from 'react';
import { ChevronDown, ChevronRight, Cpu } from 'lucide-react';
import type { WorkflowResponse } from '../../api/types';
import { AgentBadge } from '../shared/AgentBadge';
import { ConfidenceBadge } from '../shared/ConfidenceBadge';

interface Props {
  metadata: WorkflowResponse;
}

export function AgentTrace({ metadata }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-2 border border-slate-100 rounded-lg overflow-hidden text-xs">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-slate-50 hover:bg-slate-100 transition-colors text-slate-500"
      >
        {open ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        <Cpu className="w-3.5 h-3.5" />
        <span className="font-medium">Agent trace</span>
        <div className="ml-auto flex items-center gap-2">
          <AgentBadge agent={metadata.agent} />
          <ConfidenceBadge score={metadata.confidence} />
        </div>
      </button>

      {open && (
        <div className="px-3 py-2 space-y-2 bg-white">
          {/* Steps timeline */}
          <div className="space-y-1">
            {metadata.steps.map((step, i) => (
              <div key={i} className="flex items-start gap-2">
                <div className="mt-1 w-4 h-4 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-[10px] font-bold shrink-0">
                  {i + 1}
                </div>
                <p className="text-slate-600">{step}</p>
              </div>
            ))}
          </div>

          {/* Meta info */}
          <div className="pt-2 border-t border-slate-100 grid grid-cols-2 gap-x-4 gap-y-1 text-slate-500">
            <span>Source</span>
            <span className="font-medium text-slate-700">{metadata.source}</span>
            <span>Response time</span>
            <span className="font-medium text-slate-700">{metadata.response_time.toFixed(2)}s</span>
            {metadata.evaluation_score != null && (
              <>
                <span>Eval score</span>
                <span className="font-medium text-slate-700">{metadata.evaluation_score.toFixed(1)}/10</span>
              </>
            )}
            {metadata.confidence_reason && (
              <>
                <span className="col-span-2 text-slate-400 italic">{metadata.confidence_reason}</span>
              </>
            )}
          </div>

          {/* Action info */}
          {metadata.action_id && (
            <div className="pt-2 border-t border-slate-100">
              <span className="font-medium text-indigo-600">Action triggered: </span>
              <span className="text-slate-600">{metadata.action_type}</span>
              <span className={`ml-2 px-1.5 py-0.5 rounded text-[10px] font-medium ${
                metadata.action_status === 'APPROVED' ? 'bg-emerald-50 text-emerald-700' :
                metadata.action_status === 'REJECTED' ? 'bg-red-50 text-red-700' :
                'bg-amber-50 text-amber-700'
              }`}>
                {metadata.action_status}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
