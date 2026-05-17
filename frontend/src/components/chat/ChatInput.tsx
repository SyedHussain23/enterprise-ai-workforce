import { useState, useRef, type KeyboardEvent } from 'react';
import { Send, Mic, Paperclip } from 'lucide-react';
import { Spinner } from '../shared/Spinner';

interface Props {
  onSend: (message: string) => void;
  loading: boolean;
  isRTL?: boolean;
  placeholder?: string;
}

const MAX_CHARS = 2000;

const SUGGESTIONS_EN = [
  'What is the annual leave policy?',
  'How do I reset my password?',
  'How do I submit an expense claim?',
  'What is the UAE gratuity formula?',
  'How do I connect to VPN?',
  'What is the WFH policy?',
  'How do I apply for a salary advance?',
  'How do I report a phishing email?',
];

const SUGGESTIONS_AR = [
  'كيف أقدم طلب إجازة؟',
  'كيف أعيد تعيين كلمة المرور؟',
  'كيف أقدم مطالبة بالمصروفات؟',
  'ما هي مكافأة نهاية الخدمة؟',
  'كيف أتصل بالشبكة الافتراضية؟',
];

export function ChatInput({ onSend, loading, isRTL, placeholder }: Props) {
  const [value, setValue]       = useState('');
  const [showAll, setShowAll]   = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const defaultPlaceholder = isRTL
    ? 'اكتب سؤالك هنا... (اضغط Enter للإرسال)'
    : 'Ask HR, IT, or Finance anything... (Enter to send, Shift+Enter for newline)';

  const suggestions = isRTL ? SUGGESTIONS_AR : SUGGESTIONS_EN;
  const visibleSuggestions = showAll ? suggestions : suggestions.slice(0, 4);

  function handleSend() {
    const trimmed = value.trim();
    if (!trimmed || loading) return;
    onSend(trimmed);
    setValue('');
    setShowAll(false);
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleInput() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }

  function handleSuggestion(s: string) {
    setValue(s);
    setShowAll(false);
    setTimeout(() => textareaRef.current?.focus(), 0);
  }

  const remaining   = MAX_CHARS - value.length;
  const nearLimit   = remaining < 200;
  const atLimit     = remaining <= 0;

  return (
    <div className="border-t border-slate-100 bg-white px-4 py-3">
      {/* Quick suggestion chips */}
      {!value && (
        <div className="mb-2">
          <div className="flex flex-wrap gap-1.5">
            {visibleSuggestions.map((s) => (
              <button
                key={s}
                onClick={() => handleSuggestion(s)}
                className="text-xs px-3 py-1.5 bg-slate-50 hover:bg-indigo-50 hover:text-indigo-700 hover:border-indigo-200 text-slate-600 rounded-full border border-slate-200 transition-all"
              >
                {s}
              </button>
            ))}
            {suggestions.length > 4 && (
              <button
                onClick={() => setShowAll((v) => !v)}
                className="text-xs px-3 py-1.5 bg-white hover:bg-slate-50 text-indigo-500 rounded-full border border-indigo-100 transition-all"
              >
                {showAll ? (isRTL ? 'أقل' : 'Less') : (isRTL ? 'المزيد...' : 'More...')}
              </button>
            )}
          </div>
        </div>
      )}

      <div className="flex items-end gap-2">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value.slice(0, MAX_CHARS))}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            placeholder={placeholder ?? defaultPlaceholder}
            rows={1}
            disabled={loading}
            dir={isRTL ? 'rtl' : 'ltr'}
            className="w-full resize-none rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:opacity-50 transition-all pr-12"
          />
          {/* Character counter */}
          {value.length > 0 && (
            <span
              className={`absolute bottom-2 right-3 text-[10px] select-none transition-colors ${
                atLimit   ? 'text-red-500 font-semibold' :
                nearLimit ? 'text-amber-500' :
                            'text-slate-300'
              }`}
            >
              {remaining}
            </span>
          )}
        </div>

        {/* Attachment button (placeholder — future feature) */}
        <button
          disabled
          title={isRTL ? 'إرفاق ملف (قريباً)' : 'Attach file (coming soon)'}
          className="shrink-0 w-10 h-10 rounded-xl border border-slate-200 text-slate-300 flex items-center justify-center cursor-not-allowed"
        >
          <Paperclip className="w-4 h-4" />
        </button>

        {/* Send button */}
        <button
          onClick={handleSend}
          disabled={!value.trim() || loading || atLimit}
          title={isRTL ? 'إرسال' : 'Send (Enter)'}
          className="shrink-0 w-10 h-10 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed text-white flex items-center justify-center transition-all"
        >
          {loading ? <Spinner className="w-4 h-4 text-white" /> : <Send className="w-4 h-4" />}
        </button>

        {/* Voice input (placeholder) */}
        <button
          disabled
          title={isRTL ? 'الإدخال الصوتي (قريباً)' : 'Voice input (coming soon)'}
          className="shrink-0 w-10 h-10 rounded-xl border border-slate-200 text-slate-300 flex items-center justify-center cursor-not-allowed"
        >
          <Mic className="w-4 h-4" />
        </button>
      </div>

      {/* Keyboard hint */}
      {!isRTL && (
        <p className="mt-1.5 text-[10px] text-slate-300 text-center select-none">
          Enter to send · Shift+Enter for new line
        </p>
      )}
    </div>
  );
}
