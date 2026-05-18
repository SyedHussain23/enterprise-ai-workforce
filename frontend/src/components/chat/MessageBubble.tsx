import { useState, useCallback } from 'react';
import { ThumbsUp, ThumbsDown, Copy, Check, RefreshCw, Clock, CheckCircle, XCircle, Zap } from 'lucide-react';
import type { Message } from '../../api/types';
import { AgentTrace } from './AgentTrace';
import { submitFeedback, getMyActions } from '../../api/client';

interface Props {
  message:  Message;
  isRTL?:   boolean;
  onRetry?: () => void;
}

// ── Markdown renderer ─────────────────────────────────────────────────────────
function renderMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code class="bg-slate-100 px-1 py-0.5 rounded text-xs font-mono text-indigo-700">$1</code>')
    .replace(/^### (.+)$/gm, '<h3 class="text-sm font-semibold text-slate-800 mt-3 mb-1">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-sm font-bold text-slate-900 mt-3 mb-1">$1</h2>')
    .replace(/\n- (.+)/g, '</p><ul class="list-disc list-inside space-y-0.5 text-slate-700 ml-2"><li>$1</li></ul><p>')
    .replace(/\n(\d+)\. (.+)/g, '</p><ol class="list-decimal list-inside space-y-0.5 text-slate-700 ml-2"><li>$2</li></ol><p>')
    .replace(/\n\n/g, '</p><p class="mt-2">')
    .replace(/\n/g, '<br/>');
}

// ── Action type labels ────────────────────────────────────────────────────────
const ACTION_LABELS: Record<string, string> = {
  apply_leave:           'Leave Request',
  update_profile:        'Profile Update',
  request_certificate:   'Certificate Request',
  create_ticket:         'IT Support Ticket',
  reset_password:        'Password Reset',
  request_access:        'Access Request',
  submit_expense:        'Expense Claim',
  request_advance:       'Salary Advance',
  query_payslip:         'Payslip Request',
  generate_report:       'Report Generated',
};

// ── Action status card ────────────────────────────────────────────────────────
interface ActionCardProps {
  actionId: string;
  actionType: string;
  initialStatus: string;
}

