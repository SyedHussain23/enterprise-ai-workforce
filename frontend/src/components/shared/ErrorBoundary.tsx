/**
 * Global React Error Boundary
 *
 * WHY THIS EXISTS:
 *   React 18+ does not catch errors in async event handlers or Promise rejections
 *   automatically, but it DOES catch errors that occur during rendering. Without
 *   a boundary, any render error in any component crashes the entire React tree
 *   and the user sees a white screen with zero recovery path.
 *
 * HOW IT WORKS:
 *   React's getDerivedStateFromError lifecycle method catches errors during
 *   the render phase of any descendant component. The fallback UI is shown
 *   instead of the crashed subtree. The user can reload to recover.
 *
 * USAGE:
 *   Wrap the root <App> in main.tsx (already done).
 *   Can also be used for route-level boundaries to scope the crash surface.
 *
 * PRODUCTION NOTE:
 *   componentDidCatch is the correct place to send errors to Sentry/Datadog.
 *   Add your reporting SDK here when you integrate error monitoring.
 */
import { Component, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  /** Custom fallback UI. If omitted, the default full-screen fallback is shown. */
  fallback?: ReactNode;
  /** Optional: scope label for logging ("ChatPage", "AdminPage", etc.) */
  scope?: string;
}

interface State {
  hasError:   boolean;
  error:      Error | null;
  errorInfo:  string;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null, errorInfo: '' };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: '' };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    const scope = this.props.scope ?? 'root';
    // ── Send to error monitoring here (Sentry, Datadog, etc.) ────────────────
    // Sentry.captureException(error, { extra: { componentStack: info.componentStack, scope } });
    // ─────────────────────────────────────────────────────────────────────────
    console.error(`[ErrorBoundary:${scope}]`, error.message, info.componentStack);
    this.setState({ errorInfo: info.componentStack });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: '' });
  };

  render() {
    if (!this.state.hasError) return this.props.children;
    if (this.props.fallback) return this.props.fallback;

    // ── Default full-screen fallback UI ───────────────────────────────────────
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border border-slate-100 p-8 text-center">
          <div className="w-14 h-14 rounded-full bg-rose-50 flex items-center justify-center mx-auto mb-4">
            <AlertTriangle className="w-7 h-7 text-rose-500" />
          </div>
          <h1 className="text-lg font-semibold text-slate-800 mb-2">
            Something went wrong
          </h1>
          <p className="text-sm text-slate-500 mb-6">
            The application encountered an unexpected error. Your data is safe —
            reload the page to continue.
          </p>

          {/* Error detail — always shown to diagnose production crash */}
          {this.state.error && (
            <details className="text-left mb-6 bg-slate-50 rounded-lg p-3 cursor-pointer">
              <summary className="text-xs font-mono text-rose-600 select-none">
                {this.state.error.message}
              </summary>
              <pre className="text-[10px] text-slate-500 mt-2 overflow-auto max-h-40 whitespace-pre-wrap">
                {this.state.errorInfo}
              </pre>
            </details>
          )}

          <div className="flex gap-3 justify-center">
            <button
              onClick={this.handleReset}
              className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
            >
              Try again
            </button>
            <button
              onClick={this.handleReload}
              className="px-4 py-2 text-sm text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors flex items-center gap-2"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Reload page
            </button>
          </div>
        </div>
      </div>
    );
  }
}
