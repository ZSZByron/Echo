import { useState } from 'react';

export interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  text: string;
  timestamp?: Date;
}

export interface GuidedChatProps {
  messages: Message[];
  onSend: (text: string) => void;
  disabled?: boolean;
}

export function GuidedChat({ messages, onSend, disabled = false }: GuidedChatProps) {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-950">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.type === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-2xl rounded-lg px-4 py-3 ${
                message.type === 'user'
                  ? 'bg-indigo-600 text-white'
                  : message.type === 'system'
                  ? 'bg-slate-800 text-slate-300 text-sm border border-slate-700'
                  : 'bg-slate-800 text-slate-100 border border-slate-700'
              }`}
            >
              {message.text}
            </div>
          </div>
        ))}
        {disabled && (
          <div className="text-center text-slate-500 text-sm py-2">
            Processing...
          </div>
        )}
      </div>

      {/* Input area */}
      <form onSubmit={handleSubmit} className="border-t border-slate-800 p-4">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={disabled}
            placeholder="Type your message..."
            className="flex-1 bg-slate-900 text-white placeholder-slate-500 rounded-lg px-4 py-3 border border-slate-700 focus:border-indigo-500 focus:outline-none disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={disabled || !input.trim()}
            className="bg-indigo-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