function ActionStatusCard({ actionId, actionType, initialStatus }: ActionCardProps) {
  const [status, setStatus]       = useState(initialStatus.toUpperCase());
  const [checking, setChecking]   = useState(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    setChecking(true);
    try {
      const actions = await getMyActions();
      const match   = actions.find((a) => a.id === actionId);
      if (match) setStatus(match.status.toUpperCase());
      setLastChecked(new Date());
    } catch {
      // silent
    } finally {
      setChecking(false);
    }
  }, [actionId]);

  const { icon, bg, text, label } = (() => {
    switch (status) {
      case 'APPROVED':
      case 'COMPLETED':
        return {
          icon: <CheckCircle className="w-4 h-4" />,
          bg: 'bg-emerald-50 border-emerald-200',
          text: 'text-emerald-700',
          label: status === 'COMPLETED' ? 'Completed & Executed' : 'Approved',
        };
      case 'REJECTED':
        return {
          icon: <XCircle className="w-4 h-4" />,
          bg: 'bg-rose-50 border-rose-200',
          text: 'text-rose-700',
          label: 'Rejected',
        };
      case 'PENDING':
      default:
        return {
          icon: <Clock className="w-4 h-4" />,
          bg: 'bg-amber-50 border-amber-200',
          text: 'text-amber-700',
          label: 'Awaiting Approval',
        };
    }
  })();

  return (
    <div className={`mt-3 rounded-xl border px-3 py-2.5 ${bg}`}>
      <div className="flex items-center justify-between gap-2">
        <div className={`flex items-center gap-2 ${text}`}>
          {icon}
          <div>
            <p className="text-xs font-semibold">
              {ACTION_LABELS[actionType] ?? actionType.replace(/_/g, ' ')}
            </p>
            <p className="text-[10px] opacity-75">{label}</p>
          </div>
        </div>
        <button
          onClick={refresh}
          disabled={checking}
          title="Refresh status"
          className={`p-1 rounded-lg transition-colors hover:bg-white/60 ${text}`}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${checking ? 'animate-spin' : ''}`} />
        </button>
      </div>
      {lastChecked && (
        <p className={`text-[10px] mt-1 opacity-60 ${text}`}>
          Last checked: {lastChecked.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      )}
      {(status === 'APPROVED' || status === 'COMPLETED') && (
        <div className="flex items-center gap-1 mt-1.5">
          <Zap className="w-3 h-3 text-emerald-600" />
          <p className="text-[10px] text-emerald-600 font-medium">
            Action executed — check your email for confirmation
          </p>
        </div>
      )}
    </div>
  );
}

// ── Message skeleton ──────────────────────────────────────────────────────────
export function MessageSkeleton() {
  return (
    <div className="flex justify-start animate-pulse">
      <div className="max-w-[85%] space-y-1">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-7 h-7 rounded-full bg-slate-200" />
          <div className="h-3 w-16 bg-slate-200 rounded" />
        </div>
        <div className="bg-white border border-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm space-y-2">
          <div className="h-3 bg-slate-100 rounded w-3/4" />
          <div className="h-3 bg-slate-100 rounded w-full" />
          <div className="h-3 bg-slate-100 rounded w-2/3" />
        </div>
      </div>
    </div>
  );
}

// ── Main MessageBubble ────────────────────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function MessageBubble({ message, isRTL, onRetry: _onRetry }: Props) {
  const isUser = message.role === 'user';
  const [rated,  setRated]  = useState<'up' | 'down' | null>(null);
  const [copied, setCopied] = useState(false);

  async function handleRating(rating: 'up' | 'down') {
    if (rated) return;
    setRated(rating);
    if (message.metadata) {
      try {
        await submitFeedback({
          workflow_log_id: message.id,
          rating: rating === 'up' ? 5 : 1,
        });
      } catch {
        // silent fail — feedback is non-critical
      }
    }
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard API not available
    }
  }

  const timeLabel = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit', minute: '2-digit',
  });

  // ── User bubble ─────────────────────────────────────────────────────────────
  if (isUser) {
    return (
      <div className={`flex ${isRTL ? 'justify-start' : 'justify-end'} animate-slide-in`}>
        <div className="max-w-[75%] space-y-1">
          <div className={`bg-indigo-600 text-white px-4 py-2.5 rounded-2xl ${isRTL ? 'rounded-bl-sm' : 'rounded-br-sm'} text-sm leading-relaxed`}>
            {message.content}
          </div>
          <p className={`text-[10px] text-slate-400 ${isRTL ? 'text-left' : 'text-right'} px-1`}>
            {timeLabel}
          </p>
        </div>
      </div>
    );
  }

  // ── Assistant bubble ────────────────────────────────────────────────────────
  return (
    <div className="flex justify-start animate-slide-in">
      <div className="max-w-[85%] space-y-1 w-full">
        {/* Avatar + timestamp */}
        <div className="flex items-center gap-2 mb-1">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
            AI
          </div>
          <span className="text-[10px] text-slate-400">{timeLabel}</span>
          {message.metadata?.agent && (
            <span className="text-[10px] text-slate-400">· {message.metadata.agent}</span>
          )}
        </div>

        {/* Content bubble */}
        <div className="bg-white border border-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm relative group/bubble">
          {message.streaming ? (
            <div className="text-sm text-slate-700 leading-relaxed">
              <span>{message.content}</span>
              <span className="cursor-blink text-indigo-500 font-bold ml-0.5">▋</span>
            </div>
          ) : (
            <>
              <div
                className="prose-agent text-sm text-slate-700 leading-relaxed"
                dangerouslySetInnerHTML={{ __html: `<p>${renderMarkdown(message.content)}</p>` }}
              />

              {/* Copy button — hover-reveal */}
              <button
                onClick={handleCopy}
                title="Copy response"
                className="absolute top-2 right-2 opacity-0 group-hover/bubble:opacity-100 transition-opacity p-1 rounded-md hover:bg-slate-100 text-slate-400 hover:text-slate-600"
              >
                {copied
                  ? <Check className="w-3.5 h-3.5 text-emerald-500" />
                  : <Copy className="w-3.5 h-3.5" />
                }
              </button>

              {/* Action status card — shown when this message triggered an action */}
              {message.metadata?.action_id && message.metadata?.action_type && (
                <ActionStatusCard
                  actionId={message.metadata.action_id}
                  actionType={message.metadata.action_type}
                  initialStatus={message.metadata.action_status ?? 'PENDING'}
                />
              )}

              {/* Agent trace (collapsed by default) */}
              {message.metadata && <AgentTrace metadata={message.metadata} />}
            </>
          )}
        </div>

        {/* Feedback row */}
        {!message.streaming && message.metadata && (
          <div className="flex items-center gap-1 px-1">
            <button
              onClick={() => handleRating('up')}
              title="Helpful"
              disabled={rated !== null}
              className={`p-1 rounded transition-colors ${
                rated === 'up'
                  ? 'text-emerald-600'
                  : 'text-slate-300 hover:text-slate-500 disabled:cursor-default'
              }`}
            >
              <ThumbsUp className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => handleRating('down')}
              title="Not helpful"
              disabled={rated !== null}
              className={`p-1 rounded transition-colors ${
                rated === 'down'
                  ? 'text-red-500'
                  : 'text-slate-300 hover:text-slate-500 disabled:cursor-default'
              }`}
            >
              <ThumbsDown className="w-3.5 h-3.5" />
            </button>
            {rated && (
              <span className="text-[10px] text-slate-400 ml-1">
                {rated === 'up' ? 'Thanks for your feedback!' : "We'll improve this."}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
