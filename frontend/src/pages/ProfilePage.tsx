import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, User, Lock, Save, CheckCircle, AlertCircle } from 'lucide-react';
import {
  getMyProfile,
  updateMyProfile,
  changePassword,
} from '../api/client';
import type { UserProfile } from '../api/types';
import { Spinner } from '../components/shared/Spinner';
import { useRTL } from '../context/RTLContext';

const DEPARTMENTS = ['HR', 'IT', 'Finance', 'Operations', 'Legal', 'Sales', 'Marketing', 'Engineering'];

type AlertState = { type: 'success' | 'error'; message: string } | null;

function Alert({ alert, onDismiss }: { alert: AlertState; onDismiss: () => void }) {
  if (!alert) return null;
  const isSuccess = alert.type === 'success';
  return (
    <div className={`flex items-start gap-2 p-3 rounded-xl text-sm border ${
      isSuccess
        ? 'bg-emerald-50 border-emerald-100 text-emerald-700'
        : 'bg-rose-50 border-rose-100 text-rose-700'
    }`}>
      {isSuccess
        ? <CheckCircle className="w-4 h-4 shrink-0 mt-0.5" />
        : <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
      }
      <span className="flex-1">{alert.message}</span>
      <button onClick={onDismiss} className="opacity-60 hover:opacity-100 text-lg leading-none">×</button>
    </div>
  );
}

// ── Profile details section ───────────────────────────────────────────────────
function ProfileDetails({ profile, onSaved }: { profile: UserProfile; onSaved: (p: UserProfile) => void }) {
  const [email, setEmail]           = useState(profile.email ?? '');
  const [department, setDepartment] = useState(profile.department ?? '');
  const [saving, setSaving]         = useState(false);
  const [alert, setAlert]           = useState<AlertState>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setAlert(null);
    try {
      const updated = await updateMyProfile({
        email:      email || undefined,
        department: department || undefined,
      });
      onSaved(updated);
      setAlert({ type: 'success', message: 'Profile updated successfully.' });
    } catch (err) {
      setAlert({ type: 'error', message: err instanceof Error ? err.message : 'Update failed.' });
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="bg-white rounded-xl border border-slate-100 p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-5">
        <User className="w-4 h-4 text-indigo-600" />
        <h2 className="font-semibold text-slate-800">Profile Details</h2>
      </div>

      <Alert alert={alert} onDismiss={() => setAlert(null)} />

      {/* Read-only fields */}
      <div className="grid grid-cols-2 gap-4 mb-4 mt-4">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Username</label>
          <p className="px-3 py-2 rounded-lg bg-slate-50 text-slate-700 text-sm font-mono">
            {profile.username}
          </p>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Role</label>
          <p className="px-3 py-2 rounded-lg bg-slate-50 text-slate-700 text-sm capitalize">
            {profile.role}
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">
            Email address
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="your@email.com"
            className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">
            Department
          </label>
          <select
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-sm text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
          >
            <option value="">Select department…</option>
            {DEPARTMENTS.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium disabled:opacity-50 transition-colors"
        >
          {saving ? <Spinner className="w-4 h-4 text-white" /> : <Save className="w-4 h-4" />}
          {saving ? 'Saving…' : 'Save changes'}
        </button>
      </form>
    </section>
  );
}

// ── Change password section ───────────────────────────────────────────────────
function ChangePassword() {
  const [current, setCurrent]     = useState('');
  const [next, setNext]           = useState('');
  const [confirm, setConfirm]     = useState('');
  const [saving, setSaving]       = useState(false);
  const [alert, setAlert]         = useState<AlertState>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (next !== confirm) {
      setAlert({ type: 'error', message: 'New passwords do not match.' });
      return;
    }
    if (next.length < 8) {
      setAlert({ type: 'error', message: 'Password must be at least 8 characters.' });
      return;
    }
    setSaving(true);
    setAlert(null);
    try {
      const res = await changePassword({ current_password: current, new_password: next });
      setAlert({ type: 'success', message: res.message ?? 'Password changed successfully.' });
      setCurrent(''); setNext(''); setConfirm('');
    } catch (err) {
      setAlert({ type: 'error', message: err instanceof Error ? err.message : 'Password change failed.' });
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="bg-white rounded-xl border border-slate-100 p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-5">
        <Lock className="w-4 h-4 text-indigo-600" />
        <h2 className="font-semibold text-slate-800">Change Password</h2>
      </div>

      <Alert alert={alert} onDismiss={() => setAlert(null)} />

      <form onSubmit={handleSubmit} className="space-y-4 mt-4">
        {[
          { label: 'Current password',  value: current,  set: setCurrent,  auto: 'current-password' },
          { label: 'New password',      value: next,     set: setNext,     auto: 'new-password' },
          { label: 'Confirm new password', value: confirm, set: setConfirm, auto: 'new-password' },
        ].map(({ label, value, set, auto }) => (
          <div key={label}>
            <label className="block text-xs font-medium text-slate-600 mb-1">{label}</label>
            <input
              type="password"
              value={value}
              onChange={(e) => set(e.target.value)}
              autoComplete={auto}
              required
              className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
              placeholder="••••••••"
            />
          </div>
        ))}

        <button
          type="submit"
          disabled={saving || !current || !next || !confirm}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium disabled:opacity-50 transition-colors"
        >
          {saving ? <Spinner className="w-4 h-4 text-white" /> : <Lock className="w-4 h-4" />}
          {saving ? 'Updating…' : 'Update password'}
        </button>
      </form>
    </section>
  );
}

// ── Main ProfilePage ──────────────────────────────────────────────────────────
export function ProfilePage() {
  const navigate = useNavigate();
  const { isRTL } = useRTL();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  useEffect(() => {
    getMyProfile()
      .then(setProfile)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load profile'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-100 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-6 py-3 flex items-center gap-4">
          <button
            onClick={() => navigate('/chat')}
            className="flex items-center gap-1.5 text-slate-500 hover:text-slate-800 text-sm transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            {isRTL ? 'العودة' : 'Back to Chat'}
          </button>
          <div className="h-4 w-px bg-slate-200" />
          <h1 className="font-semibold text-slate-800">
            {isRTL ? 'الملف الشخصي' : 'My Profile'}
          </h1>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-8">
        {loading && (
          <div className="flex items-center justify-center py-20">
            <Spinner className="w-8 h-8 text-indigo-600" />
          </div>
        )}

        {error && (
          <div className="p-4 rounded-xl bg-rose-50 border border-rose-100 text-sm text-rose-700">
            {error}
          </div>
        )}

        {profile && (
          <div className="space-y-6">
            {/* Account info banner */}
            <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl p-5 text-white">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center text-lg font-bold">
                  {profile.username.slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <p className="font-semibold text-lg">{profile.username}</p>
                  <p className="text-indigo-200 text-sm capitalize">
                    {profile.role} · {profile.department ?? 'No department set'}
                  </p>
                </div>
              </div>
            </div>

            <ProfileDetails profile={profile} onSaved={setProfile} />
            <ChangePassword />
          </div>
        )}
      </div>
    </div>
  );
}
