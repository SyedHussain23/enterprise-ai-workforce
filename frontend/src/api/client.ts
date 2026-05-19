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
  ConversationsResponse,
  ConversationMessagesResponse,
  RequestsListResponse,
  RequestDetailResponse,
  RequestComment,
  ApprovalsListResponse,
  ApprovalsStats,
  NotificationsResponse,
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

  if (res.status === 401) throw new AuthError();
  if (res.status === 403) throw new Error('Access denied — admin privileges required.');

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

export async function serverLogout(): Promise<void> {
  try {
    await request<void>('/logout', { method: 'POST' });
  } catch {
    // Best-effort — still clear client state on failure
  }
}

export async function extractDocument(
  file: File,
): Promise<{ filename: string; text: string; chars: number; truncated: boolean }> {
  const form = new FormData();
  form.append('file', file);

  const res = await fetch(`${BASE}/ask/extract`, {
    method: 'POST',
    headers: authHeaders(),
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
    m.includes('token expired') ||
    m.includes('token has been revoked')
  );
}

function _clearAuthAndRedirect(): void {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_role');
  window.location.href = '/login';
}

// ── Chat (SSE streaming) — returns cancel function ────────────────────────────
/**
 * Opens an SSE stream to /ask/stream.
 * Returns a `cancel()` function — call it to abort mid-stream (Stop button).
 * The stream is automatically cleaned up on cancel or completion.
 */
export function askStream(
  sessionId: string,
  question: string,
  onToken: (token: string) => void,
  onDone: (meta: WorkflowResponse) => void,
  onError: (err: string) => void,
  onStatus?: (status: string) => void,
): { cancel: () => void; promise: Promise<void> } {
  const controller = new AbortController();

  const promise = (async () => {
    let res: Response;
    try {
      res = await fetch(`${BASE}/ask/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders(),
        },
        body: JSON.stringify({ session_id: sessionId, question }),
        signal: controller.signal,
      });
    } catch (err) {
      if ((err as Error).name === 'AbortError') return; // user cancelled — silent
      onError('Connection failed. Please check your network.');
      return;
    }

    if (res.status === 401 || res.status === 403) {
      _clearAuthAndRedirect();
      return;
    }

    if (!res.ok || !res.body) {
      const body = await res.json().catch(() => ({}));
      const detail = (body as { detail?: string }).detail ?? `HTTP ${res.status}`;
      if (_isAuthError(detail)) { _clearAuthAndRedirect(); return; }
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
                if (_isAuthError(evt.message ?? '')) { _clearAuthAndRedirect(); return; }
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
      if ((streamErr as Error).name === 'AbortError') return; // user cancelled
      onError('Response interrupted. Please try again.');
    }
  })();

  return {
    cancel: () => controller.abort(),
    promise,
  };
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
  // Backend may return plain numbers OR nested dicts {estimated_cost_usd, prompt_tokens, ...}
  const raw = await request<Record<string, unknown>>('/admin/cost');
  const extract = (v: unknown): number => {
    if (typeof v === 'number' && isFinite(v)) return v;
    if (v && typeof v === 'object') {
      const cost = (v as Record<string, unknown>).estimated_cost_usd;
      if (typeof cost === 'number' && isFinite(cost)) return cost;
    }
    return 0;
  };
  return { daily: extract(raw.daily), lifetime: extract(raw.lifetime) };
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
  limit?: number;
  offset?: number;
  department?: string;
  role?: string;
}): Promise<AdminUsersResponse> {
  const qs = new URLSearchParams();
  if (params?.limit  != null) qs.set('limit',      String(params.limit));
  if (params?.offset != null) qs.set('offset',     String(params.offset));
  if (params?.department)     qs.set('department', params.department);
  if (params?.role)           qs.set('role',       params.role);
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
  limit?: number;
  offset?: number;
  event_type?: string;
}): Promise<AuditLogsResponse> {
  const qs = new URLSearchParams();
  if (params?.limit  != null) qs.set('limit',      String(params.limit));
  if (params?.offset != null) qs.set('offset',     String(params.offset));
  if (params?.event_type)     qs.set('event_type', params.event_type);
  return request<AuditLogsResponse>(`/admin/audit?${qs.toString()}`);
}

// ── Conversation history ───────────────────────────────────────────────────────

export async function listConversations(params?: {
  limit?: number;
  offset?: number;
}): Promise<ConversationsResponse> {
  const qs = new URLSearchParams();
  if (params?.limit  != null) qs.set('limit',  String(params.limit));
  if (params?.offset != null) qs.set('offset', String(params.offset));
  return request<ConversationsResponse>(`/conversations?${qs.toString()}`);
}

export async function getConversationMessages(
  sessionId: string,
  limit = 100,
): Promise<ConversationMessagesResponse> {
  return request<ConversationMessagesResponse>(
    `/conversations/${encodeURIComponent(sessionId)}/messages?limit=${limit}`,
  );
}

// ── Request lifecycle ─────────────────────────────────────────────────────────

export async function listMyRequests(params?: {
  limit?: number;
  offset?: number;
  status?: string;
}): Promise<RequestsListResponse> {
  const qs = new URLSearchParams();
  if (params?.limit  != null) qs.set('limit',  String(params.limit));
  if (params?.offset != null) qs.set('offset', String(params.offset));
  if (params?.status)         qs.set('status', params.status);
  return request<RequestsListResponse>(`/requests/mine?${qs.toString()}`);
}

export async function getRequestDetail(id: string): Promise<RequestDetailResponse> {
  return request<RequestDetailResponse>(`/requests/${id}`);
}

export async function addRequestComment(
  id: string,
  body: string,
): Promise<RequestComment> {
  return request<RequestComment>(`/requests/${id}/comments`, {
    method: 'POST',
    body: JSON.stringify({ body }),
  });
}

export async function cancelRequest(
  id: string,
  reason?: string,
): Promise<{ status: string }> {
  return request<{ status: string }>(`/requests/${id}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

// ── Approvals ─────────────────────────────────────────────────────────────────

export async function listPendingApprovals(params?: {
  limit?: number;
  offset?: number;
  department?: string;
}): Promise<ApprovalsListResponse> {
  const qs = new URLSearchParams();
  if (params?.limit  != null) qs.set('limit',  String(params.limit));
  if (params?.offset != null) qs.set('offset', String(params.offset));
  if (params?.department)     qs.set('department', params.department);
  return request<ApprovalsListResponse>(`/approvals/pending?${qs.toString()}`);
}

export async function getApprovalsStats(): Promise<ApprovalsStats> {
  return request<ApprovalsStats>('/approvals/stats');
}

// ── Notifications ─────────────────────────────────────────────────────────────

export async function listNotifications(params?: {
  limit?: number;
  offset?: number;
  unread_only?: boolean;
}): Promise<NotificationsResponse> {
  const qs = new URLSearchParams();
  if (params?.limit       != null) qs.set('limit',       String(params.limit));
  if (params?.offset      != null) qs.set('offset',      String(params.offset));
  if (params?.unread_only != null) qs.set('unread_only', String(params.unread_only));
  return request<NotificationsResponse>(`/notifications?${qs.toString()}`);
}

export async function getUnreadCount(): Promise<{ unread_count: number }> {
  return request<{ unread_count: number }>('/notifications/unread/count');
}

export async function markNotificationRead(id: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/notifications/${id}/read`, { method: 'POST' });
}

export async function markAllNotificationsRead(): Promise<{ marked_read: number }> {
  return request<{ marked_read: number }>('/notifications/read-all', { method: 'POST' });
}
