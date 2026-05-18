import * as React from 'react';
import { FileDiff, Loader2, Download } from 'lucide-react';
import type { Paper } from '../App';

interface CompareTabProps {
  papers: Paper[];
  compareResult: string;
  isLoading: boolean;
  onCompare: (titles: string[]) => void;
}

const SOURCE_BORDER: Record<string, string> = {
  'arXiv':            'border-l-red-500',
  'IEEE':             'border-l-blue-500',
  'Springer':         'border-l-orange-500',
  'Semantic Scholar': 'border-l-green-500',
  'PubMed':           'border-l-sky-400',
  'CrossRef':         'border-l-purple-500',
};

const SOURCE_BADGE: Record<string, string> = {
  'arXiv':            'bg-red-50 text-red-600',
  'IEEE':             'bg-blue-50 text-blue-600',
  'Springer':         'bg-orange-50 text-orange-600',
  'Semantic Scholar': 'bg-green-50 text-green-600',
  'PubMed':           'bg-sky-50 text-sky-600',
  'CrossRef':         'bg-purple-50 text-purple-600',
};

// Very simple markdown-to-JSX renderer for the analysis result
function RenderMarkdown({ text }: { text: string }) {
  const lines = text.split('\n');
  return (
    <div className="space-y-2 text-sm leading-relaxed text-primary">
      {lines.map((line, i) => {
        if (line.startsWith('### ')) {
          return <h4 key={i} className="text-primary font-bold text-sm mt-5 mb-1 font-headline">{line.slice(4)}</h4>;
        }
        if (line.startsWith('## ')) {
          return <h3 key={i} className="text-primary font-bold text-base mt-6 mb-2 font-headline">{line.slice(3)}</h3>;
        }
        if (line.startsWith('# ')) {
          return <h2 key={i} className="text-primary font-bold text-lg mt-6 mb-2 font-headline">{line.slice(2)}</h2>;
        }
        if (line.startsWith('- ') || line.startsWith('* ')) {
          return (
            <div key={i} className="flex gap-2 ml-4">
              <span className="text-tertiary mt-1">•</span>
              <span>{line.slice(2)}</span>
            </div>
          );
        }
        if (line.trim() === '' || line === '---') {
          return <div key={i} className="h-2" />;
        }
        // Inline bold **text**
        const parts = line.split(/(\*\*[^*]+\*\*)/g);
        return (
          <p key={i}>
            {parts.map((part, j) =>
              part.startsWith('**') && part.endsWith('**')
                ? <strong key={j} className="font-bold text-primary">{part.slice(2, -2)}</strong>
                : part
            )}
          </p>
        );
      })}
    </div>
  );
}

