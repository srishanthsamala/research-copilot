import * as React from 'react';
import { Plus } from 'lucide-react';
import type { ActiveTab } from '../App';

interface HeaderProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  sessionNum: number;
  totalSessions: number;
  onNewChat: () => void;
}

const TABS: { id: ActiveTab; label: string }[] = [
  { id: 'query',   label: 'Query'   },
  { id: 'compare', label: 'Compare' },
  { id: 'library', label: 'Library' },
];

export function Header({ activeTab, onTabChange, sessionNum, onNewChat }: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 shadow-lg shadow-primary/10"
            style={{ background: 'linear-gradient(90deg, #001f41 0%, #0f3460 100%)' }}>
      <div className="flex justify-between items-center w-full px-8 py-4">
        {/* Left — title + tabs */}
        <div className="flex items-center gap-8">
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight font-headline">
              Academic Research Co-Pilot
            </h2>
            <p className="text-[11px] text-slate-300 flex items-center gap-2">
              <span>RAG-powered</span> · <span>Citation-grounded</span> · <span>Hallucination-free</span>
            </p>
          </div>

          {/* Tab links */}
          <nav className="flex gap-1">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`
                  text-xs uppercase tracking-widest font-bold px-4 py-2 transition-all
                  ${activeTab === tab.id
                    ? 'text-white border-b-2 border-tertiary'
                    : 'text-slate-400 hover:text-white border-b-2 border-transparent'}
                `}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Right — badge + session + new chat */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3">
            <span className="bg-tertiary text-[10px] font-bold text-white px-2.5 py-0.5 rounded-full uppercase tracking-tighter">
              RAG v1.0
            </span>
            <span className="text-[10px] text-slate-300 font-mono opacity-60">
              SES: {String(sessionNum).padStart(4, '0')}-XP
            </span>
          </div>

          <div className="border-l border-white/10 pl-6">
            <button
              onClick={onNewChat}
              className="bg-white/10 text-white text-xs font-bold px-4 py-2 rounded-full
                         hover:bg-white/20 active:scale-95 transition-all flex items-center gap-2"
            >
              <Plus size={14} />
              New Chat
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
