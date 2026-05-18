import { useState, useCallback, useRef } from 'react';
import {
  ThumbsUp, ThumbsDown, Copy, Check, RefreshCw,
  Clock, CheckCircle, XCircle, Zap, User, Bot,
} from 'lucide-react';
import type { Message } from '../../api/types';
import { AgentTrace } from './AgentTrace';
import { submitFeedback, getMyActions } from '../../api/client';

interface Props {
  message: Message;
  isRTL?: boolean;
  onRetry?: () => void;
  onRegenerate?: () => void;
  isLast?: boolean;
}

// ── Markdown → HTML renderer ──────────────────────────────────────────────────
// Handles: headers, bold, italic, code blocks, inline code, blockquotes,
//          tables, ordered/unordered lists, horizontal rules, line breaks.
// Code blocks include a data-lang attribute for styling.
function renderMarkdown(raw: string): string {
  let text = raw;

  // 1. Fenced code blocks  ```lang\ncode\n``` → preserve exactly
  const codeBlocks: string[] = [];
  text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    const i = codeBlocks.length;
    codeBlocks.push(
      `<pre class="not-prose"><div class="code-block-header">` +
        `<span class="code-block-lang">${lang || 'text'}</span>` +
        `<button class="code-copy-btn" data-code="${encodeURIComponent(code.trimEnd())}">Copy</button>` +
      `</div><code class="language-${lang || 'text'}">${escapeHtml(code.trimEnd())}</code></pre>`,
    );
    return `\x00code${i}\x00`;
  });

  // 2. Blockquotes
  text = text.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
  text = text.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');

  // 3. Headers
  text = text.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
  text = text.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  text = text.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  text = text.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // 4. Bold + italic (order matters)
  text = text.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  text = text.replace(/\*\*(.+?)\*\*/g,     '<strong>$1</strong>');
  text = text.replace(/\*(.+?)\*/g,         '<em>$1</em>');
  text = text.replace(/__(.+?)__/g,         '<strong>$1</strong>');
  text = text.replace(/_([^_]+)_/g,         '<em>$1</em>');

  // 5. Inline code
  text = text.replace(/`([^`\n]+)`/g, '<code>$1</code>');

  // 6. Horizontal rule
  text = text.replace(/^(---|\*\*\*|___)$/gm, '<hr />');

  // 7. Tables  (| col | col |)
  text = text.replace(
    /((\|[^\n]+\|\n?)+)/g,
    (match) => {
      const rows = match.trim().split('\n').filter(Boolean);
      if (rows.length < 2) return match;
      const isSep = (r: string) => /^\|[\s\-:|]+\|/.test(r);
      const cells = (r: string) =>
        r.replace(/^\||\|$/g, '').split('|').map((c) => c.trim());

      const headerRow = rows[0];
      const sepRow    = rows[1];
      if (!isSep(sepRow)) return match;

      const bodyRows = rows.slice(2);
      const th = cells(headerRow).map((c) => `<th>${c}</th>`).join('');
      const tbody = bodyRows.map(
        (r) => `<tr>${cells(r).map((c) => `<td>${c}</td>`).join('')}</tr>`,
      ).join('');

      return `<table><thead><tr>${th}</tr></thead><tbody>${tbody}</tbody></table>`;
    },
  );

  // 8. Unordered lists
  text = text.replace(/((?:^[ \t]*[-*+] .+\n?)+)/gm, (block) => {
    const items = block.trim().split('\n').map((l) => `<li>${l.replace(/^[ \t]*[-*+] /, '')}</li>`).join('');
    return `<ul>${items}</ul>`;
  });

  // 9. Ordered lists
  text = text.replace(/((?:^[ \t]*\d+\. .+\n?)+)/gm, (block) => {
    const items = block.trim().split('\n').map((l) => `<li>${l.replace(/^[ \t]*\d+\. /, '')}</li>`).join('');
    return `<ol>${items}</ol>`;
  });

  // 10. Paragraphs — double newlines become paragraph breaks
  text = text
    .replace(/\n\n+/g, '</p><p>')
    .replace(/\n/g, '<br />');
  text = `<p>${text}</p>`;

  // 11. Restore code blocks
  codeBlocks.forEach((block, i) => {
    text = text.replace(`\x00code${i}\x00`, block);
  });

  // 12. Clean up paragraphs wrapping block-level elements
  text = text
    .replace(/<p>\s*(<(?:ul|ol|table|h[1-6]|pre|blockquote|hr)[^>]*>)/g, '$1')
    .replace(/(<\/(?:ul|ol|table|h[1-6]|pre|blockquote|hr)>)\s*<\/p>/g, '$1')
    .replace(/<p>\s*<\/p>/g, '')
    .replace(/<br \/>\s*(<(?:ul|ol|table|pre|blockquote))/g, '$1');

  return text;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Action status card ────────────────────────────────────────────────────────
interface ActionCardProps {
  actionId: string;
  actionType: string;
  initialStatus: string;
}

const ACTION_LABELS: Record<string, string> = {
  apply_leave:         'Leave Request',
  update_profile:      'Profile Update',
  request_certificate: 'Certificate Request',
  create_ticket:       'IT Support Ticket',
  reset_password:      'Password Reset',
  request_access:      'Access Request',
  submit_expense:      'Expense Claim',
  request_advance:     'Salary Advance',
  query_payslip:       'Payslip Request',
  generate_report:     'Report Generated',
};

function ActionStatusCard({ actionId, actionType, initialStatus }: ActionCardProps) {
  const [status, setStatus]     = useState(initialStatus.toUpperCase());
  const [checking, setChecking] = useState(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    setChecking(true);
    try {
      const actions = await getMyActions();
      const match   = actions.find((a) => a.id === actionId);
      if (match) setStatus(match.status.toUpperCase());
      setLastChecked(new Date());
    } catch { /* silent */ }
    finally { setChecking(false); }
  }, [actionId]);

  const config = (() => {
    switch (status) {
      case 'APPROVED': case 'COMPLETED':
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
    <div className={`mt-3 rounded-xl border px-3 py-2.5 ${config.bg}`}>
      <div className="flex items-center justify-between gap-2">
        <div className={`flex items-center gap-2 ${config.text}`}>
          {config.icon}
          <div>
            <p className="text-xs font-semibold">
              {ACTION_LABELS[actionType] ?? actionType.replace(/_/g, ' ')}
            </p>
            <p className="text-[10px] opacity-75">{config.label}</p>
          </div>
        </div>
        <button onClick={refresh} disabled={checking} title="Refresh status"
          className={`p-1 rounded-lg transition-colors hover:bg-white/60 ${config.text}`}>
          <RefreshCw className={`w-3.5 h-3.5 ${checking ? 'animate-spin' : ''}`} />
        </button>
      </div>
      {lastChecked && (
        <p className={`text-[10px] mt-1 opacity-60 ${config.text}`}>
          Checked: {lastChecked.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      )}
      {(status === 'APPROVED' || status === 'COMPLETED') && (
        <div className="flex items-center gap-1 mt-1.5">
          <Zap className="w-3 h-3 text-emerald-600" />
          <p className="text-[10px] text-emerald-600 font-medium">
            Action executed — check your email
          </p>
        </div>
      )}
    </div>
  );
}

// ── Message skeleton ──────────────────────────────────────────────────────────
export function MessageSkeleton() {
  return (
    <div className="flex justify-start animate-pulse px-4 py-2">
      <div className="flex items-start gap-3 w-full max-w-[85%]">
        <div className="w-7 h-7 rounded-full bg-slate-200 shrink-0 mt-0.5" />
        <div className="flex-1 space-y-2 pt-1">
          <div className="h-3 bg-slate-100 rounded-full w-3/4" />
          <div className="h-3 bg-slate-100 rounded-full w-full" />
          <div className="h-3 bg-slate-100 rounded-full w-2/3" />
        </div>
      </div>
    </div>
  );
}

// ── Main MessageBubble ────────────────────────────────────────────────────────
export function MessageBubble({ message, isRTL, onRetry: _onRetry, onRegenerate, isLast }: Props) {
  const isUser = message.role === 'user';
  const [rated, setRated]   = useState<'up' | 'down' | null>(null);
  const [copied, setCopied] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  const timeLabel = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit', minute: '2-digit',
  });

  async function handleRating(rating: 'up' | 'down') {
    if (rated) return;
    setRated(rating);
    if (message.metadata) {
      try {
        await submitFeedback({ workflow_log_id: message.id, rating: rating === 'up' ? 5 : 1 });
      } catch { /* non-critical */ }
    }
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* clipboard not available */ }
  }

  // ── Code block copy handlers — delegated from dangerouslySetInnerHTML ───────
  function handleContentClick(e: React.MouseEvent<HTMLDivElement>) {
    const target = e.target as HTMLElement;
    if (target.classList.contains('code-copy-btn')) {
      const encoded = target.getAttribute('data-code') ?? '';
      const code = decodeURIComponent(encoded);
      navigator.clipboard.writeText(code).then(() => {
        const prev = target.textContent;
        target.textContent = 'Copied!';
        setTimeout(() => { target.textContent = prev; }, 1500);
      }).catch(() => {});
    }
  }

  // ── User bubble ──────────────────────────────────────────────────────────────
  if (isUser) {
    return (
      <div className={`flex items-end gap-2.5 ${isRTL ? 'flex-row' : 'flex-row-reverse'} animate-slide-in px-4 py-1`}>
        {/* Avatar */}
        <div className="w-7 h-7 rounded-full bg-slate-200 flex items-center justify-center shrink-0 mb-1">
          <User className="w-3.5 h-3.5 text-slate-500" />
        </div>
        <div className={`max-w-[75%] ${isRTL ? 'items-start' : 'items-end'} flex flex-col gap-1`}>
          {message.attachmentName && (
            <div className="flex items-center gap-1.5 bg-indigo-50 border border-indigo-100 rounded-lg px-2.5 py-1.5 text-xs text-indigo-600 font-medium self-end">
              📎 {message.attachmentName}
            </div>
          )}
          <div className={`bg-indigo-600 text-white px-4 py-2.5 rounded-2xl ${isRTL ? 'rounded-bl-sm' : 'rounded-br-sm'} text-sm leading-relaxed shadow-sm`}>
            {message.content}
          </div>
          <p className={`text-[10px] text-slate-400 ${isRTL ? 'text-left' : 'text-right'} px-1`}>
            {timeLabel}
          </p>
        </div>
      </div>
    );
  }

  // ── Assistant bubble ─────────────────────────────────────────────────────────
  return (
    <div className={`flex items-start gap-2.5 animate-slide-in px-4 py-1 group/msg`}>
      {/* Avatar */}
      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shrink-0 mt-0.5">
        <Bot className="w-3.5 h-3.5 text-white" />
      </div>

      <div className="flex-1 min-w-0 max-w-[85%]">
        {/* Name + timestamp */}
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-medium text-slate-600">
            {message.metadata?.agent
              ? `${message.metadata.agent} Agent`
              : 'Enterprise AI'}
          </span>
          <span className="text-[10px] text-slate-400">{timeLabel}</span>
        </div>

        {/* Content bubble */}
        <div className="relative group/bubble">
          {message.streaming ? (
            <div className="prose-agent text-sm leading-relaxed">
              <span>{message.content}</span>
              <span className="cursor-blink text-indigo-400 font-bold ml-0.5">▋</span>
            </div>
          ) : (
            <>
              <div
                ref={contentRef}
                className="prose-agent"
                dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
                onClick={handleContentClick}
              />

              {/* Action card */}
              {message.metadata?.action_id && message.metadata?.action_type && (
                <ActionStatusCard
                  actionId={message.metadata.action_id}
                  actionType={message.metadata.action_type}
                  initialStatus={message.metadata.action_status ?? 'PENDING'}
                />
              )}

              {/* Agent trace */}
              {message.metadata && <AgentTrace metadata={message.metadata} />}

              {/* Message actions — appear on hover */}
              <div className="msg-actions flex items-center gap-1 mt-2">
                <button
                  onClick={handleCopy}
                  title="Copy response"
                  className="flex items-center gap-1 px-2 py-1 text-[11px] text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-md transition-colors"
                >
                  {copied
                    ? <><Check className="w-3 h-3 text-emerald-500" /><span className="text-emerald-600">Copied</span></>
                    : <><Copy className="w-3 h-3" /><span>Copy</span></>
                  }
                </button>
                {isLast && onRegenerate && (
                  <button
                    onClick={onRegenerate}
                    title="Regenerate response"
                    className="flex items-center gap-1 px-2 py-1 text-[11px] text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-md transition-colors"
                  >
                    <RefreshCw className="w-3 h-3" />
                    <span>Regenerate</span>
                  </button>
                )}
              </div>
            </>
          )}
        </div>

        {/* Feedback */}
        {!message.streaming && message.metadata && (
          <div className="flex items-center gap-1 mt-1.5">
            <button
              onClick={() => handleRating('up')}
              disabled={rated !== null}
              title="Helpful"
              className={`p-1 rounded transition-colors ${
                rated === 'up' ? 'text-emerald-600' : 'text-slate-300 hover:text-slate-500 disabled:cursor-default'
              }`}
            >
              <ThumbsUp className="w-3 h-3" />
            </button>
            <button
              onClick={() => handleRating('down')}
              disabled={rated !== null}
              title="Not helpful"
              className={`p-1 rounded transition-colors ${
                rated === 'down' ? 'text-red-500' : 'text-slate-300 hover:text-slate-500 disabled:cursor-default'
              }`}
            >
              <ThumbsDown className="w-3 h-3" />
            </button>
            {rated && (
              <span className="text-[10px] text-slate-400 ml-1">
                {rated === 'up' ? 'Thanks!' : "We'll improve this."}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
