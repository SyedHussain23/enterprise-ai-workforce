import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Spinner } from '../components/shared/Spinner';
import { Eye, EyeOff, Lock, User, Bot } from 'lucide-react';

export function LoginPage() {
  const { login, isLoading } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername]     = useState('');
  const [password, setPassword]     = useState('');
  const [showPass, setShowPass]     = useState(false);
  const [error, setError]           = useState('');
  const [focusedField, setFocused]  = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    try {
      await login(username, password);
      navigate('/chat');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed. Please check your credentials.');
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 flex items-center justify-center p-4 overflow-auto">
      {/* Decorative grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff06_1px,transparent_1px),linear-gradient(to_bottom,#ffffff06_1px,transparent_1px)] bg-[size:48px_48px] pointer-events-none" />

      {/* Glowing orbs */}
      <div className="absolute top-1/4 left-1/3 w-64 h-64 bg-indigo-600/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/3 w-48 h-48 bg-purple-600/20 rounded-full blur-3xl pointer-events-none" />

      <div className="relative w-full max-w-sm animate-slide-in">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-xl shadow-indigo-900/50 mb-4">
            <Bot className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-1">Enterprise AI</h1>
          <p className="text-slate-400 text-sm">Workforce Assistant Platform</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-2xl shadow-black/40 p-8">
          <h2 className="text-lg font-semibold text-slate-800 mb-6">Sign in to your account</h2>

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            {/* Username */}
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-slate-700 mb-1.5">
                Username
              </label>
              <div className={`relative flex items-center rounded-xl border transition-all ${
                focusedField === 'username'
                  ? 'border-indigo-500 ring-2 ring-indigo-100'
                  : 'border-slate-200'
              }`}>
                <User className="absolute left-3.5 w-4 h-4 text-slate-400" />
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  onFocus={() => setFocused('username')}
                  onBlur={() => setFocused(null)}
                  required
                  autoComplete="username"
                  autoFocus
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-transparent text-slate-800 placeholder-slate-400 focus:outline-none text-sm"
                  placeholder="your.username"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-1.5">
                Password
              </label>
              <div className={`relative flex items-center rounded-xl border transition-all ${
                focusedField === 'password'
                  ? 'border-indigo-500 ring-2 ring-indigo-100'
                  : 'border-slate-200'
              }`}>
                <Lock className="absolute left-3.5 w-4 h-4 text-slate-400" />
                <input
                  id="password"
                  type={showPass ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onFocus={() => setFocused('password')}
                  onBlur={() => setFocused(null)}
                  required
                  autoComplete="current-password"
                  className="w-full pl-10 pr-10 py-2.5 rounded-xl bg-transparent text-slate-800 placeholder-slate-400 focus:outline-none text-sm"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPass((v) => !v)}
                  className="absolute right-3 text-slate-400 hover:text-slate-700 transition-colors"
                  aria-label={showPass ? 'Hide password' : 'Show password'}
                >
                  {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div role="alert" className="p-3 rounded-xl bg-red-50 border border-red-100 text-sm text-red-600 animate-slide-in">
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading || !username.trim() || !password}
              className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-[0.99] disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium text-sm flex items-center justify-center gap-2 transition-all mt-2"
            >
              {isLoading ? (
                <><Spinner className="w-4 h-4 text-white" /> Signing in…</>
              ) : (
                'Sign in'
              )}
            </button>
          </form>

          {/* Demo credentials */}
          <div className="mt-6 p-3.5 rounded-xl bg-slate-50 border border-slate-100">
            <p className="text-xs font-semibold text-slate-500 mb-2">Demo credentials</p>
            <div className="space-y-1">
              <p className="text-xs text-slate-500 flex justify-between">
                <span className="text-slate-400">Admin</span>
                <code className="font-mono text-slate-600 bg-white px-1.5 py-0.5 rounded border border-slate-200 text-[11px]">
                  admin / admin123
                </code>
              </p>
              <p className="text-xs text-slate-500 flex justify-between">
                <span className="text-slate-400">Employee</span>
                <code className="font-mono text-slate-600 bg-white px-1.5 py-0.5 rounded border border-slate-200 text-[11px]">
                  employee1 / emp123
                </code>
              </p>
            </div>
          </div>
        </div>

        <p className="text-center text-xs text-slate-500 mt-6">
          Secured with JWT · Built for UAE/GCC enterprises
        </p>
      </div>
    </div>
  );
}
