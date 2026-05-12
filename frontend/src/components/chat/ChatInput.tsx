import { useState, useRef, type KeyboardEvent } from 'react';
import { Send, Mic } from 'lucide-react';
import { Spinner } from '../shared/Spinner';

interface Props {
  onSend: (message: string) => void;
  loading: boolean;
  isRTL?: boolean;
  placeholder?: string;
}

export function ChatInput({ onSend, loading, isRTL, placeholder }: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const defaultPlaceholder = isRTL
    ? 'اكتب سؤالك هنا...'
    : 'Ask HR, IT, or Finance anything...';

  function handleSend() {
    const trimmed = value.trim();
    if (!trimmed || loading) return;
    onSend(trimmed);
    setValue('');
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

  const suggestions = isRTL
    ? ['كيف أقدم إجازة؟', 'سياسة كلمة المرور', 'سياسة المصروفات']
    : ['How do I apply for leave?', 'Reset my password', 'Submit an expense claim'];

  return (
    <div className="border-t border-slate-100 bg-white px-4 py-3">
      {/* Quick suggestions */}
      {!value && (
        <div className="flex gap-2 mb-2 overflow-x-auto pb-1">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => { setValue(s); textareaRef.current?.focus(); }}
              className="shrink-0 text-xs px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-600 rounded-full border border-slate-200 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder={placeholder ?? defaultPlaceholder}
          rows={1}
          disabled={loading}
          dir={isRTL ? 'rtl' : 'ltr'}
          className="flex-1 resize-none rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:opacity-50 transition-all"
        />

        <button
          onClick={handleSend}
          disabled={!value.trim() || loading}
          className="shrink-0 w-10 h-10 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed text-white flex items-center justify-center transition-colors"
        >
          {loading ? <Spinner className="w-4 h-4 text-white" /> : <Send className="w-4 h-4" />}
        </button>

        <button
          disabled
          title="Voice input (coming soon)"
          className="shrink-0 w-10 h-10 rounded-xl border border-slate-200 text-slate-400 flex items-center justify-center opacity-50 cursor-not-allowed"
        >
          <Mic className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
