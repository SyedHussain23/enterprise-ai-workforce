/**
 * WorkspaceLayout — shell for non-chat pages.
 *
 * Provides a polished sidebar with role-aware nav and a header that hosts
 * the notification bell + user menu. Keeps every workspace page visually
 * consistent and saves us from re-implementing nav per page.
 */
import { type ReactNode, useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Bot, MessageSquare, Inbox, CheckSquare, Shield, UserCircle,
  LogOut, Globe, Menu, X,
} from 'lucide-react';
import clsx from 'clsx';
import { useAuth } from '../../context/AuthContext';
import { useRTL } from '../../context/RTLContext';
import { NotificationBell } from './NotificationBell';
import { getApprovalsStats } from '../../api/client';

interface Props {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
}

interface NavItemConfig {
  to:    string;
  label: string;
  icon:  ReactNode;
  show:  boolean;
  badge?: number;
}

export function WorkspaceLayout({ children, title, subtitle, actions }: Props) {
  const { logout, role, isAdmin, token } = useAuth();
  const { isRTL, toggleRTL } = useRTL();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [pendingApprovals, setPendingApprovals] = useState(0);

  const username = (() => {
    try {
      if (!token) return 'user';
      const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
      return payload.sub ?? 'user';
    } catch { return 'user'; }
  })();

  const isApprover = isAdmin || role === 'manager';

  // Poll approval badge (managers/admins only)
  useEffect(() => {
    if (!isApprover) return;
    let cancelled = false;
    async function tick() {
      try {
        const r = await getApprovalsStats();
        if (!cancelled) setPendingApprovals(r.pending);
      } catch { /* silent */ }
    }
    tick();
    const id = setInterval(tick, 45_000);
    return () => { cancelled = true; clearInterval(id); };
  }, [isApprover]);

  const nav: NavItemConfig[] = [
    { to: '/chat',      label: 'Chat',      icon: <MessageSquare className="w-4 h-4" />, show: true },
    { to: '/requests',  label: 'Requests',  icon: <Inbox className="w-4 h-4" />,         show: true },
    { to: '/approvals', label: 'Approvals', icon: <CheckSquare className="w-4 h-4" />,   show: isApprover, badge: pendingApprovals },
    { to: '/admin',     label: 'Admin',     icon: <Shield className="w-4 h-4" />,        show: isAdmin },
  ];

  async function handleLogout() {
    await logout();
    navigate('/login');
  }

  return (
    <div className={clsx('flex h-screen overflow-hidden', isRTL ? 'flex-row-reverse' : 'flex-row')}>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-black/40 z-40 md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={clsx(
        'w-64 flex flex-col bg-slate-900 text-slate-100 h-full shrink-0',
        'transition-transform duration-300 ease-out',
        'fixed md:relative z-50',
        open ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
        isRTL && (open ? 'translate-x-0 right-0 left-auto' : 'translate-x-full md:translate-x-0 right-0 left-auto'),
      )}>
        <div className="px-4 py-4 border-b border-slate-700/60 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="font-semibold text-sm leading-tight">Enterprise AI</p>
              <p className="text-[11px] text-slate-400">Workforce Platform</p>
            </div>
          </div>
          <button onClick={() => setOpen(false)} className="md:hidden p-1 text-slate-400 hover:text-slate-100">
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {nav.filter((n) => n.show).map((n) => {
            const active = pathname === n.to || pathname.startsWith(`${n.to}/`);
            return (
              <Link
                key={n.to}
                to={n.to}
                onClick={() => setOpen(false)}
                className={clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  active
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100',
                )}
              >
                {n.icon}
                <span className="flex-1">{n.label}</span>
                {n.badge != null && n.badge > 0 && (
                  <span className={clsx(
                    'px-1.5 py-0.5 rounded-full text-[10px] font-bold',
                    active ? 'bg-white/20 text-white' : 'bg-rose-500 text-white',
                  )}>
                    {n.badge > 99 ? '99+' : n.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        <div className="px-3 pb-3 pt-2 border-t border-slate-700/60 shrink-0">
          <div className="flex items-center gap-2.5 px-2 py-2 mb-1">
            <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-xs font-bold text-white shrink-0">
              {username.slice(0, 2).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-slate-200 truncate">{username}</p>
              <span className={clsx(
                'text-[10px] px-1.5 py-0.5 rounded-full font-medium',
                isAdmin
                  ? 'bg-purple-900/60 text-purple-300'
                  : role === 'manager'
                    ? 'bg-amber-900/60 text-amber-300'
                    : 'bg-slate-700 text-slate-400',
              )}>
                {role ?? 'user'}
              </span>
            </div>
          </div>

          <button
            onClick={() => navigate('/profile')}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-100 text-xs transition-colors"
          >
            <UserCircle className="w-4 h-4" />
            My profile
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
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-slate-50">
        <header className="bg-white border-b border-slate-100 px-4 sm:px-6 py-3 flex items-center gap-3 shrink-0 z-10">
          <button
            onClick={() => setOpen(true)}
            className="md:hidden p-1.5 -ml-1 text-slate-500 hover:text-slate-800 rounded-lg hover:bg-slate-100"
            aria-label="Open menu"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex-1 min-w-0">
            <h1 className="text-base font-semibold text-slate-800 leading-tight truncate">{title}</h1>
            {subtitle && (
              <p className="text-[11px] text-slate-400 truncate">{subtitle}</p>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {actions}
            <NotificationBell />
          </div>
        </header>
        <div className="flex-1 overflow-y-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
