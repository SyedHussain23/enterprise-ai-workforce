import type {
  LoginRequest,
  LoginResponse,
  WorkflowResponse,
  Action,
  AdminStats,
  CostStats,
  FeedbackRequest,
  ActionApprovalRequest,
  SSEEvent,
  UserProfile,
  UpdateProfileRequest,
  ChangePasswordRequest,
  AdminUsersResponse,
  UpdateUserRequest,
  AuditLogsResponse,
} from './types';

const BASE = '/api';

// ── Typed auth error — lets callers distinguish "expired session" from other errors ──
export class AuthError extends Error {
  constructor(message = 'Session expired. Please log in again.') {
    super(message);
    this.name = 'AuthError';
  }
}

function getToken(): string | null {
  return localStorage.getItem('access_token');
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...(init.headers as Record<string, string> | undefined),
    },
  });

  if (res.status === 401) {
    // Throw a typed AuthError — callers decide whether to redirect or show an error UI.
    // We do NOT auto-redirect here because that fires synchronously before any .catch()
    // handlers can run, causing the admin dashboard to silently kick users back to /login.
    throw new AuthError();
  }

  if (res.status === 403) {
    throw new Error('Access denied — admin privileges required.');
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? `HTTP ${res.status}`);
  }

  return res.json() as Promise<T>;
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export async function login(data: LoginRequest): Promise<LoginResponse> {
  return request<LoginResponse>('/login', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Server-side logout — adds the current token's JTI to the Redis blocklist.
 * The token is invalid server-side immediately, even if the client still holds it.
 * Always call this before clearing localStorage on logout.
 */
export async function serverLogout(): Promise<void> {
  try {
    await request<void>('/logout', { method: 'POST' });
  } catch {
    // Best-effort — if the server is unreachable, we still clear client auth.
    // The token will expire naturally via its `exp` claim.
  }
}

/**
 * Extract text from an uploaded file for inline chat context injection.
 * The extracted text is prepended to the user's question for a single turn.
 * No data is persisted — this is ephemeral extraction only.
 */
export async function extractDocument(
  file: File,
): Promise<{ filename: string; text: string; chars: number; truncated: boolean }> {
  const form = new FormData();
  form.append('file', file);

  const res = await fetch(`${BASE}/ask/extract`, {
    method: 'POST',
    headers: authHeaders(),  // No Content-Type — browser sets multipart boundary
    body: form,
  });

  if (res.status === 401) throw new AuthError();
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Chat (non-streaming) ──────────────────────────────────────────────────────
export async function ask(sessionId: string, question: string): Promise<WorkflowResponse> {
  return request<WorkflowResponse>('/ask', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, question }),
  });
}

// ── Auth helpers ──────────────────────────────────────────────────────────────
function _isAuthError(msg: string): boolean {
  const m = msg.toLowerCase();
  return (
    m.includes('invalid token') ||
    m.includes('unauthorized') ||
    m.includes('no token') ||
    m.includes('not authenticated') ||
    m.includes('credentials') ||
    m.includes('token expired')
  );
}

function _clearAuthAndRedirect(): void {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_role');
  window.location.href = '/login';
}

// ── Chat (SSE streaming) ──────────────────────────────────────────────────────
export async function askStream(
  sessionId: string,
  question: string,
  onToken: (token: string) => void,
  onDone: (meta: WorkflowResponse) => void,
  onError: (err: string) => void,
  onStatus?: (status: string) => void,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/ask/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders(),
      },
      body: JSON.stringify({ session_id: sessionId, question }),
    });
  } catch (networkErr) {
    onError('Connection failed. Please check your network.');
    return;
  }

  // Auth failure at HTTP level — redirect immediately, never show a chat bubble
  if (res.status === 401 || res.status === 403) {
    _clearAuthAndRedirect();
    return;
  }

  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    const detail = (body as { detail?: string }).detail ?? `HTTP ${res.status}`;
    if (_isAuthError(detail)) {
      _clearAuthAndRedirect();
      return;
    }
    onError(detail);
    return;
  }

  const reader  = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const raw = line.slice(6).trim();
          if (!raw || raw === '[DONE]') continue;
          try {
            const evt = JSON.parse(raw) as SSEEvent;
            if (evt.type === 'token') {
              onToken(evt.content);
            } else if (evt.type === 'done') {
              onDone(evt as WorkflowResponse);
            } else if (evt.type === 'error') {
              // Auth errors in SSE → redirect; others → surface to UI
              if (_isAuthError(evt.message ?? '')) {
                _clearAuthAndRedirect();
                return;
              }
              onError(evt.message ?? 'An error occurred.');
            } else if (evt.type === 'status' && onStatus) {
              onStatus(evt.content);
            }
          } catch {
            // ignore malformed SSE lines
          }
        }
      }
    }
  } catch (streamErr) {
    // Stream dropped mid-response — surface a clean message, not a raw error
    onError('Response interrupted. Please try again.');
  }
}

