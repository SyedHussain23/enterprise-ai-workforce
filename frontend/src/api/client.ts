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
} from './types';

const BASE = '/api';

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
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_role');
    window.location.href = '/login';
    throw new Error('Unauthorized');
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

// ── Chat (non-streaming) ──────────────────────────────────────────────────────
export async function ask(sessionId: string, question: string): Promise<WorkflowResponse> {
  return request<WorkflowResponse>('/ask', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, question }),
  });
}

// ── Chat (SSE streaming) ──────────────────────────────────────────────────────
export async function askStream(
  sessionId: string,
  question: string,
  onToken: (token: string) => void,
  onDone: (meta: WorkflowResponse) => void,
  onError: (err: string) => void,
): Promise<void> {
  const res = await fetch(`${BASE}/ask/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify({ session_id: sessionId, question }),
  });

  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    onError((body as { detail?: string }).detail ?? `HTTP ${res.status}`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

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
          if (evt.type === 'token') onToken(evt.content);
          else if (evt.type === 'done') onDone(evt as WorkflowResponse);
          else if (evt.type === 'error') onError(evt.message);
        } catch {
          // ignore malformed lines
        }
      }
    }
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
