/**
 * Requests page — "My Requests" workflow center.
 *
 * Where employees go to track everything they've submitted. Status, last
 * update, click into a side drawer for the full timeline + comments +
 * cancel.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import toast, { Toaster } from 'react-hot-toast';
import { Inbox, Search } from 'lucide-react';
import { listMyRequests } from '../api/client';
import type { RequestSummary } from '../api/types';
import { WorkspaceLayout } from '../components/shared/WorkspaceLayout';
import { StatusBadge, actionLabel } from '../components/requests/StatusBadge';
import { RequestDetail } from '../components/requests/RequestDetail';
import { Spinner } from '../components/shared/Spinner';
import clsx from 'clsx';

const STATUS_OPTIONS = [
  { value: '',          label: 'All' },
  { value: 'pending',   label: 'Pending' },
  { value: 'approved',  label: 'Approved' },
  { value: 'completed', label: 'Executed' },
  { value: 'rejected',  label: 'Rejected' },
  { value: 'cancelled', label: 'Cancelled' },
];

function fmtRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1)    return 'just now';
  if (m < 60)   return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24)   return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7)    return `${d}d ago`;
  return new Date(iso).toLocaleDateString();
}

export function RequestsPage() {
  const [params, setParams] = useSearchParams();
  const [items, setItems]   = useState<RequestSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');
  const [active, setActive] = useState<string | null>(null);

  // Open the detail drawer from a deep-link (?focus=<id>)
  useEffect(() => {
    const focus = params.get('focus');
    if (focus) {
      setActive(focus);
      params.delete('focus');
      setParams(params, { replace: true });
    }
  }, [params, setParams]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await listMyRequests({ limit: 100, status: status || undefined });
      setItems(r.requests);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    if (!search.trim()) return items;
    const q = search.trim().toLowerCase();
    return items.filter((r) =>
      r.action_type.toLowerCase().includes(q) ||
      r.department.toLowerCase().includes(q) ||
      r.status.toLowerCase().includes(q) ||
      (r.notes?.toLowerCase() ?? '').includes(q),
    );
  }, [items, search]);

  return (
    <WorkspaceLayout
      title="My Requests"
      subtitle="Track every workflow you've submitted — status, history, comments"
    >
      <Toaster position="top-right" />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-5">
        {/* Toolbar */}
        <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search requests by type, department, or notes…"
              className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
            />
          </div>
          <div className="flex items-center gap-1 bg-white border border-slate-200 rounded-lg p-1 overflow-x-auto">
            {STATUS_OPTIONS.map((opt) => (
              <button
                key={opt.value || 'all'}
                onClick={() => setStatus(opt.value)}
                className={clsx(
                  'px-3 py-1 rounded-md text-xs font-medium transition-colors whitespace-nowrap',
                  status === opt.value
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-600 hover:bg-slate-100',
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* List */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Spinner className="w-6 h-6 text-indigo-500" />
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <div className="bg-white border border-slate-100 rounded-xl py-16 text-center">
            <Inbox className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <p className="text-sm font-semibold text-slate-700 mb-1">
              {search || status ? 'No matching requests' : 'No requests yet'}
            </p>
            <p className="text-xs text-slate-400">
              {search || status
                ? 'Try a different search or status filter'
                : 'Ask the AI assistant to apply for leave, submit an expense, or report an IT issue'}
            </p>
          </div>
        )}

        {!loading && filtered.length > 0 && (
          <div className="bg-white border border-slate-100 rounded-xl divide-y divide-slate-100 overflow-hidden">
            {filtered.map((r) => (
              <button
                key={r.id}
                onClick={() => setActive(r.id)}
                className="w-full text-left px-4 py-3.5 hover:bg-slate-50 transition-colors flex items-start gap-3"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <p className="text-sm font-semibold text-slate-800">
                      {actionLabel(r.action_type)}
                    </p>
                    <StatusBadge status={r.status} />
                    <span className="text-[10px] font-mono text-slate-400">
                      #{r.id.slice(0, 8)}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-slate-500">
                    <span className="font-medium">{r.department}</span>
                    <span>·</span>
                    <span>{fmtRelative(r.created_at)}</span>
                    {r.approved_at && (
                      <>
                        <span>·</span>
                        <span>updated {fmtRelative(r.approved_at)}</span>
                      </>
                    )}
                  </div>
                  {r.notes && (
                    <p className="text-xs italic text-slate-500 mt-1 line-clamp-1">"{r.notes}"</p>
                  )}
                </div>
                <span className="text-xs text-indigo-500 hover:text-indigo-700 shrink-0 self-center">
                  View →
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {active && (
        <RequestDetail
          requestId={active}
          isOwner={true}
          onClose={() => setActive(null)}
          onAfterChange={load}
        />
      )}
    </WorkspaceLayout>
  );
}
