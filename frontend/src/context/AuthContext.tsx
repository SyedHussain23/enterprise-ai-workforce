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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    token: localStorage.getItem('access_token'),
    role: localStorage.getItem('user_role'),
    isAdmin: localStorage.getItem('user_role') === 'admin',
    isLoading: false,
  });

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const role = localStorage.getItem('user_role');
    setState({ token, role, isAdmin: role === 'admin', isLoading: false });
  }, []);

  async function login(username: string, password: string) {
    setState((s) => ({ ...s, isLoading: true }));
    try {
      const res = await apiLogin({ username, password });
      localStorage.setItem('access_token', res.access_token);
      localStorage.setItem('user_role', res.role);
      setState({ token: res.access_token, role: res.role, isAdmin: res.role === 'admin', isLoading: false });
    } catch (err) {
      setState((s) => ({ ...s, isLoading: false }));
      throw err;
    }
  }

  function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_role');
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
