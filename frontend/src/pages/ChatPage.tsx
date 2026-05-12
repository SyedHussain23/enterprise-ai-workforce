import { useState, useEffect, useRef, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Sidebar } from '../components/chat/Sidebar';
import { MessageBubble } from '../components/chat/MessageBubble';
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

export function ChatPage() {
  const { isRTL } = useRTL();
  const [sessions, setSessions] = useState<Session[]>(loadSessions);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sessionMessagesRef = useRef<Record<string, Message[]>>({});

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
      id: uuidv4(),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };

    const streamingId = uuidv4();
    const streamingMsg: Message = {
      id: streamingId,
      role: 'assistant',
      content: '',
      streaming: true,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => {
      const next = [...prev, userMsg, streamingMsg];
      sessionMessagesRef.current[sessionId!] = next;
      return next;
    });
    setLoading(true);

    // Update session title from first message
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
        setMessages((prev) => {
          const next = prev.map((m) =>
            m.id === streamingId
              ? { ...m, content: `Error: ${err}`, streaming: false }
              : m,
          );
          sessionMessagesRef.current[sessionId!] = next;
          return next;
        });
        setLoading(false);
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
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
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
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-xs text-slate-400">{isRTL ? 'متصل' : 'Online'}</span>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {welcomeVisible && (
            <div className="flex flex-col items-center justify-center h-full text-center animate-slide-in">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mb-4 shadow-lg">
                <Bot className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-xl font-bold text-slate-800 mb-2">
                {isRTL ? 'كيف يمكنني مساعدتك؟' : 'How can I help you today?'}
              </h2>
              <p className="text-sm text-slate-500 max-w-sm">
                {isRTL
                  ? 'اسألني عن الإجازات والرواتب والدعم التقني والمالية والمزيد'
                  : 'Ask me about leave policies, IT support, expense claims, salary, and more.'}
              </p>
              <div className="mt-6 grid grid-cols-3 gap-3">
                {[
                  { icon: '👥', label: isRTL ? 'الموارد البشرية' : 'HR Policies', q: isRTL ? 'ما هي سياسة الإجازة السنوية؟' : 'What is the annual leave policy?' },
                  { icon: '💻', label: isRTL ? 'تقنية المعلومات' : 'IT Support', q: isRTL ? 'كيف أعيد تعيين كلمة المرور؟' : 'How do I reset my password?' },
                  { icon: '💰', label: isRTL ? 'المالية' : 'Finance', q: isRTL ? 'كيف أقدم مطالبة بالمصروفات؟' : 'How do I claim expenses?' },
                ].map((card) => (
                  <button
                    key={card.label}
                    onClick={() => handleSend(card.q)}
                    className="p-4 bg-white border border-slate-100 rounded-xl hover:border-indigo-200 hover:shadow-sm transition-all text-left group"
                  >
                    <div className="text-2xl mb-2">{card.icon}</div>
                    <p className="text-xs font-medium text-slate-700 group-hover:text-indigo-600 transition-colors">
                      {card.label}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} isRTL={isRTL} />
          ))}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <ChatInput onSend={handleSend} loading={loading} isRTL={isRTL} />
      </main>
    </div>
  );
}
