import { useState, useRef, useEffect, useCallback, type KeyboardEvent } from 'react';
import { Send, Mic, MicOff, Paperclip, X, FileText, Square } from 'lucide-react';
import { Spinner } from '../shared/Spinner';

interface Props {
  onSend: (message: string, file?: File) => void;
  onStop?: () => void;
  loading: boolean;
  isStreaming?: boolean;
  isRTL?: boolean;
  placeholder?: string;
  disabled?: boolean;
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

const ACCEPTED_TYPES = '.pdf,.txt,.csv,.doc,.docx';
const MAX_FILE_MB = 5;

export function ChatInput({ onSend, onStop, loading, isStreaming, isRTL, placeholder, disabled }: Props) {
  const [value, setValue]             = useState('');
  const [showAll, setShowAll]         = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [voiceSupported, setVoice]    = useState(false);
  const [attachedFile, setFile]       = useState<File | null>(null);
  const [fileError, setFileError]     = useState('');
  const [isDragOver, setDragOver]     = useState(false);
  const textareaRef  = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const formRef      = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setVoice(!!(('SpeechRecognition' in window) || ('webkitSpeechRecognition' in window)));
  }, []);

  // Auto-focus on mount (desktop only — avoids keyboard pop on mobile)
  useEffect(() => {
    if (window.innerWidth >= 768) textareaRef.current?.focus();
  }, []);

  const suggestions = isRTL ? SUGGESTIONS_AR : SUGGESTIONS_EN;
  const visible     = showAll ? suggestions : suggestions.slice(0, 4);

  const adjustHeight = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, []);

  function validateFile(file: File): string | null {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    const accepted = ACCEPTED_TYPES.split(',');
    if (!accepted.includes(ext)) return `Unsupported file type. Use: ${ACCEPTED_TYPES}`;
    if (file.size > MAX_FILE_MB * 1024 * 1024) return `File too large (max ${MAX_FILE_MB}MB)`;
    return null;
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    if (!file) return;
    const err = validateFile(file);
    if (err) { setFileError(err); return; }
    setFile(file);
    setFileError('');
    e.target.value = '';
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (!file) return;
    const err = validateFile(file);
    if (err) { setFileError(err); return; }
    setFile(file);
    setFileError('');
  }

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
      adjustHeight();
    };
    recognition.onerror = () => setIsListening(false);
    recognition.onend   = () => setIsListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  }

  function handleSend() {
    const trimmed = value.trim();
    if ((!trimmed && !attachedFile) || loading || disabled) return;
    onSend(trimmed, attachedFile ?? undefined);
    setValue('');
    setFile(null);
    setFileError('');
    setShowAll(false);
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (isStreaming && onStop) { onStop(); return; }
      handleSend();
    }
    if (e.key === 'Escape' && isStreaming && onStop) {
      onStop();
    }
  }

  const remaining = MAX_CHARS - value.length;
  const nearLimit = remaining < 200;
  const atLimit   = remaining <= 0;

  return (
    <div
      ref={formRef}
      className={`border-t border-slate-100 bg-white px-3 py-3 md:px-4 ${isDragOver ? 'bg-indigo-50/50' : ''} transition-colors`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      {/* Drag-over indicator */}
      {isDragOver && (
        <div className="absolute inset-0 border-2 border-dashed border-indigo-400 rounded-xl pointer-events-none flex items-center justify-center bg-indigo-50/80 z-10">
          <p className="text-sm font-medium text-indigo-600">Drop file to attach</p>
        </div>
      )}

      {/* Quick suggestions */}
      {!value && !attachedFile && (
        <div className="mb-2.5">
          <div className="flex flex-wrap gap-1.5">
            {visible.map((s) => (
              <button
                key={s}
                onClick={() => { setValue(s); setShowAll(false); setTimeout(() => textareaRef.current?.focus(), 0); }}
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
                {showAll ? (isRTL ? 'أقل' : 'Less') : (isRTL ? 'المزيد…' : 'More…')}
              </button>
            )}
          </div>
        </div>
      )}

      {/* File attachment badge */}
      {attachedFile && (
        <div className="mb-2 flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1.5 bg-indigo-50 border border-indigo-200 rounded-lg px-2.5 py-1.5 text-xs text-indigo-700 font-medium">
            <FileText className="w-3.5 h-3.5 shrink-0" />
            <span className="max-w-[200px] truncate">{attachedFile.name}</span>
            <span className="text-indigo-400">({(attachedFile.size / 1024).toFixed(0)}KB)</span>
            <button onClick={() => setFile(null)} className="ml-1 hover:text-indigo-900">
              <X className="w-3 h-3" />
            </button>
          </div>
          {isListening && (
            <span className="text-xs text-red-500 animate-pulse">● Listening…</span>
          )}
        </div>
      )}

      {/* File error */}
      {fileError && (
        <div className="mb-2 text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-1.5 flex items-center gap-2">
          <X className="w-3 h-3 shrink-0" />
          {fileError}
          <button onClick={() => setFileError('')} className="ml-auto text-red-400">Dismiss</button>
        </div>
      )}

      {/* Listening indicator */}
      {isListening && !attachedFile && (
        <div className="mb-2">
          <span className="text-xs text-red-500 animate-pulse flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
            Listening… speak now
          </span>
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED_TYPES}
        className="hidden"
        onChange={handleFileChange}
      />

      <div className="flex items-end gap-2">
        {/* Textarea */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => { setValue(e.target.value.slice(0, MAX_CHARS)); adjustHeight(); }}
            onKeyDown={handleKeyDown}
            onInput={adjustHeight}
            placeholder={placeholder ?? (isRTL
              ? 'اكتب سؤالك هنا… (Enter للإرسال)'
              : 'Ask HR, IT, or Finance anything… (Enter to send)'
            )}
            rows={1}
            disabled={disabled}
            dir={isRTL ? 'rtl' : 'ltr'}
            className="w-full resize-none rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:opacity-50 transition-all leading-relaxed"
            style={{ minHeight: '44px' }}
          />
          {/* Char counter */}
          {value.length > 0 && (
            <span className={`absolute bottom-2 right-3 text-[10px] select-none pointer-events-none ${
              atLimit ? 'text-red-500 font-semibold' : nearLimit ? 'text-amber-500' : 'text-slate-300'
            }`}>
              {remaining}
            </span>
          )}
        </div>

        {/* Attachment */}
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={loading || disabled}
          title={isRTL ? 'إرفاق ملف' : 'Attach file (PDF, TXT, DOCX, CSV)'}
          className={`shrink-0 w-10 h-10 rounded-xl border transition-all flex items-center justify-center ${
            attachedFile
              ? 'border-indigo-400 bg-indigo-50 text-indigo-600'
              : 'border-slate-200 text-slate-400 hover:border-indigo-300 hover:text-indigo-500 disabled:opacity-40'
          }`}
        >
          <Paperclip className="w-4 h-4" />
        </button>

        {/* Stop / Send button */}
        {isStreaming && onStop ? (
          <button
            onClick={onStop}
            title="Stop generation (Esc)"
            className="shrink-0 w-10 h-10 rounded-xl bg-slate-700 hover:bg-slate-900 text-white flex items-center justify-center transition-all active:scale-95"
          >
            <Square className="w-4 h-4 fill-current" />
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={(!value.trim() && !attachedFile) || loading || atLimit || disabled}
            title={isRTL ? 'إرسال' : 'Send (Enter)'}
            className="shrink-0 w-10 h-10 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed text-white flex items-center justify-center transition-all"
          >
            {loading ? <Spinner className="w-4 h-4 text-white" /> : <Send className="w-4 h-4" />}
          </button>
        )}

        {/* Voice */}
        {voiceSupported && (
          <button
            onClick={toggleVoice}
            disabled={loading || disabled}
            title={isListening ? 'Stop listening' : 'Voice input'}
            className={`shrink-0 w-10 h-10 rounded-xl border transition-all flex items-center justify-center ${
              isListening
                ? 'border-red-400 bg-red-50 text-red-500'
                : 'border-slate-200 text-slate-400 hover:border-indigo-300 hover:text-indigo-500 disabled:opacity-40'
            }`}
          >
            {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
          </button>
        )}
      </div>

      {/* Keyboard hint — desktop only */}
      <p className="hidden md:block mt-1.5 text-[10px] text-slate-300 text-center select-none">
        {isStreaming
          ? 'Press Esc or ■ to stop generation'
          : 'Enter to send · Shift+Enter for new line · Drag & drop files'
        }
      </p>
    </div>
  );
}
