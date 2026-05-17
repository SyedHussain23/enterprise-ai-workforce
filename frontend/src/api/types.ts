export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: string;
}

export interface WorkflowResponse {
  status: string;
  answer: string;
  agent: string;
  confidence: number;
  source: string;
  steps: string[];
  confidence_reason?: string;
  evaluation_score?: number;
  response_time: number;
  timestamp: string;
  action_id?: string;
  action_type?: string;
  action_status?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
  metadata?: WorkflowResponse;
  timestamp: string;
}

export interface Session {
  id: string;
  title: string;
  createdAt: string;
  lastMessage?: string;
}

export interface Action {
  id: string;
  action_type: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'COMPLETED';
  payload: Record<string, unknown>;
  created_at: string;
  notes?: string;
  requested_by?: string;
}

export interface AdminStats {
  total_queries: number;
  avg_confidence: number;
  avg_response_time: number;
  agent_distribution: Record<string, number>;
  daily_volume: Array<{ date: string; count: number }>;
}

export interface CostStats {
  daily: number;
  lifetime: number;
}

export interface FeedbackRequest {
  workflow_log_id: string;
  rating: number;
  comment?: string;
}

export interface ActionApprovalRequest {
  notes?: string;
}

export type SSETokenEvent  = { type: 'token';  content: string };
export type SSEStatusEvent = { type: 'status'; content: string };
export type SSEDoneEvent   = { type: 'done' } & WorkflowResponse;
export type SSEErrorEvent  = { type: 'error'; message: string };
export type SSEEvent = SSETokenEvent | SSEStatusEvent | SSEDoneEvent | SSEErrorEvent;

// ── User Profile ──────────────────────────────────────────────────────────────
export interface UserProfile {
  id: string;
  username: string;
  email: string | null;
  role: string;
  department: string | null;
  is_active: boolean;
  created_at: string;
}

export interface UpdateProfileRequest {
  email?: string;
  department?: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

// ── Admin — Users ─────────────────────────────────────────────────────────────
export interface AdminUser {
  id: string;
  username: string;
  email: string | null;
  role: string;
  department: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AdminUsersResponse {
  users: AdminUser[];
  total: number;
  page: number;
  page_size: number;
}

export interface UpdateUserRequest {
  role?: string;
  is_active?: boolean;
  department?: string;
}

// ── Admin — Audit Log ─────────────────────────────────────────────────────────
export interface AuditLogEntry {
  id: string;
  event_type: string;
  user_id: string | null;
  username: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface AuditLogsResponse {
  logs: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
}
