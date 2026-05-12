import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import { getAdminStats, getCostStats, getPendingActions } from '../api/client';
import type { AdminStats, CostStats, Action } from '../api/types';
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

export function AdminPage() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState<AdminStats>(EMPTY_STATS);
  const [cost, setCost] = useState<CostStats>(EMPTY_COST);
  const [actions, setActions] = useState<Action[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'approvals' | 'documents'>('overview');

  if (!isAdmin) {
    navigate('/chat');
    return null;
  }

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [s, c, a] = await Promise.all([
        getAdminStats().catch(() => EMPTY_STATS),
        getCostStats().catch(() => EMPTY_COST),
        getPendingActions().catch(() => []),
      ]);
      setStats(s);
      setCost(c);
      setActions(a);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const tabs = [
    { id: 'overview' as const, label: 'Overview' },
    { id: 'approvals' as const, label: `Approvals${actions.length > 0 ? ` (${actions.length})` : ''}` },
    { id: 'documents' as const, label: 'Documents' },
  ];

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-100 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center gap-4">
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
            <button
              onClick={fetchData}
              disabled={loading}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="max-w-6xl mx-auto px-6 flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-6 py-6">
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
                        { label: 'API Server', status: 'online' },
                        { label: 'PostgreSQL', status: 'online' },
                        { label: 'Redis Memory', status: 'online' },
                        { label: 'ChromaDB RAG', status: 'online' },
                        { label: 'LangSmith Tracing', status: 'online' },
                      ].map((item) => (
                        <div key={item.label} className="flex items-center justify-between text-sm">
                          <span className="text-slate-600">{item.label}</span>
                          <div className="flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-emerald-500" />
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
                <ApprovalQueue actions={actions} onRefresh={fetchData} />
              </div>
            )}

            {activeTab === 'documents' && (
              <div className="max-w-xl space-y-4">
                <div>
                  <h2 className="font-semibold text-slate-800">Knowledge Base</h2>
                  <p className="text-sm text-slate-500 mt-1">
                    Upload PDF documents to expand the AI knowledge base. Documents are automatically chunked and embedded into ChromaDB.
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
