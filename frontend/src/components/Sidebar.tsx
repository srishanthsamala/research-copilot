import * as React from 'react';
import {
  Search,
  FileDiff,
  Library,
  UploadCloud,
  Trash2,
  GraduationCap,
  Loader2,
} from 'lucide-react';
import type { ActiveTab } from '../App';

interface SidebarProps {
  fetchCounts: Record<string, number>;
  ragDepth: number;
  onRagDepthChange: (v: number) => void;
  onClear: () => void;
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  onUploadReview: (review: string, title: string) => void;
}

const SOURCE_COLORS: Record<string, string> = {
  'arXiv':            'bg-red-500',
  'IEEE':             'bg-blue-500',
  'Springer':         'bg-orange-500',
  'Semantic Scholar': 'bg-green-500',
  'PubMed':           'bg-slate-400',
  'CrossRef':         'bg-purple-500',
};

const ALL_SOURCES = ['arXiv', 'IEEE', 'Springer', 'Semantic Scholar', 'PubMed', 'CrossRef'];

const NAV_ITEMS: { id: ActiveTab; icon: React.ReactNode; label: string }[] = [
  { id: 'query',   icon: <Search size={18} />,   label: 'Research Query'  },
  { id: 'compare', icon: <FileDiff size={18} />, label: 'Compare Papers'  },
  { id: 'library', icon: <Library size={18} />,  label: 'Fetched Papers'  },
];

