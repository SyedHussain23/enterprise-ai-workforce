import { Plus, MessageSquare, LogOut, Settings, Globe } from 'lucide-react';
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
}

export function Sidebar({ sessions, activeId, onSelect, onNew }: Props) {
  const { logout, isAdmin, role } = useAuth();
  const { isRTL, toggleRTL } = useRTL();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <aside className="flex flex-col w-64 bg-slate-900 text-slate-100 h-screen shrink-0">
      {/* Brand */}
      <div className="px-4 py-4 border-b border-slate-700">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold text-sm">
            AI
          </div>
          <div>
            <p className="font-semibold text-sm leading-none">Enterprise AI</p>
            <p className="text-xs text-slate-400 mt-0.5">Workforce Assistant</p>
          </div>
        </div>
      </div>

      {/* New chat */}
      <div className="px-3 pt-3">
        <button
          onClick={onNew}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          {isRTL ? 'محادثة جديدة' : 'New conversation'}
        </button>
      </div>

      {/* Sessions list */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-0.5">
        {sessions.length === 0 && (
          <p className="text-xs text-slate-500 px-2 py-3">
            {isRTL ? 'لا توجد محادثات' : 'No conversations yet'}
          </p>
        )}
        {sessions.map((s) => (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={clsx(
              'w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-start transition-colors',
              activeId === s.id
                ? 'bg-slate-700 text-white'
                : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100',
            )}
          >
            <MessageSquare className="w-3.5 h-3.5 shrink-0 opacity-60" />
            <span className="truncate">{s.title}</span>
          </button>
        ))}
      </div>

      {/* Footer */}
      <div className="px-3 pb-3 pt-2 border-t border-slate-700 space-y-0.5">
        {/* Role badge */}
        <div className="px-3 py-1.5 mb-1">
          <span className={clsx(
            'text-xs px-2 py-0.5 rounded-full font-medium',
            isAdmin ? 'bg-purple-900 text-purple-300' : 'bg-slate-700 text-slate-400',
          )}>
            {role ?? 'user'}
          </span>
        </div>

        {isAdmin && (
          <button
            onClick={() => navigate('/admin')}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-100 text-sm transition-colors"
          >
            <Settings className="w-4 h-4" />
            {isRTL ? 'لوحة الإدارة' : 'Admin dashboard'}
          </button>
        )}

        <button
          onClick={toggleRTL}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-100 text-sm transition-colors"
        >
          <Globe className="w-4 h-4" />
          {isRTL ? 'English' : 'عربي'}
        </button>

        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-red-400 text-sm transition-colors"
        >
          <LogOut className="w-4 h-4" />
          {isRTL ? 'تسجيل الخروج' : 'Sign out'}
        </button>
      </div>
    </aside>
  );
}
