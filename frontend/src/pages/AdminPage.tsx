import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import {
  ArrowLeft, RefreshCw, Shield, Users, FileText, BarChart2,
  CheckCircle, XCircle, ChevronLeft, ChevronRight, AlertTriangle,
  LogIn, Activity, Wifi, WifiOff, Database, Cpu, Server,
} from 'lucide-react';
import {
  getAdminStats, getCostStats, getPendingActions,
  listUsers, updateUser, getAuditLogs, getHealthDeep, AuthError,
} from '../api/client';
import type { AdminStats, CostStats, Action, AdminUser, AuditLogEntry } from '../api/types';
import { StatsCards }     from '../components/admin/StatsCards';
import { DepartmentChart } from '../components/admin/DepartmentChart';
import { ApprovalQueue }   from '../components/admin/ApprovalQueue';
import { CostPanel }       from '../components/admin/CostPanel';
import { DocumentUpload }  from '../components/admin/DocumentUpload';
import { Spinner }         from '../components/shared/Spinner';
import { useAuth }         from '../context/AuthContext';

// ── Constants ─────────────────────────────────────────────────────────────────
const EMPTY_STATS: AdminStats = {
  total_queries: 0, avg_confidence: 0, avg_response_time: 0,
  agent_distribution: {}, daily_volume: [],
};
const EMPTY_COST: CostStats = { daily: 0, lifetime: 0 };
type Tab = 'overview' | 'approvals' | 'users' | 'audit' | 'documents';

// ── Small shared components ───────────────────────────────────────────────────
const ROLE_COLORS: Record<string, string> = {
  admin: 'bg-violet-100 text-violet-700',
  user:  'bg-sky-100 text-sky-700',
  viewer:'bg-slate-100 text-slate-600',
};

function RoleBadge({ role }: { role: string }) {
  const cls = ROLE_COLORS[role.toLowerCase()] ?? 'bg-slate-100 text-slate-600';
  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>{role}</span>;
}

function StatusDot({ active }: { active: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${active ? 'text-emerald-600' : 'text-rose-500'}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-emerald-500' : 'bg-rose-400'}`} />
      {active ? 'Active' : 'Inactive'}
    </span>
  );
}

