import { useState } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import type { Message } from '../../api/types';
import { AgentTrace } from './AgentTrace';
import { submitFeedback } from '../../api/client';

interface Props {
  message: Message;
  isRTL?: boolean;
}

function renderMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n- /g, '</p><ul><li>')
    .replace(/\n(\d+)\. /g, '</p><ol><li>')
    .replace(/\n/g, '<br/>');
}

export function MessageBubble({ message, isRTL }: Props) {
  const isUser = message.role === 'user';
  const [rated, setRated] = useState<'up' | 'down' | null>(null);

  async function handleRating(rating: 'up' | 'down') {
    if (!message.metadata?.action_id && !message.id) return;
    if (rated) return;
    setRated(rating);

    if (message.metadata) {
      try {
        await submitFeedback({
          workflow_log_id: message.id,
          rating: rating === 'up' ? 5 : 1,
        });
      } catch {
        // silent
      }
    }
  }

  if (isUser) {
    return (
      <div className={`flex ${isRTL ? 'justify-start' : 'justify-end'} animate-slide-in`}>
        <div className="max-w-[75%] bg-indigo-600 text-white px-4 py-2.5 rounded-2xl rounded-br-sm text-sm leading-relaxed">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start animate-slide-in">
      <div className="max-w-[85%] space-y-1">
        {/* Avatar row */}
        <div className="flex items-center gap-2 mb-1">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold">
            AI
          </div>
          <span className="text-xs text-slate-400">
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>

        {/* Content bubble */}
        <div className="bg-white border border-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
          {message.streaming ? (
            <div className="text-sm text-slate-700 leading-relaxed">
              <span>{message.content}</span>
              <span className="cursor-blink text-indigo-500 font-bold">▋</span>
            </div>
          ) : (
            <div
              className="prose-agent text-sm text-slate-700 leading-relaxed"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
            />
          )}

          {/* Agent trace */}
          {!message.streaming && message.metadata && (
            <AgentTrace metadata={message.metadata} />
          )}
        </div>

        {/* Feedback buttons */}
        {!message.streaming && message.metadata && (
          <div className="flex items-center gap-1 px-1">
            <button
              onClick={() => handleRating('up')}
              className={`p-1 rounded transition-colors ${rated === 'up' ? 'text-emerald-600' : 'text-slate-300 hover:text-slate-500'}`}
            >
              <ThumbsUp className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => handleRating('down')}
              className={`p-1 rounded transition-colors ${rated === 'down' ? 'text-red-500' : 'text-slate-300 hover:text-slate-500'}`}
            >
              <ThumbsDown className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
