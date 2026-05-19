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
  agent?: string;
  confidence?: number;
  source?: string;
  steps?: string[];
  confidence_reason?: string;
  evaluation_score?: number;
  response_time?: number;
  timestamp?: string;
  action_id?: string;
  action_type?: string;
  action_status?: string;
  /** Real database WorkflowLog UUID — use this for feedback submission. */
  workflow_log_id?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
  /** true when the message represents a failed AI response — shows retry UI */
  isError?: boolean;
  metadata?: WorkflowResponse;
  timestamp: string;
  /** file attachment name for display */
  attachmentName?: string;
}

export interface Session {
  id: string;
  title: string;
  createdAt: string;
  lastMessage?: string;
  /** ISO timestamp — pinned conversations float to top */
  pinnedAt?: string;
  /** message count for display */
  messageCount?: number;
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
  avg_confidence: number | null;
  avg_response_time: number | null;
  agent_distribution: Record<string, number> | null;
  daily_volume: Array<{ date: string; count: number }> | null;
}

export interface CostStats {
  daily: number | null;
  lifetime: number | null;
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
  limit: number;
  offset: number;
}

export interface UpdateUserRequest {
  role?: string;
  is_active?: boolean;
  department?: string;
}

// ── Conversation history ───────────────────────────────────────────────────────
export interface ConversationSummary {
  session_id: string;
  title: string | null;
  department: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationsResponse {
  conversations: ConversationSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface ServerMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  agent: string | null;
  confidence: number | null;
  source: string | null;
  response_time: number | null;
  evaluation_score: number | null;
  created_at: string;
}

export interface ConversationMessagesResponse {
  session_id: string;
  messages: ServerMessage[];
}

// ── Admin — Audit Log ─────────────────────────────────────────────────────────
export interface AuditLogEntry {
  id: string;
  event_type: string;
  user_id: string | null;
  entity_type: string | null;
  entity_id: string | null;
  ip_address: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface AuditLogsResponse {
  logs: AuditLogEntry[];
  total: number;
  limit: number;
  offset: number;
}

// ── Request lifecycle ──────────────────────────────────────────────────────────
export type RequestStatus =
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface RequestSummary {
  id: string;
  action_type: string;
  department: string;
  status: RequestStatus | string;
  requires_approval: boolean;
  payload: Record<string, unknown>;
  notes: string | null;
  requested_by: string | null;
  created_at: string;
  approved_at: string | null;
}

export interface RequestsListResponse {
  total: number;
  limit: number;
  offset: number;
  requests: RequestSummary[];
}

export interface RequestComment {
  id: string;
  body: string;
  author: string | null;
  created_at: string;
}

export interface RequestTimelineEntry {
  id: string;
  event_type: string;
  payload: Record<string, unknown> | null;
  created_at: string;
}

export interface RequestDetailResponse {
  request: RequestSummary;
  comments: RequestComment[];
  timeline: RequestTimelineEntry[];
}

// ── Approvals ──────────────────────────────────────────────────────────────────
export interface ApprovalsListResponse {
  total: number;
  limit: number;
  offset: number;
  items: RequestSummary[];
}

export interface ApprovalsStats {
  pending: number;
}

// ── Notifications ──────────────────────────────────────────────────────────────
export type NotificationKind =
  | 'request_submitted'
  | 'request_approved'
  | 'request_rejected'
  | 'request_commented'
  | 'request_completed'
  | 'request_escalated'
  | 'system';

export interface NotificationItem {
  id: string;
  kind: NotificationKind | string;
  title: string;
  message: string;
  entity_type: string | null;
  entity_id: string | null;
  payload: Record<string, unknown> | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface NotificationsResponse {
  unread_count: number;
  limit: number;
  offset: number;
  notifications: NotificationItem[];
}
