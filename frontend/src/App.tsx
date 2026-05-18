import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { RTLProvider } from './context/RTLContext';
import type { ReactNode } from 'react';
import { Spinner } from './components/shared/Spinner';

// ── Route-level code splitting ────────────────────────────────────────────────
// ChatPage is eagerly loaded — it's the main screen (fast first paint).
// AdminPage and ProfilePage are lazy — infrequently visited, save ~40KB on initial load.
import { ChatPage } from './pages/ChatPage';
const AdminPage   = lazy(() => import('./pages/AdminPage').then((m) => ({ default: m.AdminPage })));
const LoginPage   = lazy(() => import('./pages/LoginPage').then((m) => ({ default: m.LoginPage })));
const ProfilePage = lazy(() => import('./pages/ProfilePage').then((m) => ({ default: m.ProfilePage })));

// ── Route suspense fallback ───────────────────────────────────────────────────
function PageLoader() {
  return (
    <div className="flex items-center justify-center h-full min-h-screen bg-slate-50">
      <Spinner className="w-8 h-8 text-indigo-600" />
    </div>
  );
}

// ── Route guards ──────────────────────────────────────────────────────────────
function ProtectedRoute({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  return token ? <>{children}</> : <Navigate to="/login" replace />;
}

function PublicRoute({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  return token ? <Navigate to="/chat" replace /> : <>{children}</>;
}

function AdminRoute({ children }: { children: ReactNode }) {
  const { token, isAdmin } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  if (!isAdmin) return <Navigate to="/chat" replace />;
  return <>{children}</>;
}

// ── Routes ────────────────────────────────────────────────────────────────────
function AppRoutes() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route
          path="/login"
          element={<PublicRoute><LoginPage /></PublicRoute>}
        />
        <Route
          path="/chat"
          element={<ProtectedRoute><ChatPage /></ProtectedRoute>}
        />
        <Route
          path="/admin"
          element={<AdminRoute><AdminPage /></AdminRoute>}
        />
        <Route
          path="/profile"
          element={<ProtectedRoute><ProfilePage /></ProtectedRoute>}
        />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Routes>
    </Suspense>
  );
}

// ── Root ──────────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <RTLProvider>
          <AppRoutes />
        </RTLProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
