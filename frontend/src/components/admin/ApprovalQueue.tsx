import { useState } from 'react';
import { CheckCircle, XCircle, Clock, User, Zap, ChevronDown, ChevronUp } from 'lucide-react';
import { approveAction, rejectAction } from '../../api/client';
import type { Action } from '../../api/types';
import clsx from 'clsx';

interface Props {
  actions: Action[];
  onRefresh: () => void;
}

const ACTION_LABELS: Record<string, string> = {
  apply_leave:         'Leave Request',
  update_profile:      'Profile Update',
  request_certificate: 'Certificate Request',
  create_ticket:       'IT Support Ticket',
  reset_password:      'Password Reset',
  request_access:      'Access Request',
  submit_expense:      'Expense Claim',
  request_advance:     'Salary Advance',
  query_payslip:       'Payslip Request',
  generate_report:     'Report Generated',
};

const STATUS_STYLES: Record<string, { bg: string; text: string; icon: JSX.Element }> = {
  PENDING:   { bg: 'bg-amber-50 border-amber-200',   text: 'text-amber-700',   icon: <Clock className="w-3.5 h-3.5" /> },
  APPROVED:  { bg: 'bg-emerald-50 border-emerald-200', text: 'text-emerald-700', icon: <CheckCircle className="w-3.5 h-3.5" /> },
  COMPLETED: { bg: 'bg-emerald-50 border-emerald-200', text: 'text-emerald-700', icon: <Zap className="w-3.5 h-3.5" /> },
  REJECTED:  { bg: 'bg-rose-50 border-rose-200',     text: 'text-rose-700',    icon: <XCircle className="w-3.5 h-3.5" /> },
};

function PayloadPreview({ payload }: { payload: Record<string, unknown> }) {
  const [expanded, setExpanded] = useState(false);

  // Build a friendly key-value summary (exclude internal/result keys)
  const SKIP_KEYS = new Set(['execution_result', 'session_id']);
  const entries = Object.entries(payload).filter(([k]) => !SKIP_KEYS.has(k));

  return (
    <div className="mt-2">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition-colors"
      >
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        {expanded ? 'Hide details' : 'Show details'}
      </button>
      {expanded && (
        <div className="mt-2 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 space-y-1">
          {entries.map(([k, v]) => (
            <div key={k} className="flex gap-2 text-xs">
              <span className="text-slate-400 capitalize shrink-0" style={{ minWidth: '8rem' }}>
                {k.replace(/_/g, ' ')}
              </span>
              <span className="text-slate-700 font-medium break-all">
                {typeof v === 'object' ? JSON.stringify(v) : String(v ?? '—')}
              </span>
            </div>
          ))}
          {payload.execution_result && (
            <div className="mt-2 pt-2 border-t border-slate-200">
              <p className="text-[10px] text-emerald-600 font-semibold uppercase tracking-wide mb-1">Execution Result</p>
              {Object.entries(payload.execution_result as Record<string, unknown>).map(([k, v]) => (
                <div key={k} className="flex gap-2 text-xs">
                  <span className="text-slate-400 capitalize shrink-0" style={{ minWidth: '8rem' }}>
                    {k.replace(/_/g, ' ')}
                  </span>
                  <span className="text-slate-700 font-medium break-all">{String(v ?? '—')}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ApprovalQueue({ actions, onRefresh }: Props) {
  const [processing, setProcessing] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});

  async function handle(id: string, action: 'approve' | 'reject') {
    setProcessing(id);
    try {
      if (action === 'approve') await approveAction(id, { notes: notes[id] });
      else await rejectAction(id, { notes: notes[id] });
      onRefresh();
    } finally {
      setProcessing(null);
    }
  }

  if (actions.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-100 p-8 shadow-sm text-center">
        <CheckCircle className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
        <p className="text-sm font-medium text-slate-600">All caught up</p>
        <p className="text-xs text-slate-400 mt-1">No pending actions require your attention</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {actions.map((a) => {
        const style = STATUS_STYLES[a.status] ?? STATUS_STYLES.PENDING;
        return (
          <div key={a.id} className={`rounded-xl border px-4 py-3.5 shadow-sm ${style.bg}`}>
            {/* Header row */}
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2 mb-1.5">
                  <span className={`flex items-center gap-1 ${style.text}`}>
                    {style.icon}
                    <span className="text-sm font-semibold">
                      {ACTION_LABELS[a.action_type] ?? a.action_type.replace(/_/g, ' ')}
                    </span>
                  </span>
                  <span className={clsx(
                    'px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide',
                    a.status === 'PENDING'   ? 'bg-amber-100 text-amber-700' :
                    a.status === 'COMPLETED' ? 'bg-emerald-100 text-emerald-700' :
                    a.status === 'APPROVED'  ? 'bg-emerald-100 text-emerald-700' :
                    'bg-rose-100 text-rose-700',
                  )}>
                    {a.status === 'COMPLETED' ? '⚡ Executed' : a.status}
                  </span>
                </div>

                {/* Metadata row */}
                <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
                  {a.requested_by && (
                    <span className="flex items-center gap-1">
                      <User className="w-3 h-3" />
                      <span className="font-medium text-slate-700">{a.requested_by}</span>
                    </span>
                  )}
                  <span>{new Date(a.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</span>
                  <span className="font-mono opacity-60">#{a.id.slice(0, 8)}</span>
                </div>

                {/* Notes (if set) */}
                {a.notes && (
                  <p className={`text-xs mt-1.5 italic ${style.text} opacity-80`}>
                    "{a.notes}"
                  </p>
                )}

                {/* Payload preview */}
                {a.payload && <PayloadPreview payload={a.payload} />}
              </div>
            </div>

            {/* Action buttons — only for PENDING */}
            {a.status === 'PENDING' && (
              <div className="mt-3 pt-3 border-t border-amber-200 flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Notes (optional)"
                  value={notes[a.id] ?? ''}
                  onChange={(e) => setNotes((prev) => ({ ...prev, [a.id]: e.target.value }))}
                  className="flex-1 text-xs px-3 py-1.5 rounded-lg border border-amber-200 bg-white/80 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent placeholder:text-slate-400"
                />
                <button
                  onClick={() => handle(a.id, 'approve')}
                  disabled={processing === a.id}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold disabled:opacity-50 transition-colors"
                >
                  <CheckCircle className="w-3.5 h-3.5" />
                  Approve & Execute
                </button>
                <button
                  onClick={() => handle(a.id, 'reject')}
                  disabled={processing === a.id}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold disabled:opacity-50 transition-colors"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  Reject
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
