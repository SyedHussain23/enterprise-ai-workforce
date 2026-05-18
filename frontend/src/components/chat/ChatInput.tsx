import { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import { Send, Mic, MicOff, Paperclip, X, FileText } from 'lucide-react';
import { Spinner } from '../shared/Spinner';

interface Props {
  onSend: (message: string, file?: File) => void;
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
  const [isListening, setIsListening] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const textareaRef  = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setVoiceSupported(!!(('SpeechRecognition' in window) || ('webkitSpeechRecognition' in window)));
  }, []);

  const defaultPlaceholder = isRTL
    ? 'اكتب سؤالك هنا... (اضغط Enter للإرسال)'
    : 'Ask HR, IT, or Finance anything... (Enter to send, Shift+Enter for newline)';

  const suggestions = isRTL ? SUGGESTIONS_AR : SUGGESTIONS_EN;
  const visibleSuggestions = showAll ? suggestions : suggestions.slice(0, 4);

  function toggleVoice() {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return;

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const recognition = new SR();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = isRTL ? 'ar-AE' : 'en-US';

    recognition.onresult = (event: any) => {
      const transcript = Array.from(event.results)
        .map((r: any) => r[0].transcript)
        .join('');
      setValue(transcript.slice(0, MAX_CHARS));
    };

    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    if (file) setAttachedFile(file);
    e.target.value = '';
  }

  function removeAttachment() {
    setAttachedFile(null);
  }

  function handleSend() {
    const trimmed = value.trim();
    if ((!trimmed && !attachedFile) || loading) return;
    const messageText = attachedFile
      ? (trimmed ? `[📎 ${attachedFile.name}]\n${trimmed}` : `[📎 ${attachedFile.name}]`)
      : trimmed;
    onSend(messageText, attachedFile ?? undefined);
    setValue('');
    setAttachedFile(null);
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

      {/* File attachment badge */}
      {attachedFile && (
        <div className="mb-2 flex items-center gap-2">
          <div className="flex items-center gap-1.5 bg-indigo-50 border border-indigo-200 rounded-lg px-2.5 py-1.5 text-xs text-indigo-700 font-medium">
            <FileText className="w-3.5 h-3.5" />
            <span className="max-w-[200px] truncate">{attachedFile.name}</span>
            <button
              onClick={removeAttachment}
              className="ml-1 hover:text-indigo-900 transition-colors"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
          {isListening && (
            <span className="text-xs text-red-500 animate-pulse">● Listening…</span>
          )}
        </div>
      )}

      {/* Listening indicator (no file attached) */}
      {isListening && !attachedFile && (
        <div className="mb-2">
          <span className="text-xs text-red-500 animate-pulse">● Listening…</span>
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.txt,.csv,.doc,.docx"
        className="hidden"
        onChange={handleFileChange}
      />

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

        {/* Attachment button */}
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
          title={isRTL ? 'إرفاق ملف' : 'Attach file'}
          className={`shrink-0 w-10 h-10 rounded-xl border transition-all flex items-center justify-center ${
            attachedFile
              ? 'border-indigo-400 bg-indigo-50 text-indigo-600'
              : 'border-slate-200 text-slate-400 hover:border-indigo-300 hover:text-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed'
          }`}
        >
          <Paperclip className="w-4 h-4" />
        </button>

        {/* Send button */}
        <button
          onClick={handleSend}
          disabled={(!value.trim() && !attachedFile) || loading || atLimit}
          title={isRTL ? 'إرسال' : 'Send (Enter)'}
          className="shrink-0 w-10 h-10 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed text-white flex items-center justify-center transition-all"
        >
          {loading ? <Spinner className="w-4 h-4 text-white" /> : <Send className="w-4 h-4" />}
        </button>

        {/* Voice input button */}
        {voiceSupported && (
          <button
            onClick={toggleVoice}
            disabled={loading}
            title={isListening ? (isRTL ? 'إيقاف الاستماع' : 'Stop listening') : (isRTL ? 'الإدخال الصوتي' : 'Voice input')}
            className={`shrink-0 w-10 h-10 rounded-xl border transition-all flex items-center justify-center ${
              isListening
                ? 'border-red-400 bg-red-50 text-red-500 animate-pulse'
                : 'border-slate-200 text-slate-400 hover:border-indigo-300 hover:text-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed'
            }`}
          >
            {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
          </button>
        )}
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