function Pagination({ page, total, pageSize, onChange }: {
  page: number; total: number; pageSize: number; onChange: (p: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="flex items-center justify-between text-xs text-slate-500 pt-3 border-t border-slate-100">
      <span>{total} total</span>
      <div className="flex items-center gap-1">
        <button onClick={() => onChange(page - 1)} disabled={page <= 1}
          className="p-1 rounded hover:bg-slate-100 disabled:opacity-40">
          <ChevronLeft className="w-3.5 h-3.5" />
        </button>
        <span className="px-2">{page} / {totalPages}</span>
        <button onClick={() => onChange(page + 1)} disabled={page >= totalPages}
          className="p-1 rounded hover:bg-slate-100 disabled:opacity-40">
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}

// ── Session-expired banner ────────────────────────────────────────────────────
function SessionExpiredBanner() {
  function signIn() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_role');
    window.location.href = '/login';
  }
  return (
    <div className="mb-6 bg-amber-50 border border-amber-200 rounded-xl px-5 py-4 flex items-start gap-3">
      <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
      <div className="flex-1">
        <p className="text-sm font-semibold text-amber-800">Session expired</p>
        <p className="text-xs text-amber-700 mt-0.5">
          Your session has expired. Please sign in again to view dashboard data.
        </p>
      </div>
      <button onClick={signIn}
        className="flex items-center gap-1.5 text-xs font-medium bg-amber-600 text-white px-3 py-1.5 rounded-lg hover:bg-amber-700 transition-colors shrink-0">
        <LogIn className="w-3.5 h-3.5" /> Sign in
      </button>
    </div>
  );
}

// ── Live System Status panel ──────────────────────────────────────────────────
function SystemStatusPanel() {
  const [health, setHealth]   = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastAt, setLastAt]   = useState<Date | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try { setHealth(await getHealthDeep()); }
    catch { setHealth(null); }
    finally { setLoading(false); setLastAt(new Date()); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const items = [
    { label: 'API Server',   icon: <Server className="w-4 h-4" />,   key: 'status'   },
    { label: 'PostgreSQL',   icon: <Database className="w-4 h-4" />, key: 'postgres' },
    { label: 'Redis',        icon: <Cpu className="w-4 h-4" />,      key: 'redis'    },
    { label: 'ChromaDB RAG', icon: <Activity className="w-4 h-4" />, key: 'chromadb' },
    { label: 'OpenAI',       icon: <Wifi className="w-4 h-4" />,     key: 'openai'   },
  ];

  // Health response: { status, checks: { postgres, redis, chromadb, openai }, ... }
  // Top-level 'status' is for API Server; rest live under health.checks
  function parseStatus(key: string): { ok: boolean; label: string } {
    if (!health) return { ok: false, label: 'unreachable' };
    // 'status' is a top-level field; all others are under health.checks
    const val = key === 'status'
      ? health['status']
      : (health['checks'] as Record<string, unknown> | undefined)?.[key];
    if (val === undefined || val === null) return { ok: false, label: 'offline' };
    if (typeof val === 'string') {
      const v = val.toLowerCase();
      // "ok", "ok (701 documents)", "online", "closed", "available" are all healthy
      const ok = v === 'ok' || v.startsWith('ok ') || v === 'online' || v === 'closed' || v === 'available';
      // Extract doc count from "ok (701 documents)"
      const docMatch = val.match(/\((\d+)\s*documents?\)/i);
      const extra = docMatch ? ` · ${docMatch[1]} docs` : '';
      return { ok, label: ok ? `online${extra}` : val };
    }
    if (typeof val === 'object') {
      const obj = val as Record<string, unknown>;
      const ok  = String(obj.status ?? '').toLowerCase() === 'ok';
      return { ok, label: ok ? 'online' : String(obj.status ?? 'error') };
    }
    return { ok: false, label: 'unknown' };
  }

  return (
    <div className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-700">Live System Status</h3>
        <button onClick={load} disabled={loading} title="Refresh"
          className="text-slate-400 hover:text-slate-700 transition-colors">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>
      <div className="space-y-2.5">
        {items.map((item) => {
          const { ok, label } = parseStatus(item.key);
          return (
            <div key={item.label} className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2 text-slate-600">
                <span className="text-slate-400">{item.icon}</span>
                {item.label}
              </div>
              <div className="flex items-center gap-1.5">
                {loading ? (
                  <span className="w-2 h-2 rounded-full bg-slate-200 animate-pulse" />
                ) : ok ? (
                  <>
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                    </span>
                    <span className="text-xs text-emerald-600 font-medium">{label}</span>
                  </>
                ) : (
                  <>
                    <WifiOff className="w-3 h-3 text-rose-400" />
                    <span className="text-xs text-rose-500 font-medium">{label}</span>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>
      {lastAt && (
        <p className="text-[10px] text-slate-300 mt-3">
          Checked: {lastAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </p>
      )}
    </div>
  );
}

// ── Users Tab ─────────────────────────────────────────────────────────────────
function UsersTab({ onAuthError }: { onAuthError: () => void }) {
  const [users, setUsers]       = useState<AdminUser[]>([]);
  const [total, setTotal]       = useState(0);
  const [page, setPage]         = useState(1);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const [toggling, setToggling] = useState<string | null>(null);
  const PAGE_SIZE = 15;

  const load = useCallback(async (p: number) => {
    setLoading(true); setError(null);
    try {
      const res = await listUsers({ limit: PAGE_SIZE, offset: (p - 1) * PAGE_SIZE });
      setUsers(res.users); setTotal(res.total);
    } catch (err) {
      if (err instanceof AuthError) { onAuthError(); return; }
      setError(err instanceof Error ? err.message : 'Failed to load users.');
    } finally { setLoading(false); }
  }, [onAuthError]);

  useEffect(() => { load(page); }, [page, load]);

  async function toggleActive(u: AdminUser) {
    setToggling(u.id);
    try {
      await updateUser(u.id, { is_active: !u.is_active });
      setUsers((prev) => prev.map((x) => x.id === u.id ? { ...x, is_active: !x.is_active } : x));
    } catch (err) {
      if (err instanceof AuthError) { onAuthError(); return; }
      setError(err instanceof Error ? err.message : 'Update failed.');
    } finally { setToggling(null); }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-slate-800">User Management</h2>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">{total} users</span>
          <button onClick={() => load(page)} disabled={loading}
            className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-rose-50 border border-rose-200 rounded-xl px-4 py-3 text-sm text-rose-700">
          <XCircle className="w-4 h-4 shrink-0" />{error}
          <button onClick={() => load(page)} className="ml-auto underline text-xs">Retry</button>
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Spinner className="w-6 h-6 text-indigo-600" />
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500">Username</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500">Email</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500">Department</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500">Role</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500">Status</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500">Joined</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-slate-800">{u.username}</td>
                  <td className="px-4 py-3 text-slate-500">{u.email ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-500">{u.department ?? '—'}</td>
                  <td className="px-4 py-3"><RoleBadge role={u.role} /></td>
                  <td className="px-4 py-3"><StatusDot active={u.is_active} /></td>
                  <td className="px-4 py-3 text-slate-400 text-xs">
                    {new Date(u.created_at).toLocaleDateString('en-AE')}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => toggleActive(u)} disabled={toggling === u.id}
                      className={`flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg transition-colors ${
                        u.is_active ? 'text-rose-600 hover:bg-rose-50' : 'text-emerald-600 hover:bg-emerald-50'
                      }`}>
                      {toggling === u.id
                        ? <Spinner className="w-3 h-3" />
                        : u.is_active
                          ? <><XCircle className="w-3.5 h-3.5" /> Deactivate</>
                          : <><CheckCircle className="w-3.5 h-3.5" /> Activate</>}
                    </button>
                  </td>
                </tr>
              ))}
              {users.length === 0 && !loading && (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-slate-400 text-sm">
                    No users found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
        <div className="px-4 pb-3">
          <Pagination page={page} total={total} pageSize={PAGE_SIZE} onChange={setPage} />
        </div>
      </div>
    </div>
  );
}

// ── Audit Tab ─────────────────────────────────────────────────────────────────
const EVENT_COLORS: Record<string, string> = {
  LOGIN:'bg-sky-100 text-sky-700', LOGOUT:'bg-slate-100 text-slate-600',
  QUERY:'bg-indigo-100 text-indigo-700', ACTION_CREATED:'bg-amber-100 text-amber-700',
  ACTION_APPROVED:'bg-emerald-100 text-emerald-700', ACTION_REJECTED:'bg-rose-100 text-rose-700',
  PASSWORD_CHANGE:'bg-orange-100 text-orange-700', USER_UPDATED:'bg-violet-100 text-violet-700',
  DOCUMENT_UPLOAD:'bg-teal-100 text-teal-700',
};

function AuditTab({ onAuthError }: { onAuthError: () => void }) {
  const [logs, setLogs]       = useState<AuditLogEntry[]>([]);
  const [total, setTotal]     = useState(0);
  const [page, setPage]       = useState(1);
  const [filter, setFilter]   = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);
  const PAGE_SIZE = 20;

  const load = useCallback(async (p: number, evt: string) => {
    setLoading(true); setError(null);
    try {
      const res = await getAuditLogs({
        limit: PAGE_SIZE, offset: (p - 1) * PAGE_SIZE,
        ...(evt ? { event_type: evt } : {}),
      });
      setLogs(res.logs); setTotal(res.total);
    } catch (err) {
      if (err instanceof AuthError) { onAuthError(); return; }
      setError(err instanceof Error ? err.message : 'Failed to load logs.');
    } finally { setLoading(false); }
  }, [onAuthError]);

  useEffect(() => { load(page, filter); }, [page, filter, load]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-slate-800">Audit Log</h2>
        <div className="flex items-center gap-2">
          <select value={filter} onChange={(e) => { setFilter(e.target.value); setPage(1); }}
            className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-600 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-400">
            <option value="">All Events</option>
            {Object.keys(EVENT_COLORS).map((k) => (
              <option key={k} value={k}>{k.replace(/_/g, ' ')}</option>
            ))}
          </select>
          <button onClick={() => load(page, filter)} disabled={loading}
            className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-rose-50 border border-rose-200 rounded-xl px-4 py-3 text-sm text-rose-700">
          <XCircle className="w-4 h-4 shrink-0" />{error}
          <button onClick={() => load(page, filter)} className="ml-auto underline text-xs">Retry</button>
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Spinner className="w-6 h-6 text-indigo-600" />
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500">Timestamp</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500">Event</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500">User</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3 text-xs text-slate-400 whitespace-nowrap">
                    {new Date(log.created_at).toLocaleString('en-AE')}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${EVENT_COLORS[log.event_type] ?? 'bg-slate-100 text-slate-600'}`}>
                      {log.event_type.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600 text-xs">
                    {log.user_id ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500 max-w-xs truncate">
                    {Object.entries(log.payload ?? {}).map(([k, v]) => `${k}: ${v}`).join(' · ') || '—'}
                  </td>
                </tr>
              ))}
              {logs.length === 0 && !loading && (
                <tr>
                  <td colSpan={4} className="text-center py-12 text-slate-400 text-sm">
                    No audit events found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
        <div className="px-4 pb-3">
          <Pagination page={page} total={total} pageSize={PAGE_SIZE} onChange={setPage} />
        </div>
      </div>
    </div>
  );
}

// ── Main AdminPage ─────────────────────────────────────────────────────────────
export function AdminPage() {
  // ⚠️  ALL hooks must be called unconditionally before any early return.
  //     Violating this (calling hooks after `if (!isAdmin) return`) causes
  //     React to throw "Rendered fewer hooks than expected" when isAdmin flips.
  const { isAdmin }    = useAuth();
  const navigate       = useNavigate();

  const [stats, setStats]           = useState<AdminStats>(EMPTY_STATS);
  const [cost, setCost]             = useState<CostStats>(EMPTY_COST);
  const [actions, setActions]       = useState<Action[]>([]);
  const [loading, setLoading]       = useState(true);
  const [activeTab, setActiveTab]   = useState<Tab>('overview');
  const [sessionExpired, setSessionExpired] = useState(false);
  const [overviewError, setOverviewError]   = useState<string | null>(null);
  const hasLoaded = useRef(false);

  // Stable callback — no deps needed because setSessionExpired is stable
  const handleAuthError = useCallback(() => {
    setSessionExpired(true);
    setLoading(false);
  }, []);

  const fetchCore = useCallback(async () => {
    if (!isAdmin || sessionExpired) return;
    setLoading(true);
    setOverviewError(null);
    try {
      const [sr, cr, ar] = await Promise.allSettled([
        getAdminStats(),
        getCostStats(),
        getPendingActions(),
      ]);
      // Any auth error → show the expired banner
      if ([sr, cr, ar].some((r) => r.status === 'rejected' && r.reason instanceof AuthError)) {
        handleAuthError();
        return;
      }
      setStats(sr.status === 'fulfilled' ? sr.value : EMPTY_STATS);
      setCost(cr.status === 'fulfilled'  ? cr.value : EMPTY_COST);
      setActions(ar.status === 'fulfilled' ? ar.value : []);
      const firstErr = [sr, cr, ar].find((r) => r.status === 'rejected');
      if (firstErr?.status === 'rejected') {
        setOverviewError(`Partial load error: ${firstErr.reason?.message ?? 'Unknown'}`);
      }
    } finally {
      setLoading(false);
    }
  }, [isAdmin, sessionExpired, handleAuthError]);

  // Load once when the page mounts (and isAdmin becomes true)
  useEffect(() => {
    if (isAdmin && !hasLoaded.current) {
      hasLoaded.current = true;
      fetchCore();
    }
  }, [isAdmin, fetchCore]);

  // ── Now safe to do the early return (after all hooks) ──────────────────────
  if (!isAdmin) return <Navigate to="/chat" replace />;

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'overview',  label: 'Overview',  icon: <BarChart2 className="w-3.5 h-3.5" /> },
    { id: 'approvals', label: `Approvals${actions.length > 0 ? ` (${actions.length})` : ''}`,
                                           icon: <CheckCircle className="w-3.5 h-3.5" /> },
    { id: 'users',     label: 'Users',     icon: <Users className="w-3.5 h-3.5" /> },
    { id: 'audit',     label: 'Audit Log', icon: <Shield className="w-3.5 h-3.5" /> },
    { id: 'documents', label: 'Documents', icon: <FileText className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="min-h-screen bg-slate-50 overflow-auto">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="bg-white border-b border-slate-100 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-4">
          <button onClick={() => navigate('/chat')}
            className="flex items-center gap-1.5 text-slate-500 hover:text-slate-800 text-sm transition-colors">
            <ArrowLeft className="w-4 h-4" />Back to Chat
          </button>
          <div className="h-4 w-px bg-slate-200" />
          <h1 className="font-semibold text-slate-800">Admin Dashboard</h1>
          <div className="ml-auto">
            {!sessionExpired && (activeTab === 'overview' || activeTab === 'approvals') && (
              <button onClick={fetchCore} disabled={loading}
                className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors">
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="max-w-7xl mx-auto px-6 flex gap-0.5 overflow-x-auto">
          {tabs.map((tab) => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}>
              {tab.icon}{tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Content ────────────────────────────────────────────────────────── */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        {sessionExpired && <SessionExpiredBanner />}

        {/* Overview */}
        {activeTab === 'overview' && !sessionExpired && (
          loading ? (
            /* Skeleton loading state — matches the real layout so there's no layout shift */
            <div className="space-y-4 animate-pulse">
              {/* Stats cards skeleton */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm">
                    <div className="h-3 w-20 bg-slate-100 rounded mb-4" />
                    <div className="h-7 w-14 bg-slate-200 rounded mb-2" />
                    <div className="h-2 w-24 bg-slate-100 rounded" />
                  </div>
                ))}
              </div>
              {/* Chart skeleton */}
              <div className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm">
                <div className="h-4 w-32 bg-slate-100 rounded mb-4" />
                <div className="h-48 bg-slate-50 rounded-lg" />
              </div>
              {/* Bottom row skeleton */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {[...Array(2)].map((_, i) => (
                  <div key={i} className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm">
                    <div className="h-4 w-28 bg-slate-100 rounded mb-4" />
                    <div className="space-y-3">
                      {[...Array(3)].map((_, j) => (
                        <div key={j} className="h-3 bg-slate-100 rounded" />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {overviewError && (
                <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-700">
                  <AlertTriangle className="w-4 h-4 shrink-0" />{overviewError}
                  <button onClick={fetchCore} className="ml-auto underline text-xs">Retry</button>
                </div>
              )}
              <StatsCards stats={stats} cost={cost} />
              <DepartmentChart stats={stats} />
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <CostPanel cost={cost} />
                <SystemStatusPanel />
              </div>
            </div>
          )
        )}

        {/* Approvals */}
        {activeTab === 'approvals' && !sessionExpired && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-slate-800">Pending Actions</h2>
              <span className="text-xs text-slate-400">{actions.length} pending</span>
            </div>
            <ApprovalQueue actions={actions} onRefresh={fetchCore} />
          </div>
        )}

        {/* Users */}
        {activeTab === 'users' && !sessionExpired && (
          <UsersTab onAuthError={handleAuthError} />
        )}

        {/* Audit */}
        {activeTab === 'audit' && !sessionExpired && (
          <AuditTab onAuthError={handleAuthError} />
        )}

        {/* Documents */}
        {activeTab === 'documents' && !sessionExpired && (
          <div className="max-w-xl space-y-4">
            <div>
              <h2 className="font-semibold text-slate-800">Knowledge Base</h2>
              <p className="text-sm text-slate-500 mt-1">
                Upload PDFs to expand the AI knowledge base. Files are automatically
                chunked and embedded into ChromaDB.
              </p>
            </div>
            <DocumentUpload />
          </div>
        )}
      </div>
    </div>
  );
}
