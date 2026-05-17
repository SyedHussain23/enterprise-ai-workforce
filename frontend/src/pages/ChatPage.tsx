import { useState, useEffect, useRef, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Sidebar } from '../components/chat/Sidebar';
import { MessageBubble, MessageSkeleton } from '../components/chat/MessageBubble';
import { ChatInput } from '../components/chat/ChatInput';
import { askStream } from '../api/client';
import type { Message, Session, WorkflowResponse } from '../api/types';
import { useRTL } from '../context/RTLContext';
import { Bot } from 'lucide-react';

const STORAGE_KEY = 'chat_sessions';

function loadSessions(): Session[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]');
  } catch {
    return [];
  }
}

function saveSessions(sessions: Session[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

// ── Welcome screen quick-start cards ─────────────────────────────────────────
const QUICK_CARDS_EN = [
  { icon: '👩‍💼', label: 'Annual Leave',        q: 'What is the annual leave policy?' },
  { icon: '💻', label: 'Reset Password',       q: 'How do I reset my password?' },
  { icon: '💰', label: 'Expense Claim',         q: 'How do I submit an expense claim?' },
  { icon: '📋', label: 'UAE Gratuity',          q: 'How is end of service gratuity calculated?' },
  { icon: '🔒', label: 'VPN Access',            q: 'How do I connect to VPN from home?' },
  { icon: '🏠', label: 'Work From Home',        q: 'What is the work from home policy?' },
  { icon: '💳', label: 'Salary Advance',        q: 'How do I apply for a salary advance?' },
  { icon: '🛡️', label: 'Report Phishing',       q: 'I received a suspicious email — what should I do?' },
  { icon: '📅', label: 'Maternity Leave',       q: 'What is the maternity leave policy?' },
  { icon: '💼', label: 'Purchase Order',        q: 'How do I raise a purchase order?' },
  { icon: '🧾', label: 'UAE VAT',               q: 'What is the VAT rate and what are VAT-exempt items?' },
  { icon: '📱', label: 'MFA Setup',             q: 'How do I set up multi-factor authentication?' },
];

const QUICK_CARDS_AR = [
  { icon: '👩‍💼', label: 'الإجازة السنوية',     q: 'ما هي سياسة الإجازة السنوية؟' },
  { icon: '💻', label: 'إعادة تعيين كلمة المرور', q: 'كيف أعيد تعيين كلمة المرور؟' },
  { icon: '💰', label: 'المصروفات',              q: 'كيف أقدم مطالبة بالمصروفات؟' },
  { icon: '📋', label: 'مكافأة نهاية الخدمة',   q: 'كيف تُحسب مكافأة نهاية الخدمة؟' },
  { icon: '🔒', label: 'الشبكة الافتراضية',     q: 'كيف أتصل بالشبكة الافتراضية من المنزل؟' },
  { icon: '🏠', label: 'العمل عن بُعد',         q: 'ما هي سياسة العمل من المنزل؟' },
];

export function ChatPage() {
  const { isRTL } = useRTL();
  const [sessions, setSessions]               = useState<Session[]>(loadSessions);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages]               = useState<Message[]>([]);
  const [loading, setLoading]                 = useState(false);
  const [isTyping, setIsTyping]               = useState(false);
  const [statusHint, setStatusHint]           = useState<string>('');
  const messagesEndRef                        = useRef<HTMLDivElement>(null);
  const sessionMessagesRef                    = useRef<Record<string, Message[]>>({});

  const quickCards = isRTL ? QUICK_CARDS_AR : QUICK_CARDS_EN;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  function createNewSession(): string {
    const id = uuidv4();
    const session: Session = {
      id,
      title: isRTL ? 'محادثة جديدة' : 'New conversation',
      createdAt: new Date().toISOString(),
    };
    setSessions((prev) => {
      const next = [session, ...prev];
      saveSessions(next);
      return next;
    });
    setActiveSessionId(id);
    setMessages([]);
    sessionMessagesRef.current[id] = [];
    return id;
  }

  function selectSession(id: string) {
    setActiveSessionId(id);
    setMessages(sessionMessagesRef.current[id] ?? []);
  }

  const handleSend = useCallback(async (text: string) => {
    let sessionId = activeSessionId;
    if (!sessionId) {
      sessionId = createNewSession();
    }

    const userMsg: Message = {
      id:        uuidv4(),
      role:      'user',
      content:   text,
      timestamp: new Date().toISOString(),
    };

    const streamingId  = uuidv4();
    const streamingMsg: Message = {
      id:        streamingId,
      role:      'assistant',
      content:   '',
      streaming: true,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => {
      const next = [...prev, userMsg, streamingMsg];
      sessionMessagesRef.current[sessionId!] = next;
      return next;
    });
    setLoading(true);
    setIsTyping(true);
    setStatusHint('Analyzing your request…');

    // Update session title from first user message
    if (!sessionMessagesRef.current[sessionId]?.find((m) => m.role === 'user')) {
      setSessions((prev) => {
        const next = prev.map((s) =>
          s.id === sessionId
            ? { ...s, title: text.slice(0, 40) + (text.length > 40 ? '…' : ''), lastMessage: text }
            : s,
        );
        saveSessions(next);
        return next;
      });
    }

    let accumulatedText = '';

    await askStream(
      sessionId,
      text,
      (token) => {
        // First token signals the end of the thinking phase
        if (isTyping) { setIsTyping(false); setStatusHint(''); }
        accumulatedText += token;
        setMessages((prev) => {
          const next = prev.map((m) =>
            m.id === streamingId ? { ...m, content: accumulatedText } : m,
          );
          sessionMessagesRef.current[sessionId!] = next;
          return next;
        });
      },
      (meta: WorkflowResponse) => {
        setIsTyping(false);
        setStatusHint('');
        setMessages((prev) => {
          const next = prev.map((m) =>
            m.id === streamingId
              ? { ...m, content: accumulatedText, streaming: false, metadata: meta }
              : m,
          );
          sessionMessagesRef.current[sessionId!] = next;
          return next;
        });
        setLoading(false);
      },
      (err) => {
        setIsTyping(false);
        setStatusHint('');
        setMessages((prev) => {
          const next = prev.map((m) =>
            m.id === streamingId
              ? { ...m, content: `⚠️ Error: ${err}`, streaming: false }
              : m,
          );
          sessionMessagesRef.current[sessionId!] = next;
          return next;
        });
        setLoading(false);
      },
      (status) => {
        setStatusHint(status);
      },
    );
  }, [activeSessionId]);

  const welcomeVisible = messages.length === 0;

  return (
    <div className={`flex h-screen bg-slate-50 ${isRTL ? 'flex-row-reverse' : 'flex-row'}`}>
      <Sidebar
        sessions={sessions}
        activeId={activeSessionId}
        onSelect={selectSession}
        onNew={createNewSession}
      />

      <main className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="bg-white border-b border-slate-100 px-6 py-3 flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shrink-0">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-800">
              {isRTL ? 'مساعد المؤسسة الذكي' : 'Enterprise AI Assistant'}
            </p>
            <p className="text-xs text-slate-400">
              {isRTL ? 'الموارد البشرية · تقنية المعلومات · المالية' : 'HR · IT · Finance'}
            </p>
          </div>
          <div className="ml-auto flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <span className="text-xs text-slate-400">{isRTL ? 'متصل' : 'Online'}</span>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">

          {/* Welcome screen */}
          {welcomeVisible && (
            <div className="flex flex-col items-center justify-center h-full text-center animate-slide-in">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mb-4 shadow-lg">
                <Bot className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-xl font-bold text-slate-800 mb-2">
                {isRTL ? 'كيف يمكنني مساعدتك؟' : 'How can I help you today?'}
              </h2>
              <p className="text-sm text-slate-500 max-w-sm mb-6">
                {isRTL
                  ? 'اسألني عن الإجازات والرواتب والدعم التقني والمالية والمزيد'
                  : 'Ask me about leave, payslip, IT support, expenses, VAT, gratuity and more.'}
              </p>

              {/* Quick-start card grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2.5 max-w-2xl w-full">
                {quickCards.map((card) => (
                  <button
                    key={card.label}
                    onClick={() => handleSend(card.q)}
                    className="p-3 bg-white border border-slate-100 rounded-xl hover:border-indigo-200 hover:shadow-md hover:-translate-y-0.5 transition-all text-left group"
                  >
                    <div className="text-xl mb-1.5">{card.icon}</div>
                    <p className="text-xs font-medium text-slate-700 group-hover:text-indigo-600 transition-colors leading-tight">
                      {card.label}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Message list */}
          {messages.map((msg) =>
            msg.streaming && !msg.content
              ? <MessageSkeleton key={msg.id} />
              : <MessageBubble key={msg.id} message={msg} isRTL={isRTL} />,
          )}

          {/* Typing indicator — shows routing status hint */}
          {isTyping && (
            <div className="flex justify-start animate-slide-in">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
                  AI
                </div>
                <div className="bg-white border border-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
                  {statusHint ? (
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1 items-center">
                        <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:0ms]" />
                        <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:150ms]" />
                        <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:300ms]" />
                      </div>
                      <span className="text-xs text-slate-400 italic">{statusHint}</span>
                    </div>
                  ) : (
                    <div className="flex gap-1 items-center h-4">
                      <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:0ms]" />
                      <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:150ms]" />
                      <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:300ms]" />
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <ChatInput onSend={handleSend} loading={loading} isRTL={isRTL} />
      </main>
    </div>
  );
}
