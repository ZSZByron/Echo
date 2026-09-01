import { useState } from 'react';
import '../theme.css';
import type { A1Proposal } from '../../types/a1';
import { ProposalCard } from './ProposalCard';
import { ProposalTray } from './ProposalTray';

export interface DiceRecommendation {
  field: string;
  value: string;
  reason: string;
}

export interface DiceRecommendationResponse {
  recommendations: DiceRecommendation[];
  summary: string;
}

export interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  text: string;
  timestamp?: Date;
  diceRecommendation?: DiceRecommendationResponse;
}

export interface GuidedChatProps {
  messages: Message[];
  onSend: (text: string) => void;
  disabled?: boolean;
  /** Pending proposals from backend response */
  proposals?: A1Proposal[];
  /** Session ID for proposal API calls */
  sessionId?: string;
  /** Callback when proposal is resolved */
  onProposalResolved?: (key: string) => void;
}

function DiceRecommendationCard({ recommendation }: { recommendation: DiceRecommendationResponse }) {
  return (
    <div className="glass-panel mt-3 p-4 border border-nebula-400/20">
      <div className="text-stardust-300 text-sm font-medium mb-3">
        🎲 Dice Recommendations
      </div>
      <div className="text-gray-300 text-xs mb-3 italic">
        {recommendation.summary}
      </div>
      <div className="space-y-2">
        {recommendation.recommendations.map((rec, idx) => (
          <div key={idx} className="bg-space-800/40 border border-white/5 rounded p-3">
            <div className="flex items-start gap-2">
              <span className="text-nebula-400 text-lg">🎲</span>
              <div className="flex-1">
                <div className="text-stardust-300 text-sm font-medium mb-1">
                  {rec.field}: {rec.value}
                </div>
                <div className="text-void-400 text-xs">
                  Based on: {rec.reason}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function GuidedChat({ 
  messages, 
  onSend, 
  disabled = false, 
  proposals = [], 
  sessionId = '', 
  onProposalResolved 
}: GuidedChatProps) {
  const [input, setInput] = useState('');
  const [trayProposals, setTrayProposals] = useState<A1Proposal[]>([]);
  const [displayProposals, setDisplayProposals] = useState<A1Proposal[]>([]);

  // Split proposals: first 3 go to display, rest to tray
  useState(() => {
    if (proposals.length > 0) {
      const toDisplay = proposals.slice(0, 3);
      const toTray = proposals.slice(3);
      setDisplayProposals(toDisplay);
      setTrayProposals(toTray);
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      // User ignores proposals and sends message - move display proposals to tray
      if (displayProposals.length > 0) {
        setTrayProposals(prev => [...prev, ...displayProposals]);
        setDisplayProposals([]);
      }
      onSend(input.trim());
      setInput('');
    }
  };

  const handleProposalResolved = (key: string) => {
    // Remove from display proposals
    setDisplayProposals(prev => prev.filter(p => p.key !== key));
    // Trigger parent callback
    if (onProposalResolved) {
      onProposalResolved(key);
    }
  };

  const handleTrayProposalResolved = (key: string) => {
    // Remove from tray proposals
    setTrayProposals(prev => prev.filter(p => p.key !== key));
    // Trigger parent callback
    if (onProposalResolved) {
      onProposalResolved(key);
    }
  };

  const handleRestoreFromTray = (key: string) => {
    // Move from tray to display if less than 3 in display
    if (displayProposals.length < 3) {
      const proposal = trayProposals.find(p => p.key === key);
      if (proposal) {
        setTrayProposals(prev => prev.filter(p => p.key !== key));
        setDisplayProposals(prev => [...prev, proposal]);
      }
    }
  };

  // Suspend next_question when proposals are present
  const showSuspendedMessage = displayProposals.length > 0;

  return (
    <div className="flex flex-col h-full bg-slate-950 relative">
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
              {message.diceRecommendation && (
                <DiceRecommendationCard recommendation={message.diceRecommendation} />
              )}
            </div>
          </div>
        ))}
        
        {/* Display proposal cards (inline with messages) */}
        {displayProposals.map(proposal => (
          <div key={proposal.key} className="flex justify-start">
            <ProposalCard
              proposal={proposal}
              sessionId={sessionId}
              onResolved={handleProposalResolved}
              fieldLabel={`${proposal.module}.${proposal.subfield}`}
            />
          </div>
        ))}

        {/* Suspended message placeholder */}
        {showSuspendedMessage && (
          <div className="text-center text-stardust-300 text-sm py-3 glass-panel px-4 border border-nebula-400/20">
            处理完修改提案后继续
          </div>
        )}

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

      {/* Proposal tray */}
      {sessionId && (
        <ProposalTray
          proposals={trayProposals}
          sessionId={sessionId}
          onResolved={handleTrayProposalResolved}
          onRestore={handleRestoreFromTray}
        />
      )}
    </div>
  );
}
