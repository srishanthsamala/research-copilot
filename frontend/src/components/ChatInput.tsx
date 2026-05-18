import * as React from 'react';
import { Rocket, MessageSquare, ShieldCheck, Loader2 } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading?: boolean;
}

export function ChatInput({ onSend, isLoading = false }: ChatInputProps) {
  const [input, setInput] = React.useState('');

  const handleSend = () => {
    if (input.trim() && !isLoading) {
      onSend(input.trim());
      setInput('');
    }
  };

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-1">
        <h3 className="text-3xl font-bold font-headline text-primary flex items-center gap-3">
          <MessageSquare size={32} className="text-primary" />
          Ask a Research Question
        </h3>
        <p className="text-slate-500 font-medium flex items-center gap-2 text-sm">
          <ShieldCheck size={16} className="text-tertiary" />
          Answers come only from fetched research papers — no hallucination
        </p>
      </div>

      <div className="relative group">
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          disabled={isLoading}
          className="w-full h-36 p-6 bg-white border-2 border-transparent
                     focus:border-primary/20 rounded-2xl shadow-sm resize-none
                     text-primary placeholder:text-slate-400 outline-none
                     transition-all text-sm leading-relaxed
                     disabled:opacity-60 disabled:cursor-not-allowed"
          placeholder="E.g., What are the current limitations of Transformer models in processing long-context sequences within medical datasets?"
        />
        <div className="absolute bottom-4 right-4">
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="bg-primary text-white flex items-center gap-2 px-6 py-3
                       rounded-xl font-bold shadow-lg hover:shadow-primary/20
                       hover:bg-primary-container active:scale-95 transition-all
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading
              ? <><Loader2 size={16} className="animate-spin" /> Thinking…</>
              : <><Rocket size={18} /> Ask Co-Pilot</>
            }
          </button>
        </div>
      </div>
    </section>
  );
}
