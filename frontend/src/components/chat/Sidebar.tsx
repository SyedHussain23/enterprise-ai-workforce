import { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import {
  Plus, MessageSquare, LogOut, Settings, Globe, UserCircle,
  Search, Trash2, Pin, PinOff, Edit3, Check, X, Bot,
} from 'lucide-react';
import clsx from 'clsx';
import type { Session } from '../../api/types';
import { useAuth } from '../../context/AuthContext';
import { useRTL } from '../../context/RTLContext';
import { useNavigate } from 'react-router-dom';

interface Props {
  sessions: Session[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onPin: (id: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

// ── Date grouping helpers ─────────────────────────────────────────────────────
function getGroup(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diff = (now.getTime() - d.getTime()) / 86_400_000;
  if (diff < 1 && d.getDate() === now.getDate()) return 'Today';
  if (diff < 2) return 'Yesterday';
  if (diff < 7) return 'Last 7 days';
  if (diff < 30) return 'Last 30 days';
  return d.toLocaleString('default', { month: 'long', year: 'numeric' });
}

function groupSessions(sessions: Session[]): [string, Session[]][] {
  const pinned = sessions.filter((s) => s.pinnedAt);
  const rest   = sessions.filter((s) => !s.pinnedAt);

  const groups = new Map<string, Session[]>();
  if (pinned.length) groups.set('Pinned', pinned);

  for (const s of rest) {
    const g = getGroup(s.createdAt);
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g)!.push(s);
  }

  return [...groups.entries()];
}

// ── Rename input ──────────────────────────────────────────────────────────────
function RenameInput({
  initial, onSave, onCancel,
}: { initial: string; onSave: (v: string) => void; onCancel: () => void }) {
  const [val, setVal] = useState(initial);
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => { ref.current?.select(); }, []);

  function handleKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') { if (val.trim()) onSave(val.trim()); }
    if (e.key === 'Escape') onCancel();
  }

  return (
    <div className="flex items-center gap-1 flex-1 min-w-0">
      <input
        ref={ref}
        value={val}
        onChange={(e) => setVal(e.target.value)}
        onKeyDown={handleKey}
        onBlur={() => { if (val.trim()) onSave(val.trim()); else onCancel(); }}
        className="flex-1 min-w-0 bg-slate-700 text-white text-xs px-2 py-1 rounded focus:outline-none focus:ring-1 focus:ring-indigo-400"
        maxLength={60}
      />
      <button onClick={() => { if (val.trim()) onSave(val.trim()); }}
        className="p-0.5 text-emerald-400 hover:text-emerald-300">
        <Check className="w-3 h-3" />
      </button>
      <button onClick={onCancel} className="p-0.5 text-slate-400 hover:text-slate-200">
        <X className="w-3 h-3" />
      </button>
    </div>
  );
}

// ── Session row ───────────────────────────────────────────────────────────────
function SessionRow({
  session, isActive, onSelect, onDelete, onRename, onPin,
}: {
  session: Session;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onRename: (title: string) => void;
  onPin: () => void;
}) {
  const [renaming, setRenaming]   = useState(false);
  const [showMenu, setShowMenu]   = useState(false);
  const [confirmDel, setConfirm]  = useState(false);
  const isPinned = !!session.pinnedAt;

  if (renaming) {
    return (
      <div className={clsx(
        'flex items-center gap-1.5 px-2 py-1.5 rounded-lg',
        isActive ? 'bg-slate-700' : 'bg-slate-800',
      )}>
        <MessageSquare className="w-3.5 h-3.5 shrink-0 text-slate-400" />
        <RenameInput
          initial={session.title}
          onSave={(t) => { onRename(t); setRenaming(false); }}
          onCancel={() => setRenaming(false)}
        />
      </div>
    );
  }

  if (confirmDel) {
    return (
      <div className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg bg-red-900/30 border border-red-800/40">
        <span className="text-xs text-red-300 flex-1 truncate">Delete this chat?</span>
        <button onClick={onDelete}
          className="text-xs text-red-400 hover:text-red-300 font-medium px-1.5 py-0.5 rounded hover:bg-red-800/30 transition-colors">
          Delete
        </button>
        <button onClick={() => setConfirm(false)}
          className="text-xs text-slate-400 hover:text-slate-200 px-1.5 py-0.5 rounded hover:bg-slate-700 transition-colors">
          Cancel
        </button>
      </div>
    );
  }

  return (
    <div
      className={clsx(
        'group flex items-center gap-2 px-2 py-1.5 rounded-lg transition-colors cursor-pointer relative',
        isActive
          ? 'bg-slate-700 text-white'
          : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100',
      )}
      onClick={onSelect}
    >
      {isPinned
        ? <Pin className="w-3 h-3 shrink-0 text-indigo-400" />
        : <MessageSquare className="w-3.5 h-3.5 shrink-0 opacity-50" />
      }
      <span className="truncate text-xs flex-1 leading-relaxed">{session.title}</span>

      {/* Hover actions */}
      <div className={clsx(
        'flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0',
        showMenu && 'opacity-100',
      )}>
        <button
          onClick={(e) => { e.stopPropagation(); setRenaming(true); }}
          className="p-1 rounded hover:bg-slate-600 text-slate-400 hover:text-slate-200 transition-colors"
          title="Rename"
        >
          <Edit3 className="w-3 h-3" />
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onPin(); }}
          className="p-1 rounded hover:bg-slate-600 text-slate-400 hover:text-slate-200 transition-colors"
          title={isPinned ? 'Unpin' : 'Pin'}
        >
          {isPinned ? <PinOff className="w-3 h-3" /> : <Pin className="w-3 h-3" />}
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); setConfirm(true); setShowMenu(false); }}
          className="p-1 rounded hover:bg-red-800/40 text-slate-400 hover:text-red-400 transition-colors"
          title="Delete"
        >
          <Trash2 className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}

