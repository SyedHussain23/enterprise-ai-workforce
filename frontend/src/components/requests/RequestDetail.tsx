/**
 * RequestDetail — side drawer that loads on-demand for a single request.
 *
 * Shows the request payload, full audit timeline, and threaded comments.
 * Requester can cancel from here; approvers can add comments.
 */
import { useEffect, useState } from 'react';
import { X, Send, MessageSquare, Clock4 } from 'lucide-react';
import toast from 'react-hot-toast';
import {
  getRequestDetail,
  addRequestComment,
  cancelRequest,
} from '../../api/client';
import type { RequestDetailResponse } from '../../api/types';
import { StatusBadge, actionLabel } from './StatusBadge';
import { Spinner } from '../shared/Spinner';

interface Props {
  requestId: string;
  /** Whether the viewer owns this request (enables Cancel button) */
  isOwner: boolean;
  onClose: () => void;
  onAfterChange?: () => void;
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
}

const EVENT_LABELS: Record<string, string> = {
  action_created:   'Submitted',
  action_approved:  'Approved',
  action_rejected:  'Rejected',
  action_cancelled: 'Cancelled',
  action_commented: 'Commented',
};

export function RequestDetail({ requestId, isOwner, onClose, onAfterChange }: Props) {
  const [data, setData]       = useState<RequestDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [comment, setComment] = useState('');
  const [posting, setPosting] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const r = await getRequestDetail(requestId);
      setData(r);
    } catch (e) {
      toast.error((e as Error).message);
      onClose();
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [requestId]);

  async function postComment() {
    if (!comment.trim() || posting) return;
    setPosting(true);
    try {
      await addRequestComment(requestId, comment.trim());
      setComment('');
      await load();
      onAfterChange?.();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setPosting(false);
    }
  }

  async function handleCancel() {
    if (cancelling) return;
    if (!confirm('Cancel this request? This cannot be undone.')) return;
    setCancelling(true);
    try {
      await cancelRequest(requestId, 'Cancelled by requester');
      toast.success('Request cancelled');
      await load();
      onAfterChange?.();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setCancelling(false);
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex">
      <div className="flex-1 bg-black/40" onClick={onClose} />
      <aside className="w-full max-w-md bg-white shadow-2xl flex flex-col">
        <header className="px-5 py-4 border-b border-slate-100 flex items-start justify-between gap-3 shrink-0">
          <div className="min-w-0 flex-1">
            <p className="text-[11px] uppercase tracking-wider text-slate-400">Request detail</p>
            {data && (
              <h2 className="text-base font-semibold text-slate-800 truncate">
                {actionLabel(data.request.action_type)}
              </h2>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <Spinner className="w-6 h-6 text-indigo-500" />
            </div>
          )}

          {data && (
            <>
              {/* Summary card */}
              <section className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                <div className="flex items-center justify-between gap-2 mb-2">
                  <StatusBadge status={data.request.status} />
                  <span className="text-[10px] font-mono text-slate-400">
                    #{data.request.id.slice(0, 8)}
                  </span>
                </div>
                <p className="text-xs text-slate-500">
                  Submitted by <span className="font-semibold text-slate-700">
                    {data.request.requested_by ?? 'Unknown'}
                  </span> · {fmtDate(data.request.created_at)}
                </p>
                {data.request.notes && (
                  <p className="text-xs italic text-slate-600 mt-2">
                    "{data.request.notes}"
                  </p>
                )}
              </section>

              {/* Payload */}
              <section>
                <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                  Details
                </h3>
                <div className="rounded-xl border border-slate-100 bg-white divide-y divide-slate-50 text-xs">
                  {Object.entries(data.request.payload).length === 0 && (
                    <p className="px-4 py-3 text-slate-400">No additional details</p>
                  )}
                  {Object.entries(data.request.payload).map(([k, v]) => (
                    <div key={k} className="px-4 py-2 flex gap-3">
                      <span className="text-slate-400 capitalize shrink-0" style={{ minWidth: '7rem' }}>
                        {k.replace(/_/g, ' ')}
                      </span>
                      <span className="text-slate-700 font-medium break-all">
                        {typeof v === 'object' ? JSON.stringify(v) : String(v ?? '—')}
                      </span>
                    </div>
                  ))}
                </div>
              </section>

              {/* Timeline */}
              <section>
                <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5 flex items-center gap-1.5">
                  <Clock4 className="w-3 h-3" /> Timeline
                </h3>
                <ol className="relative border-l-2 border-slate-100 ml-1 space-y-3 pl-4">
                  {data.timeline.length === 0 && (
                    <li className="text-xs text-slate-400">No events recorded</li>
                  )}
                  {data.timeline.map((t) => (
                    <li key={t.id} className="relative">
                      <span className="absolute -left-[1.32rem] top-1 w-2.5 h-2.5 rounded-full bg-indigo-500 ring-4 ring-white" />
                      <p className="text-xs font-medium text-slate-700">
                        {EVENT_LABELS[t.event_type] ?? t.event_type.replace(/_/g, ' ')}
                      </p>
                      <p className="text-[10px] text-slate-400">{fmtDate(t.created_at)}</p>
                      {t.payload?.notes != null && typeof t.payload.notes === 'string' && (
                        <p className="text-[11px] text-slate-500 italic mt-0.5">
                          "{t.payload.notes}"
                        </p>
                      )}
                    </li>
                  ))}
                </ol>
              </section>

              {/* Comments */}
              <section>
                <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5 flex items-center gap-1.5">
                  <MessageSquare className="w-3 h-3" /> Discussion ({data.comments.length})
                </h3>
                <div className="space-y-2 mb-3">
                  {data.comments.length === 0 && (
                    <p className="text-xs text-slate-400 italic">No comments yet</p>
                  )}
                  {data.comments.map((c) => (
                    <div key={c.id} className="rounded-lg bg-slate-50 px-3 py-2">
                      <div className="flex items-center justify-between mb-0.5">
                        <p className="text-[11px] font-semibold text-slate-700">{c.author ?? 'Unknown'}</p>
                        <p className="text-[10px] text-slate-400">{fmtDate(c.created_at)}</p>
                      </div>
                      <p className="text-xs text-slate-600 whitespace-pre-wrap">{c.body}</p>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') postComment(); }}
                    placeholder="Add a comment…"
                    maxLength={2000}
                    className="flex-1 text-xs px-3 py-2 rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent placeholder:text-slate-400"
                  />
                  <button
                    onClick={postComment}
                    disabled={posting || !comment.trim()}
                    className="flex items-center gap-1 px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold disabled:opacity-50 transition-colors"
                  >
                    <Send className="w-3 h-3" />
                    Post
                  </button>
                </div>
              </section>
            </>
          )}
        </div>

        {/* Footer — owner can cancel a pending request */}
        {data && isOwner && data.request.status.toLowerCase() === 'pending' && (
          <footer className="px-5 py-3 border-t border-slate-100 shrink-0 bg-slate-50">
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border border-rose-200 text-rose-700 hover:bg-rose-50 text-xs font-semibold disabled:opacity-50 transition-colors"
            >
              {cancelling ? 'Cancelling…' : 'Cancel this request'}
            </button>
          </footer>
        )}
      </aside>
    </div>
  );
}
