import { useState } from 'react';
import { ChevronDown, ChevronRight, Cpu, Clock, Zap } from 'lucide-react';
import type { WorkflowResponse } from '../../api/types';
import { AgentBadge } from '../shared/AgentBadge';
import { ConfidenceBadge } from '../shared/ConfidenceBadge';

interface Props {
  metadata: WorkflowResponse;
}

export function AgentTrace({ metadata }: Props) {
  const [open, setOpen] = useState(false);

  // Defensive — steps may be undefined from older cached responses
  const steps: string[] = Array.isArray(metadata.steps) ? metadata.steps : [];

  return (
    <div className="mt-3 border border-slate-100 rounded-xl overflow-hidden text-xs">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-slate-50 hover:bg-slate-100 transition-colors text-slate-500"
      >
        {open
          ? <ChevronDown className="w-3.5 h-3.5 shrink-0" />
          : <ChevronRight className="w-3.5 h-3.5 shrink-0" />
        }
        <Cpu className="w-3.5 h-3.5 shrink-0" />
        <span className="font-medium">Agent trace</span>

        <div className="ml-auto flex items-center gap-2">
          <AgentBadge agent={metadata.agent} />
          <ConfidenceBadge score={metadata.confidence} />
          <span className="text-slate-400 flex items-center gap-0.5">
            <Zap className="w-3 h-3" />
            {metadata.response_time.toFixed(2)}s
          </span>
        </div>
      </button>

      {open && (
        <div className="px-3 py-3 space-y-3 bg-white animate-fade-in">
          {/* Steps timeline */}
          {steps.length > 0 && (
            <div className="space-y-1.5">
              {steps.map((step, i) => (
                <div key={i} className="flex items-start gap-2">
                  <div className="mt-0.5 w-4 h-4 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-[10px] font-bold shrink-0">
                    {i + 1}
                  </div>
                  <p className="text-slate-600 leading-relaxed">{step}</p>
                </div>
              ))}
            </div>
          )}

          {/* Meta grid */}
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-slate-500 border-t border-slate-50 pt-2">
            <span className="text-slate-400">Source</span>
            <span className="font-medium text-slate-700">{metadata.source || '—'}</span>

            <span className="text-slate-400">Response time</span>
            <span className="font-medium text-slate-700 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {metadata.response_time.toFixed(2)}s
            </span>

            {metadata.evaluation_score != null && (
              <>
                <span className="text-slate-400">Eval score</span>
                <span className="font-medium text-slate-700">
                  {metadata.evaluation_score.toFixed(1)}/10
                </span>
              </>
            )}

            {metadata.confidence_reason && (
              <p className="col-span-2 text-slate-400 italic leading-relaxed">
                {metadata.confidence_reason}
              </p>
            )}
          </div>

          {/* Action info */}
          {metadata.action_id && (
            <div className="flex items-center gap-2 pt-1 border-t border-slate-50">
              <span className="font-medium text-indigo-600">Action:</span>
              <span className="text-slate-600">{metadata.action_type}</span>
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
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