// ── Main Sidebar ──────────────────────────────────────────────────────────────
export function Sidebar({
  sessions, activeId, onSelect, onNew, onDelete, onRename, onPin, isOpen, onClose,
}: Props) {
  const { logout, isAdmin, role, token } = useAuth();
  const { isRTL, toggleRTL } = useRTL();
  const navigate = useNavigate();
  const [search, setSearch] = useState('');

  const username = (() => {
    try {
      if (!token) return 'user';
      const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
      return payload.sub ?? 'user';
    } catch { return 'user'; }
  })();

  async function handleLogout() {
    await logout();
    navigate('/login');
  }

  const filtered = search.trim()
    ? sessions.filter((s) => s.title.toLowerCase().includes(search.toLowerCase()))
    : sessions;

  const grouped = groupSessions(filtered);

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div className="sidebar-overlay md:hidden" onClick={onClose} />
      )}

      <aside className={clsx(
        'sidebar-width flex flex-col bg-slate-900 text-slate-100 h-full shrink-0',
        'transition-transform duration-300 ease-out',
        // Mobile: slide in/out from left (or right in RTL)
        'fixed md:relative z-50 md:z-auto',
        isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
        isRTL && (isOpen ? 'translate-x-0 right-0 left-auto' : 'translate-x-full md:translate-x-0 right-0 left-auto'),
      )}>
        {/* Brand */}
        <div className="px-4 py-4 border-b border-slate-700/60 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="font-semibold text-sm leading-tight">Enterprise AI</p>
              <p className="text-[11px] text-slate-400">Workforce Assistant</p>
            </div>
          </div>
          {/* Mobile close button */}
          <button onClick={onClose} className="md:hidden p-1 text-slate-400 hover:text-slate-100">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* New chat */}
        <div className="px-3 pt-3 pb-2 shrink-0">
          <button
            onClick={() => { onNew(); onClose(); }}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors active:scale-[0.98]"
          >
            <Plus className="w-4 h-4" />
            {isRTL ? 'محادثة جديدة' : 'New conversation'}
          </button>
        </div>

        {/* Search */}
        <div className="px-3 pb-2 shrink-0">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={isRTL ? 'بحث…' : 'Search conversations…'}
              className="w-full bg-slate-800 text-slate-200 placeholder-slate-500 text-xs pl-8 pr-3 py-2 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all"
            />
            {search && (
              <button onClick={() => setSearch('')} className="absolute right-2 top-1/2 -translate-y-1/2">
                <X className="w-3 h-3 text-slate-500 hover:text-slate-300" />
              </button>
            )}
          </div>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto px-3 py-1 space-y-4">
          {filtered.length === 0 && (
            <p className="text-xs text-slate-500 px-2 py-4 text-center">
              {search ? 'No matching conversations' : (isRTL ? 'لا توجد محادثات' : 'No conversations yet')}
            </p>
          )}

          {grouped.map(([group, items]) => (
            <div key={group}>
              <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider px-2 mb-1.5">
                {group}
              </p>
              <div className="space-y-0.5">
                {items.map((s) => (
                  <SessionRow
                    key={s.id}
                    session={s}
                    isActive={s.id === activeId}
                    onSelect={() => { onSelect(s.id); onClose(); }}
                    onDelete={() => onDelete(s.id)}
                    onRename={(t) => onRename(s.id, t)}
                    onPin={() => onPin(s.id)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="px-3 pb-3 pt-2 border-t border-slate-700/60 shrink-0">
          {/* User info */}
          <div className="flex items-center gap-2.5 px-2 py-2 mb-1">
            <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-xs font-bold text-white shrink-0">
              {username.slice(0, 2).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-slate-200 truncate">{username}</p>
              <span className={clsx(
                'text-[10px] px-1.5 py-0.5 rounded-full font-medium',
                isAdmin ? 'bg-purple-900/60 text-purple-300' : 'bg-slate-700 text-slate-400',
              )}>
                {role ?? 'user'}
              </span>
            </div>
          </div>

          {isAdmin && (
            <button
              onClick={() => { navigate('/admin'); onClose(); }}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-100 text-xs transition-colors"
            >
              <Settings className="w-4 h-4" />
              {isRTL ? 'لوحة الإدارة' : 'Admin dashboard'}
            </button>
          )}

          <button
            onClick={() => { navigate('/profile'); onClose(); }}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-100 text-xs transition-colors"
          >
            <UserCircle className="w-4 h-4" />
            {isRTL ? 'ملفي الشخصي' : 'My profile'}
          </button>

          <button
            onClick={toggleRTL}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-100 text-xs transition-colors"
          >
            <Globe className="w-4 h-4" />
            {isRTL ? 'English' : 'العربية'}
          </button>

          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-red-400 text-xs transition-colors"
          >
            <LogOut className="w-4 h-4" />
            {isRTL ? 'تسجيل الخروج' : 'Sign out'}
          </button>
        </div>
      </aside>
    </>
  );
}
