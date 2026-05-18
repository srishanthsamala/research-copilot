import * as React from 'react';
import { Library, ExternalLink, Download } from 'lucide-react';
import type { Paper } from '../App';

interface LibraryTabProps {
  papers: Paper[];
}

const SOURCE_BADGE: Record<string, string> = {
  'arXiv':            'bg-red-50 text-red-600',
  'IEEE':             'bg-blue-50 text-blue-600',
  'Springer':         'bg-orange-50 text-orange-600',
  'Semantic Scholar': 'bg-green-50 text-green-600',
  'PubMed':           'bg-sky-50 text-sky-600',
  'CrossRef':         'bg-purple-50 text-purple-600',
};

const SOURCE_BORDER: Record<string, string> = {
  'arXiv':            'border-l-red-500',
  'IEEE':             'border-l-blue-500',
  'Springer':         'border-l-orange-500',
  'Semantic Scholar': 'border-l-green-500',
  'PubMed':           'border-l-sky-400',
  'CrossRef':         'border-l-purple-500',
};

export function LibraryTab({ papers }: LibraryTabProps) {
  const [sourceFilter, setSourceFilter] = React.useState<string[]>([]);
  const [minCitations, setMinCitations] = React.useState(0);
  const [search, setSearch]             = React.useState('');
  const [sortBy, setSortBy]             = React.useState<'citations' | 'year'>('citations');

  const allSources = [...new Set(papers.map(p => p.source))];

  // Initialise filter to all sources on first load
  React.useEffect(() => {
    setSourceFilter(allSources);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [papers.length]);

  const toggleSource = (src: string) => {
    setSourceFilter(prev =>
      prev.includes(src) ? prev.filter(s => s !== src) : [...prev, src]
    );
  };

  const filtered = papers
    .filter(p =>
      (sourceFilter.length === 0 || sourceFilter.includes(p.source)) &&
      p.citation_count >= minCitations &&
      (search === '' ||
        p.title.toLowerCase().includes(search.toLowerCase()) ||
        p.authors.toLowerCase().includes(search.toLowerCase()))
    )
    .sort((a, b) =>
      sortBy === 'citations'
        ? b.citation_count - a.citation_count
        : parseInt(b.year || '0') - parseInt(a.year || '0')
    );

  const totalCitations = papers.reduce((s, p) => s + p.citation_count, 0);
  const topCited = papers.reduce((m, p) => p.citation_count > m ? p.citation_count : m, 0);

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(filtered, null, 2)], { type: 'application/json' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'papers.json'; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="p-10 max-w-5xl mx-auto w-full">

        {/* Header */}
        <div className="mb-8">
          <h3 className="text-3xl font-bold font-headline text-primary flex items-center gap-3 mb-1">
            <Library size={32} className="text-primary" />
            Fetched Papers Library
          </h3>
          <p className="text-slate-500 text-sm">
            All papers retrieved in this session, ranked by citation count.
          </p>
        </div>

        {/* Empty state */}
        {papers.length === 0 ? (
          <div className="text-center py-20 border-2 border-dashed border-surface-container-high rounded-2xl">
            <div className="text-4xl mb-3">📚</div>
            <p className="text-primary font-bold mb-1">Library is empty</p>
            <p className="text-slate-500 text-sm">Run a query to populate the library.</p>
          </div>
        ) : (
          <>
            {/* Stats bar */}
            <div className="grid grid-cols-4 gap-4 mb-8">
              {[
                { label: 'Papers',      value: papers.length.toString() },
                { label: 'Citations',   value: totalCitations.toLocaleString() },
                { label: 'Top Cited',   value: topCited.toLocaleString() },
                { label: 'Sources',     value: allSources.length.toString() },
              ].map(stat => (
                <div key={stat.label}
                     className="bg-white border border-surface-container-high
                                rounded-xl p-4 shadow-sm text-center">
                  <div className="text-2xl font-bold text-primary font-headline">
                    {stat.value}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-0.5">{stat.label}</div>
                </div>
              ))}
            </div>

            {/* Filters */}
            <div className="bg-white border border-surface-container-high rounded-xl p-5 mb-6 space-y-4">
              {/* Search */}
              <input
                type="text"
                placeholder="Search by title or author…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full border border-surface-container-high rounded-lg px-4 py-2
                           text-sm text-primary placeholder-slate-400 outline-none
                           focus:border-primary/30 transition-colors"
              />

              <div className="flex flex-wrap gap-4 items-center">
                {/* Source toggles */}
                <div className="flex flex-wrap gap-2">
                  {allSources.map(src => (
                    <button
                      key={src}
                      onClick={() => toggleSource(src)}
                      className={`text-[11px] font-bold px-2.5 py-1 rounded-full transition-all
                        ${sourceFilter.includes(src)
                          ? SOURCE_BADGE[src] ?? 'bg-slate-100 text-slate-600'
                          : 'bg-surface-container-high text-slate-400'}`}
                    >
                      {src}
                    </button>
                  ))}
                </div>

                {/* Min citations */}
                <div className="flex items-center gap-2 ml-auto">
                  <label className="text-[11px] text-slate-500 whitespace-nowrap">
                    Min citations:
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={minCitations}
                    onChange={e => setMinCitations(Math.max(0, parseInt(e.target.value) || 0))}
                    className="w-20 border border-surface-container-high rounded px-2 py-1
                               text-xs text-primary outline-none focus:border-primary/30"
                  />
                </div>

                {/* Sort */}
                <select
                  value={sortBy}
                  onChange={e => setSortBy(e.target.value as 'citations' | 'year')}
                  className="text-xs border border-surface-container-high rounded px-2 py-1
                             text-primary outline-none focus:border-primary/30 cursor-pointer"
                >
                  <option value="citations">Sort: Citations ↓</option>
                  <option value="year">Sort: Year ↓</option>
                </select>
              </div>
            </div>

            {/* Result count + export */}
            <div className="flex justify-between items-center mb-4">
              <p className="text-xs text-slate-500">
                Showing <span className="font-bold text-primary">{filtered.length}</span> of {papers.length} papers
              </p>
              <button
                onClick={exportJSON}
                className="flex items-center gap-2 text-xs font-bold text-primary
                           border border-surface-container-high rounded-lg px-3 py-1.5
                           hover:bg-surface transition-colors"
              >
                <Download size={12} />
                Export JSON
              </button>
            </div>

            {/* Paper cards */}
            <div className="space-y-3 pb-16">
              {filtered.map((p, i) => {
                const border = SOURCE_BORDER[p.source] ?? 'border-l-slate-400';
                const badge  = SOURCE_BADGE[p.source]  ?? 'bg-slate-50 text-slate-600';
                return (
                  <div
                    key={i}
                    className={`bg-white border-l-4 ${border} border-y border-r
                                border-surface-container-high rounded-r-xl p-5
                                hover:shadow-md transition-all group`}
                  >
                    <div className="flex justify-between items-start gap-4">
                      <div className="flex-1">
                        <div className="flex items-start gap-2 mb-1">
                          <span className="text-[10px] text-slate-400 font-bold shrink-0 mt-0.5">
                            #{i + 1}
                          </span>
                          <h4 className="text-sm font-bold text-primary
                                         group-hover:text-tertiary transition-colors">
                            {p.title}
                          </h4>
                        </div>
                        <p className="text-[11px] text-slate-500 ml-5">
                          {p.authors}
                          {p.year && ` · ${p.year}`}
                          {` · 📊 ${p.citation_count.toLocaleString()} citations`}
                        </p>
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${badge}`}>
                          {p.source}
                        </span>
                        {p.url && p.url !== '#' && (
                          <a
                            href={p.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-slate-400 hover:text-primary transition-colors"
                          >
                            <ExternalLink size={14} />
                          </a>
                        )}
                      </div>
                    </div>

                    {p.abstract && (
                      <p className="text-[11px] text-slate-500 mt-2 ml-5 line-clamp-2 leading-relaxed">
                        {p.abstract}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
