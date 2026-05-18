import { useState, useEffect, useRef, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import toast, { Toaster } from 'react-hot-toast';
import { Sidebar } from '../components/chat/Sidebar';
import { MessageBubble, MessageSkeleton } from '../components/chat/MessageBubble';
import { ChatInput } from '../components/chat/ChatInput';
import { askStream, extractDocument } from '../api/client';
import type { Message, Session, WorkflowResponse } from '../api/types';
import { useRTL } from '../context/RTLContext';
import { Bot, Menu, ChevronDown } from 'lucide-react';

// ── Storage helpers ───────────────────────────────────────────────────────────
const SESSIONS_KEY  = 'chat_sessions_v2';
const MESSAGES_KEY  = (id: string) => `chat_messages_v2_${id}`;
const MAX_STORED_SESSIONS = 50;
const MAX_MSGS_PER_SESSION = 100;

function loadSessions(): Session[] {
  try { return JSON.parse(localStorage.getItem(SESSIONS_KEY) ?? '[]'); }
  catch { return []; }
}

function saveSessions(sessions: Session[]) {
  try {
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions.slice(0, MAX_STORED_SESSIONS)));
  } catch { /* storage full */ }
}

function loadMessages(sessionId: string): Message[] {
  try { return JSON.parse(localStorage.getItem(MESSAGES_KEY(sessionId)) ?? '[]'); }
  catch { return []; }
}

function saveMessages(sessionId: string, messages: Message[]) {
  try {
    // Only persist non-streaming, non-error messages
    const toSave = messages
      .filter((m) => !m.streaming)
      .slice(-MAX_MSGS_PER_SESSION);
    localStorage.setItem(MESSAGES_KEY(sessionId), JSON.stringify(toSave));
  } catch { /* storage full */ }
}

function deleteMessages(sessionId: string) {
  try { localStorage.removeItem(MESSAGES_KEY(sessionId)); } catch {}
}

// ── Welcome quick-start cards ─────────────────────────────────────────────────
const CARDS_EN = [
  { icon: '👩‍💼', label: 'Annual Leave',     q: 'What is the annual leave policy?' },
  { icon: '💻', label: 'Reset Password',    q: 'How do I reset my password?' },
  { icon: '💰', label: 'Expense Claim',      q: 'How do I submit an expense claim?' },
  { icon: '📋', label: 'UAE Gratuity',       q: 'How is end of service gratuity calculated?' },
  { icon: '🔒', label: 'VPN Access',         q: 'How do I connect to VPN from home?' },
  { icon: '🏠', label: 'Work From Home',     q: 'What is the work from home policy?' },
  { icon: '💳', label: 'Salary Advance',     q: 'How do I apply for a salary advance?' },
  { icon: '🛡️', label: 'Report Phishing',   q: 'I received a suspicious email, what should I do?' },
  { icon: '📅', label: 'Maternity Leave',   q: 'What is the maternity leave policy?' },
  { icon: '🧾', label: 'UAE VAT',            q: 'What is the VAT rate and exempt items?' },
  { icon: '📱', label: 'MFA Setup',          q: 'How do I set up multi-factor authentication?' },
  { icon: '💼', label: 'Purchase Order',     q: 'How do I raise a purchase order?' },
];

const CARDS_AR = [
  { icon: '👩‍💼', label: 'الإجازة السنوية',     q: 'ما هي سياسة الإجازة السنوية؟' },
  { icon: '💻', label: 'كلمة المرور',            q: 'كيف أعيد تعيين كلمة المرور؟' },
  { icon: '💰', label: 'المصروفات',              q: 'كيف أقدم مطالبة بالمصروفات؟' },
  { icon: '📋', label: 'مكافأة نهاية الخدمة',  q: 'كيف تُحسب مكافأة نهاية الخدمة؟' },
  { icon: '🔒', label: 'الشبكة الافتراضية',    q: 'كيف أتصل بالشبكة الافتراضية من المنزل؟' },
  { icon: '🏠', label: 'العمل عن بُعد',         q: 'ما هي سياسة العمل من المنزل؟' },
];

