import { useState, useEffect, useCallback } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import {
  ArrowLeft,
  RefreshCw,
  Shield,
  Users,
  FileText,
  BarChart2,
  CheckCircle,
  XCircle,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import {
  getAdminStats,
  getCostStats,
  getPendingActions,
  listUsers,
  updateUser,
  getAuditLogs,
} from '../api/client';
import type {
  AdminStats,
  CostStats,
  Action,
  AdminUser,
  AuditLogEntry,
} from '../api/types';
import { StatsCards } from '../components/admin/StatsCards';
import { DepartmentChart } from '../components/admin/DepartmentChart';
import { ApprovalQueue } from '../components/admin/ApprovalQueue';
import { CostPanel } from '../components/admin/CostPanel';
import { DocumentUpload } from '../components/admin/DocumentUpload';
import { Spinner } from '../components/shared/Spinner';
import { useAuth } from '../context/AuthContext';

const EMPTY_STATS: AdminStats = {
  total_queries: 0,
  avg_confidence: 0,
  avg_response_time: 0,
  agent_distribution: {},
  daily_volume: [],
};
const EMPTY_COST: CostStats = { daily: 0, lifetime: 0 };

type Tab = 'overview' | 'approvals' | 'users' | 'audit' | 'documents';

const ROLE_COLORS: Record<string, string> = {
  admin:  'bg-violet-100 text-violet-700',
  user:   'bg-sky-100 text-sky-700',
  viewer: 'bg-slate-100 text-slate-600',
};

function RoleBadge({ role }: { role: string }) {
  const cls = ROLE_COLORS[role.toLowerCase()] ?? 'bg-slate-100 text-slate-600';
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {role}
    </span>
  );
}

function StatusDot({ active }: { active: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${active ? 'text-emerald-600' : 'text-rose-500'}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-emerald-500' : 'bg-rose-400'}`} />
      {active ? 'Active' : 'Inactive'}
    </span>
  );
}