export function CompareTab({ papers, compareResult, isLoading, onCompare }: CompareTabProps) {
  const [selected, setSelected] = React.useState<string[]>([]);

  const togglePaper = (title: string) => {
    setSelected(prev =>
      prev.includes(title)
        ? prev.filter(t => t !== title)
        : prev.length < 5
          ? [...prev, title]
          : prev
    );
  };

  const downloadResult = () => {
    const blob = new Blob([compareResult], { type: 'text/markdown' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'comparison.md'; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="p-10 max-w-5xl mx-auto w-full">

        {/* Header */}
        <div className="mb-8">
          <h3 className="text-3xl font-bold font-headline text-primary flex items-center gap-3 mb-1">
            <FileDiff size={32} className="text-primary" />
            Compare Papers
          </h3>
          <p className="text-slate-500 text-sm">
            Select 2–5 papers fetched in this session to compare side-by-side.
          </p>
        </div>

        {/* No papers yet */}
        {papers.length === 0 ? (
          <div className="text-center py-20 border-2 border-dashed border-surface-container-high rounded-2xl">
            <div className="text-4xl mb-3">📄</div>
            <p className="text-primary font-bold mb-1">No papers fetched yet</p>
            <p className="text-slate-500 text-sm">Run a query in the Research Query tab first.</p>
          </div>
        ) : (
          <>
            {/* Paper selection grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
              {papers.map(p => {
                const isSelected = selected.includes(p.title);
                const borderColor = SOURCE_BORDER[p.source] ?? 'border-l-slate-400';
                const badgeClass  = SOURCE_BADGE[p.source]  ?? 'bg-slate-50 text-slate-600';
                return (
                  <button
                    key={p.title}
                    onClick={() => togglePaper(p.title)}
                    className={`
                      text-left p-4 rounded-xl border-l-4 border transition-all
                      ${borderColor}
                      ${isSelected
                        ? 'bg-primary/5 border-t-primary/20 border-r-primary/20 border-b-primary/20 shadow-md'
                        : 'bg-white border-t-surface-container-high border-r-surface-container-high border-b-surface-container-high hover:shadow-sm'}
                    `}
                  >
                    <div className="flex justify-between items-start gap-2 mb-1">
                      <p className="text-xs font-bold text-primary line-clamp-2 flex-1">
                        {p.title}
                      </p>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${badgeClass}`}>
                          {p.source}
                        </span>
                        <div className={`w-4 h-4 rounded border-2 flex items-center justify-center
                          ${isSelected ? 'bg-primary border-primary' : 'border-slate-300'}`}>
                          {isSelected && <span className="text-white text-[10px]">✓</span>}
                        </div>
                      </div>
                    </div>
                    <p className="text-[10px] text-slate-500">
                      {p.authors} · {p.year} · 📊 {p.citation_count.toLocaleString()} citations
                    </p>
                  </button>
                );
              })}
            </div>

            {/* Selection counter + button */}
            <div className="flex items-center justify-between mb-8">
              <p className="text-sm text-slate-500">
                {selected.length === 0
                  ? 'Select at least 2 papers to compare'
                  : `${selected.length} paper${selected.length > 1 ? 's' : ''} selected`}
              </p>
              <button
                onClick={() => onCompare(selected)}
                disabled={selected.length < 2 || isLoading}
                className="bg-primary text-white text-sm font-bold px-8 py-3 rounded-xl
                           shadow-lg hover:bg-primary-container active:scale-95 transition-all
                           disabled:opacity-40 disabled:cursor-not-allowed
                           flex items-center gap-2"
              >
                {isLoading
                  ? <><Loader2 size={16} className="animate-spin" /> Comparing…</>
                  : '⚡ Generate Comparison'
                }
              </button>
            </div>

            {/* Result */}
            {compareResult && !isLoading && (
              <div className="bg-white border border-surface-container-high rounded-2xl
                              shadow-sm overflow-hidden">
                {/* Result header */}
                <div className="flex items-center justify-between px-8 py-5
                                border-b border-surface-container-high">
                  <h4 className="font-bold text-primary font-headline text-base">
                    🔬 Detailed AI Analysis
                  </h4>
                  <button
                    onClick={downloadResult}
                    className="flex items-center gap-2 text-xs font-bold text-primary
                               border border-surface-container-high rounded-lg px-3 py-1.5
                               hover:bg-surface transition-colors"
                  >
                    <Download size={12} />
                    Download .md
                  </button>
                </div>

                {/* Comparison summary table */}
                <div className="px-8 pt-6 pb-4 overflow-x-auto">
                  <table className="w-full text-xs border-collapse mb-6">
                    <thead>
                      <tr className="bg-primary text-white">
                        <th className="text-left px-4 py-2 rounded-tl-lg font-bold">Title</th>
                        <th className="text-left px-4 py-2 font-bold">Year</th>
                        <th className="text-left px-4 py-2 font-bold">Source</th>
                        <th className="text-right px-4 py-2 rounded-tr-lg font-bold">Citations</th>
                      </tr>
                    </thead>
                    <tbody>
                      {papers
                        .filter(p => selected.includes(p.title))
                        .map((p, i) => (
                          <tr key={i} className={i % 2 === 0 ? 'bg-surface' : 'bg-white'}>
                            <td className="px-4 py-2 text-primary font-medium max-w-xs">
                              {p.title.length > 60 ? p.title.slice(0, 60) + '…' : p.title}
                            </td>
                            <td className="px-4 py-2 text-slate-600">{p.year}</td>
                            <td className="px-4 py-2">
                              <span className={`px-1.5 py-0.5 rounded font-bold text-[10px]
                                ${SOURCE_BADGE[p.source] ?? 'bg-slate-50 text-slate-600'}`}>
                                {p.source}
                              </span>
                            </td>
                            <td className="px-4 py-2 text-right text-slate-600">
                              {p.citation_count.toLocaleString()}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>

                {/* AI analysis text */}
                <div className="px-8 pb-8">
                  <RenderMarkdown text={compareResult} />
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
