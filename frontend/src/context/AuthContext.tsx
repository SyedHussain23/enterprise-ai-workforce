import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { login as apiLogin } from '../api/client';

interface AuthState {
  token: string | null;
  role: string | null;
  isAdmin: boolean;
  isLoading: boolean;
}

interface AuthContextType extends AuthState {
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

// ── JWT expiry check (client-side, no library needed) ─────────────────────────
// JWT = header.payload.signature — payload is base64url-encoded JSON.
// We decode it to check the `exp` field (Unix timestamp in seconds).
// This is purely a UX guard; the server always re-validates the signature.
function isTokenExpired(token: string): boolean {
  try {
    const payloadB64 = token.split('.')[1];
    if (!payloadB64) return true;
    // base64url → base64 → JSON
    const padded  = payloadB64.replace(/-/g, '+').replace(/_/g, '/');
    const payload = JSON.parse(atob(padded));
    const exp: number | undefined = payload.exp;
    if (!exp) return false; // no expiry claim — treat as valid
    // Add a 30-second buffer so we redirect before the server rejects it
    return Date.now() / 1000 > exp - 30;
  } catch {
    return true; // malformed token → treat as expired
  }
}

function clearAuth(): void {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_role');
}

function getValidToken(): { token: string; role: string } | null {
  const token = localStorage.getItem('access_token');
  const role  = localStorage.getItem('user_role');
  if (!token || !role) return null;
  if (isTokenExpired(token)) {
    clearAuth();
    return null;
  }
  return { token, role };
}

// ── Provider ──────────────────────────────────────────────────────────────────
export function AuthProvider({ children }: { children: ReactNode }) {
  const initial = getValidToken();
  const [state, setState] = useState<AuthState>({
    token:    initial?.token  ?? null,
    role:     initial?.role   ?? null,
    isAdmin:  initial?.role   === 'admin',
    isLoading: false,
  });

  // Re-check expiry on mount (handles browser tab restored after a long idle)
  useEffect(() => {
    const valid = getValidToken();
    if (!valid && localStorage.getItem('access_token')) {
      // Token was in storage but is expired — clear and reset state.
      // ProtectedRoute will redirect to /login on next render.
      setState({ token: null, role: null, isAdmin: false, isLoading: false });
    }
  }, []);

  // Periodic expiry check: every 60s, re-validate the stored token.
  // Catches the edge case where the user leaves a tab open across the 8h window.
  useEffect(() => {
    const interval = setInterval(() => {
      const token = localStorage.getItem('access_token');
      if (token && isTokenExpired(token)) {
        clearAuth();
        setState({ token: null, role: null, isAdmin: false, isLoading: false });
        // Navigate to login — ProtectedRoute will redirect on next state change
        window.location.href = '/login';
      }
    }, 60_000);  // every 60 seconds
    return () => clearInterval(interval);
  }, []);

  async function login(username: string, password: string) {
    setState((s) => ({ ...s, isLoading: true }));
    try {
      const res = await apiLogin({ username, password });
      localStorage.setItem('access_token', res.access_token);
      localStorage.setItem('user_role', res.role);
      setState({
        token:    res.access_token,
        role:     res.role,
        isAdmin:  res.role === 'admin',
        isLoading: false,
      });
    } catch (err) {
      setState((s) => ({ ...s, isLoading: false }));
      throw err;
    }
  }

  function logout() {
    clearAuth();
    setState({ token: null, role: null, isAdmin: false, isLoading: false });
  }

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