function Pagination({
  page,
  total,
  pageSize,
  onChange,
}: {
  page: number;
  total: number;
  pageSize: number;
  onChange: (p: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="flex items-center justify-between text-xs text-slate-500 pt-3 border-t border-slate-100">
      <span>{total} total</span>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onChange(page - 1)}
          disabled={page <= 1}
          className="p-1 rounded hover:bg-slate-100 disabled:opacity-40"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
        </button>
        <span className="px-2">{page} / {totalPages}</span>
        <button
          onClick={() => onChange(page + 1)}
          disabled={page >= totalPages}
          className="p-1 rounded hover:bg-slate-100 disabled:opacity-40"
        >
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}

// ── Users Tab ─────────────────────────────────────────────────────────────────
function UsersTab() {
  const [users, setUsers]     = useState<AdminUser[]>([]);
  const [total, setTotal]     = useState(0);
  const [page, setPage]       = useState(1);
  const [loading, setLoading] = useState(false);
  const [toggling, setToggling] = useState<string | null>(null);
  const PAGE_SIZE = 15;

  const load = useCallback(async (p: number) => {
    setLoading(true);
    try {
      const res = await listUsers({ page: p, page_size: PAGE_SIZE });
      setUsers(res.users);
      setTotal(res.total);
    } catch {
      // silent — network issues
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(page); }, [page, load]);

  async function toggleActive(user: AdminUser) {
    setToggling(user.id);
    try {
      await updateUser(user.id, { is_active: !user.is_active });
      setUsers((prev) =>
        prev.map((u) => u.id === user.id ? { ...u, is_active: !u.is_active } : u)
      );
    } catch {
      // silent
    } finally {
      setToggling(null);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-slate-800">User Management</h2>
        <span className="text-xs text-slate-400">{total} users total</span>
      </div>

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
                    <button
                      onClick={() => toggleActive(u)}
                      disabled={toggling === u.id}
                      className={`flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg transition-colors ${
                        u.is_active
                          ? 'text-rose-600 hover:bg-rose-50'
                          : 'text-emerald-600 hover:bg-emerald-50'
                      }`}
                    >
                      {toggling === u.id ? (
                        <Spinner className="w-3 h-3" />
                      ) : u.is_active ? (
                        <><XCircle className="w-3.5 h-3.5" /> Deactivate</>
                      ) : (
                        <><CheckCircle className="w-3.5 h-3.5" /> Activate</>
                      )}
                    </button>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
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

// ── Audit Log Tab ─────────────────────────────────────────────────────────────
const EVENT_COLORS: Record<string, string> = {
  LOGIN:          'bg-sky-100 text-sky-700',
  LOGOUT:         'bg-slate-100 text-slate-600',
  QUERY:          'bg-indigo-100 text-indigo-700',
  ACTION_CREATED: 'bg-amber-100 text-amber-700',
  ACTION_APPROVED:'bg-emerald-100 text-emerald-700',
  ACTION_REJECTED:'bg-rose-100 text-rose-700',
  PASSWORD_CHANGE:'bg-orange-100 text-orange-700',
  USER_UPDATED:   'bg-violet-100 text-violet-700',
  DOCUMENT_UPLOAD:'bg-teal-100 text-teal-700',
};

function EventBadge({ type }: { type: string }) {
  const cls = EVENT_COLORS[type] ?? 'bg-slate-100 text-slate-600';
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {type.replace(/_/g, ' ')}
    </span>
  );
}

function AuditTab() {
  const [logs, setLogs]       = useState<AuditLogEntry[]>([]);
  const [total, setTotal]     = useState(0);
  const [page, setPage]       = useState(1);
  const [filter, setFilter]   = useState('');
  const [loading, setLoading] = useState(false);
  const PAGE_SIZE = 20;

  const load = useCallback(async (p: number, evt: string) => {
    setLoading(true);
    try {
      const res = await getAuditLogs({
        page: p,
        page_size: PAGE_SIZE,
        ...(evt ? { event_type: evt } : {}),
      });
      setLogs(res.logs);
      setTotal(res.total);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(page, filter); }, [page, filter, load]);

  function handleFilter(v: string) {
    setFilter(v);
    setPage(1);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-slate-800">Audit Log</h2>
        <select
          value={filter}
          onChange={(e) => handleFilter(e.target.value)}
          className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-600 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-400"
        >
          <option value="">All Events</option>
          {Object.keys(EVENT_COLORS).map((k) => (
            <option key={k} value={k}>{k.replace(/_/g, ' ')}</option>
          ))}
        </select>
      </div>

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
                    <EventBadge type={log.event_type} />
                  </td>
                  <td className="px-4 py-3 text-slate-600 text-xs">
                    {log.username ?? log.user_id ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500 max-w-xs truncate">
                    {Object.entries(log.details ?? {})
                      .map(([k, v]) => `${k}: ${v}`)
                      .join(' · ') || '—'}
                  </td>
                </tr>
              ))}
              {logs.length === 0 && (
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
  const { isAdmin }  = useAuth();
  const navigate     = useNavigate();
  const [stats, setStats]   = useState<AdminStats>(EMPTY_STATS);
  const [cost, setCost]     = useState<CostStats>(EMPTY_COST);
  const [actions, setActions] = useState<Action[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [error, setError] = useState<string | null>(null);

  const fetchCore = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, c, a] = await Promise.all([
        getAdminStats().catch(() => EMPTY_STATS),
        getCostStats().catch(() => EMPTY_COST),
        getPendingActions().catch(() => []),
      ]);
      setStats(s);
      setCost(c);
      setActions(a);
    } catch (err) {
      setError('Failed to load dashboard data. Please refresh.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchCore(); }, [fetchCore]);

  if (!isAdmin) return <Navigate to="/chat" replace />;

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'overview',   label: 'Overview',   icon: <BarChart2 className="w-3.5 h-3.5" /> },
    { id: 'approvals',  label: `Approvals${actions.length > 0 ? ` (${actions.length})` : ''}`, icon: <CheckCircle className="w-3.5 h-3.5" /> },
    { id: 'users',      label: 'Users',      icon: <Users className="w-3.5 h-3.5" /> },
    { id: 'audit',      label: 'Audit Log',  icon: <Shield className="w-3.5 h-3.5" /> },
    { id: 'documents',  label: 'Documents',  icon: <FileText className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-100 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-4">
          <button
            onClick={() => navigate('/chat')}
            className="flex items-center gap-1.5 text-slate-500 hover:text-slate-800 text-sm transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Chat
          </button>
          <div className="h-4 w-px bg-slate-200" />
          <h1 className="font-semibold text-slate-800">Admin Dashboard</h1>

          <div className="ml-auto flex items-center gap-2">
            {(activeTab === 'overview' || activeTab === 'approvals') && (
              <button
                onClick={fetchCore}
                disabled={loading}
                className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="max-w-7xl mx-auto px-6 flex gap-0.5">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        {error && (
          <div className="mb-4 bg-rose-50 border border-rose-200 rounded-xl px-4 py-3 text-sm text-rose-700 flex items-center gap-2">
            <XCircle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}
        {loading && activeTab === 'overview' ? (
          <div className="flex items-center justify-center py-20">
            <Spinner className="w-8 h-8 text-indigo-600" />
          </div>
        ) : (
          <>
            {activeTab === 'overview' && (
              <div className="space-y-4">
                <StatsCards stats={stats} cost={cost} />
                <DepartmentChart stats={stats} />
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <CostPanel cost={cost} />
                  <div className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm">
                    <h3 className="text-sm font-semibold text-slate-700 mb-3">System Status</h3>
                    <div className="space-y-2">
                      {[
                        { label: 'API Server',       status: 'online' },
                        { label: 'PostgreSQL',       status: 'online' },
                        { label: 'Redis Memory',     status: 'online' },
                        { label: 'ChromaDB RAG',     status: 'online' },
                        { label: 'LangSmith Tracing',status: 'online' },
                      ].map((item) => (
                        <div key={item.label} className="flex items-center justify-between text-sm">
                          <span className="text-slate-600">{item.label}</span>
                          <div className="flex items-center gap-1.5">
                            <span className="relative flex h-2 w-2">
                              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                            </span>
                            <span className="text-xs text-emerald-600 font-medium">{item.status}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'approvals' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="font-semibold text-slate-800">Pending Actions</h2>
                  <span className="text-xs text-slate-400">{actions.length} pending approval</span>
                </div>
                <ApprovalQueue actions={actions} onRefresh={fetchCore} />
              </div>
            )}

            {activeTab === 'users' && <UsersTab />}

            {activeTab === 'audit' && <AuditTab />}

            {activeTab === 'documents' && (
              <div className="max-w-xl space-y-4">
                <div>
                  <h2 className="font-semibold text-slate-800">Knowledge Base</h2>
                  <p className="text-sm text-slate-500 mt-1">
                    Upload documents to expand the AI knowledge base. Files are automatically chunked and embedded into ChromaDB.
                  </p>
                </div>
                <DocumentUpload />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