export function Sidebar({
  fetchCounts,
  ragDepth,
  onRagDepthChange,
  onClear,
  activeTab,
  onTabChange,
  onUploadReview,
}: SidebarProps) {
  const [uploading, setUploading]   = React.useState(false);
  const [question, setQuestion]     = React.useState('');
  const [uploadedFile, setUploadedFile] = React.useState<File | null>(null);
  const [uploadError, setUploadError]  = React.useState('');
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const total   = Object.values(fetchCounts).reduce((a, b) => a + b, 0);
  const indexed = total; // backend indexes all fetched papers

  // ── PDF Upload ─────────────────────────────────────────────
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    setUploadedFile(f);
    setUploadError('');
  };

  const handleReview = async () => {
    if (!uploadedFile) return;
    setUploading(true);
    setUploadError('');
    try {
      const form = new FormData();
      form.append('file', uploadedFile);
      form.append('question', question);
      const res = await fetch('/api/upload-paper', { method: 'POST', body: form });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      onUploadReview(data.review, data.title ?? uploadedFile.name);
      // Reset
      setUploadedFile(null);
      setQuestion('');
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setUploadError(msg);
    } finally {
      setUploading(false);
    }
  };

  return (
    <aside className="fixed inset-y-0 left-0 flex flex-col z-40 bg-primary w-72 text-white/90">
      <div className="p-6 flex-1 overflow-y-auto">

        {/* ── Logo ── */}
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 bg-tertiary rounded-lg flex items-center justify-center text-white shadow-lg">
            <GraduationCap size={24} />
          </div>
          <div>
            <h1 className="text-[14px] font-bold tracking-tight text-white uppercase leading-none font-headline">
              Research Co-Pilot
            </h1>
            <p className="text-[10px] font-bold text-slate-400 tracking-widest uppercase mt-1">
              The Intellectual Ledger
            </p>
          </div>
        </div>

        {/* ── Papers Fetched metrics ── */}
        <div className="mb-8">
          <p className="text-[11px] font-bold text-slate-400 tracking-widest uppercase mb-4">
            Papers Fetched
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-white/5 p-3 rounded-lg">
              <span className="text-2xl font-bold text-white">{total}</span>
              <p className="text-[10px] text-slate-400 mt-0.5">Total</p>
            </div>
            <div className="bg-white/5 p-3 rounded-lg border-l-2 border-tertiary">
              <span className="text-2xl font-bold text-white">{indexed}</span>
              <p className="text-[10px] text-slate-400 mt-0.5">Indexed</p>
            </div>
          </div>
        </div>

        {/* ── Navigation ── */}
        <nav className="space-y-1 mb-8">
          {NAV_ITEMS.map(item => (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`
                w-full flex items-center gap-3 px-4 py-3 transition-all text-left
                ${activeTab === item.id
                  ? 'text-white font-bold border-r-4 border-tertiary bg-white/5'
                  : 'text-slate-400 font-medium hover:text-white hover:bg-white/5'}
              `}
            >
              {item.icon}
              <span className="text-sm">{item.label}</span>
            </button>
          ))}
        </nav>

        {/* ── Sources ── */}
        <div className="mb-8">
          <p className="text-[11px] font-bold text-slate-400 tracking-widest uppercase mb-3">
            Sources
          </p>
          <div className="space-y-2">
            {ALL_SOURCES.map(src => {
              const count = fetchCounts[src] ?? 0;
              const color = SOURCE_COLORS[src] ?? 'bg-slate-400';
              return (
                <div
                  key={src}
                  className={`flex items-center justify-between px-3 py-1.5 bg-white/5
                              rounded border-l-4 ${color}`}
                >
                  <span className="text-xs text-white">{src}</span>
                  <span className="text-[10px] bg-white/10 px-1.5 py-0.5 rounded text-slate-300 font-bold">
                    {String(count).padStart(2, '0')}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Upload ── */}
        <div className="mb-8">
          <p className="text-[11px] font-bold text-slate-400 tracking-widest uppercase mb-3">
            Upload Your Paper
          </p>

          {/* Drop zone */}
          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-white/15 rounded-lg p-4 text-center
                       hover:border-white/30 transition-colors cursor-pointer mb-2 group"
          >
            <UploadCloud size={20} className="mx-auto text-slate-400 mb-2 group-hover:text-white transition-colors" />
            {uploadedFile
              ? <p className="text-[11px] text-white font-semibold truncate">{uploadedFile.name}</p>
              : <p className="text-[10px] text-slate-400">Drag PDF here or click to browse</p>
            }
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>

          {/* Optional question */}
          {uploadedFile && (
            <input
              type="text"
              value={question}
              onChange={e => setQuestion(e.target.value)}
              placeholder="Question (optional)"
              className="w-full bg-white/5 border border-white/10 rounded px-3 py-2
                         text-xs text-white placeholder-slate-500 outline-none
                         focus:border-white/25 transition-colors mb-2"
            />
          )}

          {uploadError && (
            <p className="text-[10px] text-red-400 mb-2">{uploadError}</p>
          )}

          <button
            onClick={handleReview}
            disabled={!uploadedFile || uploading}
            className="w-full bg-tertiary text-white text-xs font-bold py-2.5 rounded
                       hover:bg-tertiary/90 transition-all active:scale-[0.98]
                       disabled:opacity-40 disabled:cursor-not-allowed
                       flex items-center justify-center gap-2"
          >
            {uploading
              ? <><Loader2 size={14} className="animate-spin" /> Analysing…</>
              : 'Review Paper'
            }
          </button>
        </div>
      </div>

      {/* ── Footer ── */}
      <div className="p-6 space-y-2 border-t border-white/5 bg-primary/50">
        <div className="mb-4">
          <div className="flex justify-between text-[10px] text-slate-400 mb-2">
            <span>RAG Depth</span>
            <span className="text-white font-bold">{ragDepth}</span>
          </div>
          <input
            type="range"
            min="4"
            max="20"
            value={ragDepth}
            onChange={e => onRagDepthChange(parseInt(e.target.value))}
            className="w-full h-1 rounded-full appearance-none cursor-pointer
                       accent-tertiary bg-white/10"
          />
          <p className="text-[9px] text-slate-500 mt-1">
            Higher = more paper chunks retrieved per query
          </p>
        </div>

        <button
          onClick={onClear}
          className="flex items-center gap-3 text-slate-400 font-medium
                     hover:text-red-400 transition-colors py-2 w-full text-left"
        >
          <Trash2 size={16} />
          <span className="text-xs">Clear Chat</span>
        </button>
      </div>
    </aside>
  );
}
