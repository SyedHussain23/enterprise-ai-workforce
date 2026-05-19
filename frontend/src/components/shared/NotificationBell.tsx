/**
 * Notification bell — fits in any header.
 *
 * Polls the unread-count endpoint every 45 seconds (long enough to avoid
 * hammering the API; short enough to feel "live"). On open, fetches the
 * latest 20 notifications. Click → mark-read + navigate to the source.
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, CheckCheck, X } from 'lucide-react';
import clsx from 'clsx';
import {
  listNotifications,
  getUnreadCount,
  markNotificationRead,
  markAllNotificationsRead,
} from '../../api/client';
import type { NotificationItem } from '../../api/types';

const KIND_ICON: Record<string, string> = {
  request_submitted: '📥',
  request_approved:  '✅',
  request_rejected:  '⛔',
  request_commented: '💬',
  request_completed: '⚡',
  request_escalated: '⏫',
  system:            '🛎️',
};

function fmtTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1)    return 'just now';
  if (m < 60)   return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24)   return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

export function NotificationBell({ compact = false }: { compact?: boolean }) {
  const [open,    setOpen]    = useState(false);
  const [unread,  setUnread]  = useState(0);
  const [items,   setItems]   = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Poll unread count
  useEffect(() => {
    let cancelled = false;
    async function tick() {
      try {
        const r = await getUnreadCount();
        if (!cancelled) setUnread(r.unread_count);
      } catch {
        // silent — never break the UI for a poll error
      }
    }
    tick();
    const id = setInterval(tick, 45_000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (!dropdownRef.current?.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next) {
      setLoading(true);
      try {
        const r = await listNotifications({ limit: 20 });
        setItems(r.notifications);
        setUnread(r.unread_count);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
  }

  async function clickItem(n: NotificationItem) {
    setOpen(false);
    if (!n.is_read) {
      try {
        await markNotificationRead(n.id);
        setUnread((u) => Math.max(0, u - 1));
        setItems((arr) => arr.map((it) => it.id === n.id ? { ...it, is_read: true } : it));
      } catch {/* ignore */}
    }
    // Deep-link to the source entity
    if (n.entity_type === 'action' && n.entity_id) {
      navigate(`/requests?focus=${n.entity_id}`);
    }
  }

  async function markAll() {
    try {
      await markAllNotificationsRead();
      setUnread(0);
      setItems((arr) => arr.map((it) => ({ ...it, is_read: true })));
    } catch {/* ignore */}
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={toggle}
        className={clsx(
          'relative p-2 rounded-lg transition-colors',
          compact ? 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
                  : 'text-slate-500 hover:text-slate-800 hover:bg-slate-100',
        )}
        aria-label="Notifications"
        title="Notifications"
      >
        <Bell className="w-4.5 h-4.5" style={{ width: '1.125rem', height: '1.125rem' }} />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[1.1rem] h-[1.1rem] px-1 rounded-full bg-rose-500 text-white text-[10px] font-bold flex items-center justify-center ring-2 ring-white">
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-[22rem] bg-white rounded-xl shadow-xl border border-slate-200 z-50 max-h-[28rem] overflow-hidden flex flex-col">
          {/* Header */}
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between bg-slate-50">
            <p className="text-sm font-semibold text-slate-800">Notifications</p>
            <div className="flex items-center gap-1">
              {unread > 0 && (
                <button
                  onClick={markAll}
                  className="flex items-center gap-1 text-[11px] text-indigo-600 hover:text-indigo-800 font-medium"
                  title="Mark all as read"
                >
                  <CheckCheck className="w-3 h-3" />
                  Mark all read
                </button>
              )}
              <button
                onClick={() => setOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded"
                aria-label="Close"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Body */}
          <div className="overflow-y-auto flex-1">
            {loading && (
              <p className="text-xs text-slate-400 text-center py-8">Loading…</p>
            )}
            {!loading && items.length === 0 && (
              <div className="text-center py-10 px-4">
                <p className="text-4xl mb-2">🎉</p>
                <p className="text-sm font-medium text-slate-600">You're all caught up</p>
                <p className="text-xs text-slate-400 mt-1">No notifications right now</p>
              </div>
            )}
            {!loading && items.map((n) => (
              <button
                key={n.id}
                onClick={() => clickItem(n)}
                className={clsx(
                  'w-full text-left px-4 py-3 border-b border-slate-50 hover:bg-slate-50 transition-colors',
                  !n.is_read && 'bg-indigo-50/40',
                )}
              >
                <div className="flex gap-2.5">
                  <span className="text-lg shrink-0 leading-none mt-0.5">
                    {KIND_ICON[n.kind] ?? '🔔'}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <p className={clsx(
                        'text-xs font-semibold text-slate-800 truncate',
                        !n.is_read && 'text-slate-900',
                      )}>
                        {n.title}
                      </p>
                      {!n.is_read && (
                        <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 shrink-0" />
                      )}
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{n.message}</p>
                    <p className="text-[10px] text-slate-400 mt-1">{fmtTime(n.created_at)}</p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
