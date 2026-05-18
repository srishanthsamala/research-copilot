import * as React from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { ChatInput } from './components/ChatInput';
import { ChatMessage } from './components/ChatMessage';
import { CompareTab } from './components/CompareTab';
import { LibraryTab } from './components/LibraryTab';

// ── Types ────────────────────────────────────────────────────
export interface Citation {
  title: string;
  source: string;
  authors: string;
  year: string;
  doi?: string;
  url?: string;
  citation_count: number;
}

export interface Paper {
  title: string;
  source: string;
  authors: string;
  year: string;
  doi?: string;
  url?: string;
  citation_count: number;
  abstract?: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  isError?: boolean;
}

export type ActiveTab = 'query' | 'compare' | 'library';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';
const apiUrl = (path: string) => `${API_BASE_URL}${path}`;

// ── API helpers ──────────────────────────────────────────────
async function apiQuery(query: string, topK: number) {
  const res = await fetch(apiUrl('/api/query'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: topK }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function apiCompare(paperTitles: string[]) {
  const res = await fetch(apiUrl('/api/compare'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paper_titles: paperTitles }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function apiPapers(): Promise<{ papers: Paper[] }> {
  const res = await fetch(apiUrl('/api/papers'));
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function apiFetchCounts(): Promise<Record<string, number>> {
  const res = await fetch(apiUrl('/api/fetch-counts'));
  if (!res.ok) return {};
  return res.json();
}

async function apiNewChat() {
  const res = await fetch(apiUrl('/api/new-chat'), { method: 'POST' });
  return res.json();
}

async function apiClear() {
  await fetch(apiUrl('/api/clear'), { method: 'POST' });
}

// ── App ──────────────────────────────────────────────────────
export default function App() {
  const [activeTab, setActiveTab]       = React.useState<ActiveTab>('query');
  const [messages, setMessages]         = React.useState<Message[]>([]);
  const [isLoading, setIsLoading]       = React.useState(false);
  const [fetchCounts, setFetchCounts]   = React.useState<Record<string, number>>({});
  const [allPapers, setAllPapers]       = React.useState<Paper[]>([]);
  const [ragDepth, setRagDepth]         = React.useState(14);
  const [sessionNum, setSessionNum]     = React.useState(1);
  const [totalSessions, setTotalSessions] = React.useState(1);
  const [compareResult, setCompareResult] = React.useState('');
  const [compareLoading, setCompareLoading] = React.useState(false);

  const chatEndRef = React.useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  React.useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // ── Handle query send ──────────────────────────────────────
  const handleSend = async (query: string) => {
    if (!query.trim() || isLoading) return;

    setMessages(prev => [...prev, { role: 'user', content: query }]);
    setIsLoading(true);

    try {
      const data = await apiQuery(query, ragDepth);

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        citations: data.cited_papers as Citation[],
      }]);

      // Refresh sidebar counts + library
      setFetchCounts(data.fetch_counts ?? {});
      const papersData = await apiPapers();
      setAllPapers(papersData.papers);

    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `❌ Error: ${msg}\n\nCheck your API keys in config.py and make sure the backend is running.`,
        isError: true,
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  // ── Handle compare ─────────────────────────────────────────
  const handleCompare = async (selectedTitles: string[]) => {
    setCompareLoading(true);
    setCompareResult('');
    try {
      const data = await apiCompare(selectedTitles);
      setCompareResult(data.result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setCompareResult(`❌ Error: ${msg}`);
    } finally {
      setCompareLoading(false);
    }
  };

  // ── New chat ───────────────────────────────────────────────
  const handleNewChat = async () => {
    const data = await apiNewChat();
    setMessages([]);
    setCompareResult('');
    setSessionNum(data.session + 1);
    setTotalSessions(data.total_sessions);
  };

  // ── Clear chat ─────────────────────────────────────────────
  const handleClear = async () => {
    await apiClear();
    setMessages([]);
    setCompareResult('');
  };

  // ── Refresh library ────────────────────────────────────────
  const refreshLibrary = async () => {
    const [papersData, counts] = await Promise.all([apiPapers(), apiFetchCounts()]);
    setAllPapers(papersData.papers);
    setFetchCounts(counts);
  };

  // Refresh when switching to library tab
  React.useEffect(() => {
    if (activeTab === 'library') refreshLibrary();
  }, [activeTab]);

  return (
    <div className="flex min-h-screen bg-surface">
      {/* ── Sidebar ── */}
      <Sidebar
        fetchCounts={fetchCounts}
        ragDepth={ragDepth}
        onRagDepthChange={setRagDepth}
        onClear={handleClear}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onUploadReview={(review, title) => {
          setActiveTab('query');
          setMessages(prev => [...prev, {
            role: 'assistant',
            content: `## 📄 Paper Review: ${title}\n\n${review}`,
          }]);
        }}
      />

      {/* ── Main ── */}
      <main className="ml-72 flex-1 flex flex-col min-h-screen">
        <Header
          activeTab={activeTab}
          onTabChange={setActiveTab}
          sessionNum={sessionNum}
          totalSessions={totalSessions}
          onNewChat={handleNewChat}
        />

        {/* ── Query Tab ── */}
        {activeTab === 'query' && (
          <div className="flex-1 overflow-y-auto">
            <div className="p-10 max-w-5xl mx-auto w-full space-y-10">

              <ChatInput onSend={handleSend} isLoading={isLoading} />

              <hr className="border-surface-container-high" />

              {/* Empty state */}
              {messages.length === 0 && !isLoading && (
                <div className="text-center py-20">
                  <div className="text-5xl mb-4">🎓</div>
                  <h3 className="text-xl font-bold font-headline text-primary mb-2">
                    Your Research Session Awaits
                  </h3>
                  <p className="text-slate-500 text-sm max-w-md mx-auto leading-relaxed">
                    Ask any academic question above. The system will fetch live papers from{' '}
                    <span className="font-semibold text-primary">
                      arXiv · IEEE · Springer · Semantic Scholar · PubMed · CrossRef
                    </span>{' '}
                    and generate a grounded, citation-backed answer.
                  </p>
                </div>
              )}

              {/* Messages */}
              <section className="space-y-8 pb-24">
                {messages.map((msg, idx) => (
                  <ChatMessage
                    key={idx}
                    role={msg.role}
                    content={msg.content}
                    citations={msg.citations}
                    isError={msg.isError}
                  />
                ))}

                {/* Loading indicator */}
                {isLoading && (
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center shrink-0 shadow-md">
                      <span className="text-white text-lg">🤖</span>
                    </div>
                    <div className="bg-white border border-surface-container-high rounded-2xl rounded-tl-none p-6 shadow-sm">
                      <div className="flex items-center gap-3 text-slate-500 text-sm">
                        <span className="animate-spin text-lg">⟳</span>
                        <span>Fetching papers · Indexing · Generating answer…</span>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={chatEndRef} />
              </section>
            </div>
          </div>
        )}

        {/* ── Compare Tab ── */}
        {activeTab === 'compare' && (
          <CompareTab
            papers={allPapers}
            compareResult={compareResult}
            isLoading={compareLoading}
            onCompare={handleCompare}
          />
        )}

        {/* ── Library Tab ── */}
        {activeTab === 'library' && (
          <LibraryTab papers={allPapers} />
        )}
      </main>

      {/* ── Live Lab indicator ── */}
      <div className="fixed bottom-8 right-8 z-50">
        <div className="bg-white border border-primary/10 shadow-2xl rounded-full px-4 py-2 flex items-center gap-3">
          <div className="flex -space-x-2">
            <div className="w-6 h-6 rounded-full border-2 border-white bg-primary flex items-center justify-center text-white text-[10px]">A</div>
            <div className="w-6 h-6 rounded-full border-2 border-white bg-tertiary flex items-center justify-center text-white text-[10px]">R</div>
          </div>
          <span className="text-[10px] font-bold text-primary uppercase tracking-tighter">Live Lab Mode</span>
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
        </div>
      </div>
    </div>
  );
}
