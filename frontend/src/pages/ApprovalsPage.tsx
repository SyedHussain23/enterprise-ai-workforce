/**
 * Approvals page — manager + admin view.
 *
 * Lists every pending approval in the tenant. Inline Approve / Reject
 * actions with an optional note. Click into a request to see full
 * detail, timeline, and comments.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import toast, { Toaster } from 'react-hot-toast';
import { CheckSquare, Search, CheckCircle, XCircle } from 'lucide-react';
import {
  listPendingApprovals,
  approveAction,
  rejectAction,
} from '../api/client';
import type { RequestSummary } from '../api/types';
import { WorkspaceLayout } from '../components/shared/WorkspaceLayout';
import { StatusBadge, actionLabel } from '../components/requests/StatusBadge';
import { RequestDetail } from '../components/requests/RequestDetail';
import { Spinner } from '../components/shared/Spinner';

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

export function ApprovalsPage() {
  const [items, setItems]     = useState<RequestSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch]   = useState('');
  const [active, setActive]   = useState<string | null>(null);
  const [busy, setBusy]       = useState<string | null>(null);
  const [notes, setNotes]     = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await listPendingApprovals({ limit: 100 });
      setItems(r.items);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    if (!search.trim()) return items;
    const q = search.trim().toLowerCase();
    return items.filter((r) =>
      r.action_type.toLowerCase().includes(q) ||
      r.department.toLowerCase().includes(q) ||
      (r.requested_by?.toLowerCase() ?? '').includes(q),
    );
  }, [items, search]);

  async function decide(id: string, decision: 'approve' | 'reject') {
    setBusy(id);
    try {
      const note = notes[id]?.trim() || undefined;
      if (decision === 'approve') await approveAction(id, { notes: note });
      else                         await rejectAction(id, { notes: note });
      toast.success(decision === 'approve' ? 'Approved — requester notified' : 'Rejected — requester notified');
      setNotes((n) => { const copy = { ...n }; delete copy[id]; return copy; });
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <WorkspaceLayout
      title="Approvals"
      subtitle="Review and decide on pending workflow requests"
    >
      <Toaster position="top-right" />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-5">
        {/* Toolbar */}
        <div className="flex items-center gap-3 mb-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by requester, type, or department…"
              className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
            />
          </div>
          <span className="text-xs text-slate-500 px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-700 font-semibold">
            {filtered.length} pending
          </span>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-12">
            <Spinner className="w-6 h-6 text-indigo-500" />
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <div className="bg-white border border-slate-100 rounded-xl py-16 text-center">
            <CheckSquare className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
            <p className="text-sm font-semibold text-slate-700 mb-1">All caught up</p>
            <p className="text-xs text-slate-400">No pending approvals require your attention</p>
          </div>
        )}

        {!loading && filtered.length > 0 && (
          <div className="space-y-3">
            {filtered.map((r) => (
              <div key={r.id} className="bg-white border border-amber-100 rounded-xl shadow-sm overflow-hidden">
                <button
                  onClick={() => setActive(r.id)}
                  className="w-full text-left px-4 py-3.5 hover:bg-amber-50/40 transition-colors flex items-start gap-3"
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
                      <span>
                        From <span className="font-semibold text-slate-700">{r.requested_by ?? 'System'}</span>
                      </span>
                      <span>·</span>
                      <span className="font-medium">{r.department}</span>
                      <span>·</span>
                      <span>{fmtRelative(r.created_at)}</span>
                    </div>
                    {/* Lightweight payload preview */}
                    {r.payload && (
                      <p className="text-xs text-slate-500 mt-1 line-clamp-1">
                        {Object.entries(r.payload)
                          .filter(([k]) => !['execution_result', 'session_id', 'raw_request'].includes(k))
                          .slice(0, 3)
                          .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${typeof v === 'object' ? JSON.stringify(v) : v}`)
                          .join(' · ')}
                      </p>
                    )}
                  </div>
                  <span className="text-xs text-indigo-500 hover:text-indigo-700 shrink-0 self-center">
                    Detail →
                  </span>
                </button>

                {/* Inline decision row */}
                <div className="px-4 py-3 border-t border-amber-100 bg-amber-50/30 flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                  <input
                    type="text"
                    placeholder="Optional note for the requester"
                    value={notes[r.id] ?? ''}
                    onChange={(e) => setNotes((prev) => ({ ...prev, [r.id]: e.target.value }))}
                    className="flex-1 text-xs px-3 py-1.5 rounded-lg border border-amber-200 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent placeholder:text-slate-400"
                  />
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => decide(r.id, 'approve')}
                      disabled={busy === r.id}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold disabled:opacity-50 transition-colors"
                    >
                      <CheckCircle className="w-3.5 h-3.5" />
                      Approve
                    </button>
                    <button
                      onClick={() => decide(r.id, 'reject')}
                      disabled={busy === r.id}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-rose-200 text-rose-700 hover:bg-rose-50 text-xs font-semibold disabled:opacity-50 transition-colors"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      Reject
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {active && (
        <RequestDetail
          requestId={active}
          isOwner={false}
          onClose={() => setActive(null)}
          onAfterChange={load}
        />
      )}
    </WorkspaceLayout>
  );
}
