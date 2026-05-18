import * as React from 'react';
import { User, Bot, BookOpen, ExternalLink, Link as LinkIcon } from 'lucide-react';
import type { Citation } from '../App';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  isError?: boolean;
}

const SOURCE_BADGE: Record<string, string> = {
  'arXiv':            'bg-red-50 text-red-600',
  'IEEE':             'bg-blue-50 text-blue-600',
  'Springer':         'bg-orange-50 text-orange-600',
  'Semantic Scholar': 'bg-green-50 text-green-600',
  'PubMed':           'bg-sky-50 text-sky-600',
  'CrossRef':         'bg-purple-50 text-purple-600',
};

export function ChatMessage({ role, content, citations, isError }: ChatMessageProps) {
  const isUser = role === 'user';

  return (
    <div className={`flex items-start gap-4 ${isUser ? 'justify-end' : ''}`}>
      {/* AI avatar */}
      {!isUser && (
        <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center shrink-0 shadow-md">
          <Bot size={20} className="text-white" />
        </div>
      )}

      <div className={`flex-1 max-w-3xl space-y-6 ${isUser ? 'flex flex-col items-end' : ''}`}>
        {/* Bubble */}
        <div className={`
          p-6 rounded-2xl shadow-sm border
          ${isUser
            ? 'bg-blue-50 border-blue-100 rounded-tr-none text-primary'
            : isError
              ? 'bg-red-50 border-red-100 rounded-tl-none text-red-700'
              : 'bg-white border-surface-container-high rounded-tl-none text-primary'
          }
        `}>
          <div className="text-sm leading-relaxed whitespace-pre-wrap">
            {content}
          </div>
        </div>

        {/* Citations grid — AI only */}
        {!isUser && citations && citations.length > 0 && (
          <div className="space-y-4">
            <p className="text-[11px] font-bold text-slate-400 tracking-widest uppercase flex items-center gap-2">
              <BookOpen size={14} />
              Grounded Citations ({citations.length})
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {citations.map((c, idx) => (
                <CitationCard key={idx} citation={c} />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="w-10 h-10 rounded-lg bg-surface-container-highest
                        flex items-center justify-center shrink-0 shadow-sm">
          <User size={20} className="text-primary" />
        </div>
      )}
    </div>
  );
}

function CitationCard({ citation }: { citation: Citation }) {
  const badgeClass = SOURCE_BADGE[citation.source] ?? 'bg-slate-50 text-slate-600';
  const url   = citation.url  || '#';
  const doiUrl = citation.doi ? `https://doi.org/${citation.doi}` : null;

  return (
    <div className="bg-white border-l-4 border-primary p-4 shadow-sm hover:shadow-md
                    transition-all group rounded-r-lg border-y border-r border-surface-container-high">
      {/* Title + badge */}
      <div className="flex justify-between items-start mb-2 gap-2">
        <h4 className="text-xs font-bold text-primary group-hover:text-tertiary
                       transition-colors line-clamp-2 flex-1">
          {citation.title}
        </h4>
        <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold shrink-0 ${badgeClass}`}>
          {citation.source}
        </span>
      </div>

      {/* Meta */}
      <p className="text-[10px] text-slate-500 mb-3">
        {citation.authors}
        {citation.year && ` · ${citation.year}`}
        {citation.citation_count > 0 && ` · 📊 ${citation.citation_count.toLocaleString()} citations`}
      </p>

      {/* Links */}
      <div className="flex gap-4">
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[10px] font-bold text-primary flex items-center gap-1
                     hover:underline underline-offset-2"
        >
          <ExternalLink size={10} />
          View Paper
        </a>
        {doiUrl && (
          <a
            href={doiUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[10px] font-bold text-primary flex items-center gap-1
                       hover:underline underline-offset-2"
          >
            <LinkIcon size={10} />
            DOI
          </a>
        )}
      </div>
    </div>
  );
}