// ── Feedback ──────────────────────────────────────────────────────────────────
export async function submitFeedback(data: FeedbackRequest): Promise<void> {
  await request('/feedback', { method: 'POST', body: JSON.stringify(data) });
}

// ── Actions ───────────────────────────────────────────────────────────────────
export async function getPendingActions(): Promise<Action[]> {
  return request<Action[]>('/actions/pending');
}

export async function getMyActions(): Promise<Action[]> {
  return request<Action[]>('/actions/mine');
}

export async function approveAction(id: string, data: ActionApprovalRequest): Promise<Action> {
  return request<Action>(`/actions/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function rejectAction(id: string, data: ActionApprovalRequest): Promise<Action> {
  return request<Action>(`/actions/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ── Admin / Analytics ─────────────────────────────────────────────────────────
export async function getAdminStats(): Promise<AdminStats> {
  return request<AdminStats>('/admin/stats');
}

export async function getCostStats(): Promise<CostStats> {
  return request<CostStats>('/admin/cost');
}

// ── Document Upload ───────────────────────────────────────────────────────────
export async function uploadDocument(file: File): Promise<{ message: string; chunks: number }> {
  const form = new FormData();
  form.append('file', file);

  const res = await fetch(`${BASE}/admin/documents`, {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? `HTTP ${res.status}`);
  }

  return res.json();
}

// ── My Profile ────────────────────────────────────────────────────────────────
export async function getMyProfile(): Promise<UserProfile> {
  return request<UserProfile>('/me');
}

export async function updateMyProfile(data: UpdateProfileRequest): Promise<UserProfile> {
  return request<UserProfile>('/me', { method: 'PUT', body: JSON.stringify(data) });
}

export async function changePassword(data: ChangePasswordRequest): Promise<{ message: string }> {
  return request<{ message: string }>('/me/password', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// ── Admin — Users ─────────────────────────────────────────────────────────────
export async function listUsers(params?: {
  page?: number;
  page_size?: number;
  department?: string;
  role?: string;
}): Promise<AdminUsersResponse> {
  const qs = new URLSearchParams();
  if (params?.page)        qs.set('page',       String(params.page));
  if (params?.page_size)   qs.set('page_size',  String(params.page_size));
  if (params?.department)  qs.set('department', params.department);
  if (params?.role)        qs.set('role',       params.role);
  return request<AdminUsersResponse>(`/admin/users?${qs.toString()}`);
}

export async function updateUser(userId: string, data: UpdateUserRequest): Promise<{ message: string }> {
  return request<{ message: string }>(`/admin/users/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

// ── System Health ─────────────────────────────────────────────────────────────
export async function getHealthDeep(): Promise<Record<string, unknown>> {
  const res = await fetch(`${BASE}/health/deep`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── Admin — Audit Log ─────────────────────────────────────────────────────────
export async function getAuditLogs(params?: {
  page?: number;
  page_size?: number;
  event_type?: string;
}): Promise<AuditLogsResponse> {
  const qs = new URLSearchParams();
  if (params?.page)        qs.set('page',       String(params.page));
  if (params?.page_size)   qs.set('page_size',  String(params.page_size));
  if (params?.event_type)  qs.set('event_type', params.event_type);
  return request<AuditLogsResponse>(`/admin/audit?${qs.toString()}`);
}
