import { useState } from 'react';
import { CheckCircle, XCircle, Clock } from 'lucide-react';
import { approveAction, rejectAction } from '../../api/client';
import type { Action } from '../../api/types';
import clsx from 'clsx';

interface Props {
  actions: Action[];
  onRefresh: () => void;
}

const ACTION_LABELS: Record<string, string> = {
  apply_leave: 'Apply Leave',
  update_profile: 'Update Profile',
  create_ticket: 'IT Ticket',
  request_access: 'Access Request',
  submit_expense: 'Submit Expense',
  request_advance: 'Salary Advance',
  generate_report: 'Generate Report',
};

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
        <p className="text-sm text-slate-500">All caught up — no pending actions</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {actions.map((a) => (
        <div key={a.id} className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <Clock className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                <span className="text-sm font-medium text-slate-800">
                  {ACTION_LABELS[a.action_type] ?? a.action_type}
                </span>
                <span className={clsx(
                  'px-1.5 py-0.5 rounded text-xs font-medium',
                  a.status === 'PENDING' ? 'bg-amber-50 text-amber-700' :
                  a.status === 'APPROVED' ? 'bg-emerald-50 text-emerald-700' :
                  'bg-red-50 text-red-700',
                )}>
                  {a.status}
                </span>
              </div>
              <p className="text-xs text-slate-400 mb-2">
                {new Date(a.created_at).toLocaleString()} · ID: {a.id.slice(0, 8)}…
              </p>
              {a.payload && (
                <pre className="text-xs bg-slate-50 rounded-lg p-2 text-slate-600 overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(a.payload, null, 2)}
                </pre>
              )}
            </div>
          </div>

          {a.status === 'PENDING' && (
            <div className="mt-3 flex items-center gap-2">
              <input
                type="text"
                placeholder="Notes (optional)"
                value={notes[a.id] ?? ''}
                onChange={(e) => setNotes((prev) => ({ ...prev, [a.id]: e.target.value }))}
                className="flex-1 text-xs px-3 py-1.5 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
              />
              <button
                onClick={() => handle(a.id, 'approve')}
                disabled={processing === a.id}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium disabled:opacity-50 transition-colors"
              >
                <CheckCircle className="w-3.5 h-3.5" />
                Approve
              </button>
              <button
                onClick={() => handle(a.id, 'reject')}
                disabled={processing === a.id}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-medium disabled:opacity-50 transition-colors"
              >
                <XCircle className="w-3.5 h-3.5" />
                Reject
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