export function ChatPage() {
  const { isRTL } = useRTL();
  const [sessions, setSessions]     = useState<Session[]>(loadSessions);
  const [activeId, setActiveId]     = useState<string | null>(null);
  const [messages, setMessages]     = useState<Message[]>([]);
  const [loading, setLoading]       = useState(false);
  const [isStreaming, setStreaming]  = useState(false);
  const [statusHint, setStatusHint] = useState('');
  const [extracting, setExtracting] = useState(false);
  const [sidebarOpen, setSidebar]   = useState(false);
  const [atBottom, setAtBottom]     = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef  = useRef<HTMLDivElement>(null);
  const cancelStreamRef = useRef<(() => void) | null>(null);
  const lastQuestionRef = useRef<{ text: string; file?: File } | null>(null);
  const streamingIdRef  = useRef<string | null>(null);

  const cards = isRTL ? CARDS_AR : CARDS_EN;

  // ── Scroll management ──────────────────────────────────────────────────────
  function scrollToBottom(force = false) {
    if (force || atBottom) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }

  function handleScroll() {
    const el = scrollAreaRef.current;
    if (!el) return;
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setAtBottom(distFromBottom < 80);
  }

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // ── Session management ─────────────────────────────────────────────────────
  function createNewSession(): string {
    const id = uuidv4();
    const session: Session = {
      id,
      title: isRTL ? 'محادثة جديدة' : 'New conversation',
      createdAt: new Date().toISOString(),
      messageCount: 0,
    };
    setSessions((prev) => {
      const next = [session, ...prev];
      saveSessions(next);
      return next;
    });
    setActiveId(id);
    setMessages([]);
    return id;
  }

  function selectSession(id: string) {
    if (isStreaming) cancelStream();
    setActiveId(id);
    const msgs = loadMessages(id);
    setMessages(msgs);
    setTimeout(() => scrollToBottom(true), 100);
  }

  function deleteSession(id: string) {
    deleteMessages(id);
    setSessions((prev) => {
      const next = prev.filter((s) => s.id !== id);
      saveSessions(next);
      return next;
    });
    if (activeId === id) {
      setActiveId(null);
      setMessages([]);
    }
    toast.success('Conversation deleted');
  }

  function renameSession(id: string, title: string) {
    setSessions((prev) => {
      const next = prev.map((s) => s.id === id ? { ...s, title } : s);
      saveSessions(next);
      return next;
    });
  }

  function pinSession(id: string) {
    setSessions((prev) => {
      const next = prev.map((s) =>
        s.id === id ? { ...s, pinnedAt: s.pinnedAt ? undefined : new Date().toISOString() } : s,
      );
      saveSessions(next);
      return next;
    });
  }

  // ── Streaming cancellation ─────────────────────────────────────────────────
  function cancelStream() {
    cancelStreamRef.current?.();
    cancelStreamRef.current = null;
    setStreaming(false);
    setLoading(false);
    setStatusHint('');
    // Replace the streaming bubble with the partial text
    setMessages((prev) => prev.map((m) =>
      m.id === streamingIdRef.current
        ? { ...m, streaming: false }
        : m,
    ));
    streamingIdRef.current = null;
  }

  // ── Core send handler ──────────────────────────────────────────────────────
  const handleSend = useCallback(async (text: string, file?: File) => {
    let sessionId = activeId;
    if (!sessionId) sessionId = createNewSession();

    lastQuestionRef.current = { text, file };

    // File extraction
    let questionText = text;
    if (file) {
      try {
        setExtracting(true);
        const extracted = await extractDocument(file);
        const prefix = extracted.truncated
          ? `[📎 ${file.name} — first ${extracted.chars.toLocaleString()} chars shown]\n${extracted.text}`
          : `[📎 ${file.name}]\n${extracted.text}`;
        questionText = text ? `${prefix}\n\nUser question: ${text}` : `Please analyse this document:\n\n${prefix}`;
      } catch (err) {
        toast.error(`File extraction failed: ${(err as Error).message}`);
        questionText = text || `[Could not read ${file.name}]`;
      } finally {
        setExtracting(false);
      }
    }

    // User message bubble
    const userMsg: Message = {
      id:             uuidv4(),
      role:           'user',
      content:        file ? (text ? `${text}` : '') : text,
      timestamp:      new Date().toISOString(),
      attachmentName: file?.name,
    };

    const streamId = uuidv4();
    streamingIdRef.current = streamId;

    const streamingMsg: Message = {
      id:        streamId,
      role:      'assistant',
      content:   '',
      streaming: true,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => {
      const next = [...prev, userMsg, streamingMsg];
      return next;
    });
    setLoading(true);
    setStreaming(true);
    setStatusHint(isRTL ? 'جارٍ تحليل طلبك…' : 'Analyzing your request…');

    // Update session title from first non-file message
    const titleText = text || (file?.name ?? 'File analysis');
    setSessions((prev) => {
      const s = prev.find((s) => s.id === sessionId);
      if (s && (s.title === 'New conversation' || s.title === 'محادثة جديدة')) {
        const title = titleText.slice(0, 45) + (titleText.length > 45 ? '…' : '');
        const next = prev.map((s) => s.id === sessionId ? { ...s, title, lastMessage: titleText } : s);
        saveSessions(next);
        return next;
      }
      return prev;
    });

    let accText = '';

    const { cancel, promise } = askStream(
      sessionId,
      questionText,
      (token) => {
        accText += token;
        setStatusHint('');
        setMessages((prev) => prev.map((m) =>
          m.id === streamId ? { ...m, content: accText } : m,
        ));
        scrollToBottom();
      },
      (meta: WorkflowResponse) => {
        cancelStreamRef.current = null;
        streamingIdRef.current = null;
        setStreaming(false);
        setLoading(false);
        setStatusHint('');
        setMessages((prev) => {
          const next = prev.map((m) =>
            m.id === streamId
              ? { ...m, content: accText || meta.answer, streaming: false, metadata: meta }
              : m,
          );
          // Persist after done
          saveMessages(sessionId!, next.filter((m) => !m.streaming));
          // Update message count
          setSessions((s) => {
            const updated = s.map((sess) =>
              sess.id === sessionId
                ? { ...sess, messageCount: next.filter((m) => m.role === 'user').length }
                : sess,
            );
            saveSessions(updated);
            return updated;
          });
          return next;
        });
        scrollToBottom(true);
      },
      (err) => {
        cancelStreamRef.current = null;
        streamingIdRef.current = null;
        setStreaming(false);
        setLoading(false);
        setStatusHint('');

        const errLower = err.toLowerCase();
        const isAuth = errLower.includes('token') || errLower.includes('unauthorized') || errLower.includes('credentials');
        if (isAuth) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('user_role');
          window.location.href = '/login';
          return;
        }

        toast.error(err, { duration: 4000 });
        setMessages((prev) => prev.map((m) =>
          m.id === streamId ? { ...m, content: '', streaming: false, isError: true } : m,
        ));
      },
      (status) => setStatusHint(status),
    );

    cancelStreamRef.current = cancel;
    await promise;
  }, [activeId, isRTL]);

  // ── Retry ─────────────────────────────────────────────────────────────────
  const handleRetry = useCallback(() => {
    const last = lastQuestionRef.current;
    if (!last || loading) return;
    setMessages((prev) => {
      const next = prev.filter((m) => !m.isError).slice(0, -1); // remove error + last user msg
      if (activeId) saveMessages(activeId, next);
      return next;
    });
    handleSend(last.text, last.file);
  }, [handleSend, loading, activeId]);

  // ── Regenerate last assistant response ────────────────────────────────────
  const handleRegenerate = useCallback(() => {
    const last = lastQuestionRef.current;
    if (!last || loading) return;
    // Remove last assistant message
    setMessages((prev) => {
      const lastAssistIdx = [...prev].reverse().findIndex((m) => m.role === 'assistant');
      if (lastAssistIdx === -1) return prev;
      const idx = prev.length - 1 - lastAssistIdx;
      const next = prev.slice(0, idx);
      if (activeId) saveMessages(activeId, next);
      return next;
    });
    handleSend(last.text, last.file);
  }, [handleSend, loading, activeId]);

  const welcomeVisible = messages.length === 0;
  const lastNonError   = [...messages].reverse().find((m) => m.role === 'assistant' && !m.isError && !m.streaming);

  return (
    <div className={`flex h-full overflow-hidden ${isRTL ? 'flex-row-reverse' : 'flex-row'}`}>
      <Toaster
        position="top-right"
        toastOptions={{
          className: 'text-sm',
          style: { borderRadius: '12px', boxShadow: '0 4px 24px rgba(0,0,0,0.12)' },
        }}
      />

      {/* Sidebar */}
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        onSelect={selectSession}
        onNew={() => { if (isStreaming) cancelStream(); createNewSession(); }}
        onDelete={deleteSession}
        onRename={renameSession}
        onPin={pinSession}
        isOpen={sidebarOpen}
        onClose={() => setSidebar(false)}
      />

      {/* Main area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <div className="bg-white border-b border-slate-100 px-4 py-3 flex items-center gap-3 shrink-0 z-30">
          {/* Mobile hamburger */}
          <button
            onClick={() => setSidebar(true)}
            className="md:hidden p-1.5 -ml-1 text-slate-500 hover:text-slate-800 rounded-lg hover:bg-slate-100 transition-colors"
            aria-label="Open menu"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shrink-0">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-slate-800 leading-tight truncate">
              {isRTL ? 'مساعد المؤسسة الذكي' : 'Enterprise AI Assistant'}
            </p>
            <p className="text-[11px] text-slate-400">
              {isRTL ? 'الموارد البشرية · تقنية المعلومات · المالية' : 'HR · IT · Finance'}
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {/* Online indicator */}
            <span className="hidden sm:flex items-center gap-1.5">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
              </span>
              <span className="text-xs text-slate-400">{isRTL ? 'متصل' : 'Online'}</span>
            </span>
          </div>
        </div>

        {/* File extracting banner */}
        {extracting && (
          <div className="bg-indigo-50 border-b border-indigo-100 px-4 py-2 flex items-center gap-2 shrink-0">
            <div className="w-3.5 h-3.5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-indigo-600 font-medium">
              {isRTL ? 'جارٍ استخراج نص المستند…' : 'Extracting document text…'}
            </span>
          </div>
        )}

        {/* Messages */}
        <div
          ref={scrollAreaRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto py-4"
        >
          {welcomeVisible ? (
            <div className="flex flex-col items-center justify-center min-h-full px-4 py-8 text-center animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mb-5 shadow-lg shadow-indigo-200">
                <Bot className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-xl font-bold text-slate-800 mb-2">
                {isRTL ? 'كيف يمكنني مساعدتك؟' : 'How can I help you today?'}
              </h2>
              <p className="text-sm text-slate-500 max-w-sm mb-8">
                {isRTL
                  ? 'اسألني عن الإجازات والرواتب والدعم التقني والمالية والمزيد'
                  : 'Ask about leave, payslip, IT support, expenses, VAT, gratuity and more.'
                }
              </p>

              {/* Quick-start grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2.5 max-w-2xl w-full">
                {cards.map((card) => (
                  <button
                    key={card.label}
                    onClick={() => handleSend(card.q)}
                    className="p-3 bg-white border border-slate-100 rounded-xl hover:border-indigo-200 hover:shadow-md hover:-translate-y-0.5 transition-all text-left group active:scale-[0.98]"
                  >
                    <div className="text-xl mb-1.5">{card.icon}</div>
                    <p className="text-xs font-medium text-slate-700 group-hover:text-indigo-600 transition-colors leading-snug">
                      {card.label}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-0.5 pb-2">
              {messages.map((msg) => {
                if (msg.streaming && !msg.content) {
                  return <MessageSkeleton key={msg.id} />;
                }
                if (msg.isError) {
                  return (
                    <div key={msg.id} className="flex items-start gap-2.5 px-4 py-2 animate-slide-in">
                      <div className="w-7 h-7 rounded-full bg-rose-100 flex items-center justify-center text-rose-600 text-xs font-bold shrink-0 mt-0.5">!</div>
                      <div className="max-w-[85%]">
                        <div className="bg-rose-50 border border-rose-200 rounded-2xl rounded-tl-sm px-4 py-3">
                          <p className="text-sm text-rose-700 mb-2.5">
                            {isRTL ? 'حدث خطأ. يرجى المحاولة مرة أخرى.' : 'Something went wrong. Please try again.'}
                          </p>
                          <button
                            onClick={handleRetry}
                            disabled={loading}
                            className="flex items-center gap-1.5 text-xs font-medium text-rose-600 hover:text-rose-800 border border-rose-200 hover:border-rose-400 bg-white rounded-lg px-3 py-1.5 transition-all disabled:opacity-40"
                          >
                            <Bot className="w-3 h-3" /> {isRTL ? 'إعادة المحاولة' : 'Try again'}
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                }
                const isLastAssistant = msg.role === 'assistant' && msg.id === lastNonError?.id;
                return (
                  <MessageBubble
                    key={msg.id}
                    message={msg}
                    isRTL={isRTL}
                    onRetry={msg.isError ? handleRetry : undefined}
                    onRegenerate={isLastAssistant ? handleRegenerate : undefined}
                    isLast={isLastAssistant}
                  />
                );
              })}

              {/* Typing indicator */}
              {(loading || isStreaming) && statusHint && (
                <div className="flex items-start gap-2.5 px-4 py-2 animate-slide-in">
                  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shrink-0 mt-0.5">
                    <Bot className="w-3.5 h-3.5 text-white" />
                  </div>
                  <div className="bg-white border border-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm max-w-xs">
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <span className="typing-dot w-1.5 h-1.5 bg-indigo-400 rounded-full" />
                        <span className="typing-dot w-1.5 h-1.5 bg-indigo-400 rounded-full" />
                        <span className="typing-dot w-1.5 h-1.5 bg-indigo-400 rounded-full" />
                      </div>
                      <span className="text-xs text-slate-400 italic">{statusHint}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Scroll-to-bottom button */}
        {!atBottom && messages.length > 0 && (
          <div className="flex justify-center pb-2 shrink-0">
            <button
              onClick={() => { setAtBottom(true); scrollToBottom(true); }}
              className="flex items-center gap-1.5 text-xs text-slate-500 bg-white border border-slate-200 hover:border-indigo-300 hover:text-indigo-600 px-3 py-1.5 rounded-full shadow-sm transition-all animate-fade-in"
            >
              <ChevronDown className="w-3.5 h-3.5" />
              {isRTL ? 'انتقل إلى الأسفل' : 'Scroll to bottom'}
            </button>
          </div>
        )}

        {/* Input */}
        <ChatInput
          onSend={handleSend}
          onStop={cancelStream}
          loading={loading || extracting}
          isStreaming={isStreaming}
          isRTL={isRTL}
        />
      </main>
    </div>
  );
}
