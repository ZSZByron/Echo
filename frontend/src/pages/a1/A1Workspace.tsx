/**
 * A1Workspace Page
 *
 * Three-state flow for A1 workbench:
 * 1. SeedSelector - Choose from 8 seeds or custom input
 * 2. GuidedChat - Interactive chat with file panel and progress tracking
 * 3. PosterView - Display generated poster with link to poster page
 */

import { useState, useEffect } from 'react';
import { fetchJson, ApiError } from '../../api/client';
import { GuidedChat, type Message } from '../../components/guided/GuidedChat';
import { StructuredFilePanel, type DiffChange, type StructuredFile } from '../../components/structured/StructuredFilePanel';
import { DimensionProgress } from '../../components/structured/DimensionProgress';
import { PosterBoard } from '../../components/poster/PosterBoard';
import '../../components/theme.css';

// API Types
interface Seed {
  id: string;
  name: string;
  genre: string;
  description: string;
  dimension_defaults: Record<string, unknown>;
}

interface SeedsResponse {
  seeds: Seed[];
}

interface SessionStartResponse {
  session_id: string;
  file_id: string;
  ip_code: string;
  first_question: string;
  file: StructuredFile;
}

interface ChatResponse {
  reply: string;
  next_question: string;
  file_diff?: DiffChange[];
  progress: {
    sections: Array<{ id: string; label: string; done: boolean }>;
    done: number;
  };
  phase: string;
  classification_proposal?: string;
}

interface FinalizeResponse {
  graph_id: string;
  graph_code: string;
  warnings?: string[];
}

interface PosterResponse {
  panels: Array<{ id: string; title: string; content: string }>;
  ai_image_prompt: string;
  ai_image_status: string;
}

interface MissingSectionsError {
  missing_sections: string[];
}

// Workspace States
type WorkspaceState = 'seed_selector' | 'guided_chat' | 'poster_view';

export function A1Workspace() {
  const [workspaceState, setWorkspaceState] = useState<WorkspaceState>('seed_selector');
  const [userId] = useState<string>(() => localStorage.getItem('user_id') || '');
  
  // Seed Selector State
  const [seeds, setSeeds] = useState<Seed[]>([]);
  const [customIdea, setCustomIdea] = useState('');
  const [isLoadingSeeds, setIsLoadingSeeds] = useState(true);
  
  // Session State
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [fileId, setFileId] = useState<string | null>(null);
  const [ipCode, setIpCode] = useState<string | null>(null);
  
  // Chat State
  const [messages, setMessages] = useState<Message[]>([]);
  const [file, setFile] = useState<StructuredFile | null>(null);
  const [progressSections, setProgressSections] = useState<Array<{ id: string; label: string; done: boolean }>>([]);
  const [progressDone, setProgressDone] = useState(0);
  const [isChatLoading, setIsChatLoading] = useState(false);
  
  // Classification Proposal State
  const [classificationProposal, setClassificationProposal] = useState<string | null>(null);
  const [showClassificationModal, setShowClassificationModal] = useState(false);
  
  // Error State
  const [error, setError] = useState<string | null>(null);
  const [missingSections, setMissingSections] = useState<string[] | null>(null);

  // Load seeds on mount
  useEffect(() => {
    fetchJson<SeedsResponse>('/api/a1/seeds')
      .then((data: SeedsResponse) => {
        setSeeds(data.seeds);
        setIsLoadingSeeds(false);
      })
      .catch((err: Error) => {
        console.error('Failed to load seeds:', err);
        setError('Failed to load seeds. Please try again.');
        setIsLoadingSeeds(false);
      });
  }, []);

  // Start session from seed or custom idea
  const startSession = async (seedId?: string, customIdeaText?: string) => {
    setIsChatLoading(true);
    setError(null);
    
    try {
      const request = {
        user_id: userId,
        ...(seedId && { seed_id: seedId }),
        ...(customIdeaText && { custom_idea: customIdeaText })
      };
      
      const response = await fetchJson<SessionStartResponse>('/api/a1/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });
      
      setSessionId(response.session_id);
      setFileId(response.file_id);
      setIpCode(response.ip_code);
      setFile(response.file);
      
      // Initialize messages with first question
      setMessages([{
        id: Date.now().toString(),
        type: 'assistant',
        text: response.first_question,
      }]);
      
      setWorkspaceState('guided_chat');
    } catch (err) {
      console.error('Failed to start session:', err);
      setError('Failed to start session. Please try again.');
    } finally {
      setIsChatLoading(false);
    }
  };

  // Send chat message
  const sendMessage = async (text: string) => {
    if (!sessionId || isChatLoading) return;
    
    setIsChatLoading(true);
    setError(null);
    
    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      text,
    };
    setMessages(prev => [...prev, userMessage]);
    
    try {
      const response = await fetchJson<ChatResponse>('/api/a1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: text,
        }),
      });
      
      // Add assistant reply
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        text: response.reply,
      };
      setMessages(prev => [...prev, assistantMessage]);
      
      // Update file and progress
      if (response.file_diff && file) {
        // Create updated file with diff applied
        const updatedFile = { ...file };
        response.file_diff.forEach((change: DiffChange) => {
          const sectionIndex = updatedFile.sections?.findIndex((s: { id: string }) => s.id === change.field);
          if (sectionIndex !== undefined && sectionIndex >= 0 && updatedFile.sections) {
            updatedFile.sections[sectionIndex] = {
              ...updatedFile.sections[sectionIndex],
              content: change.new,
              done: true,
            };
          }
        });
        setFile(updatedFile);
      }
      
      setProgressSections(response.progress.sections);
      setProgressDone(response.progress.done);
      
      // Handle classification proposal
      if (response.classification_proposal) {
        setClassificationProposal(response.classification_proposal);
        setShowClassificationModal(true);
      }
    } catch (err) {
      console.error('Failed to send message:', err);
      setError('Failed to send message. Please try again.');
      // Remove user message on error
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsChatLoading(false);
    }
  };

  // Confirm classification
  const confirmClassification = async (choice: string) => {
    if (!sessionId) return;
    
    setIsChatLoading(true);
    setShowClassificationModal(false);
    
    try {
      const response = await fetchJson<ChatResponse>('/api/a1/chat/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          choice,
        }),
      });
      
      // Add assistant reply
      const assistantMessage: Message = {
        id: Date.now().toString(),
        type: 'assistant',
        text: response.reply,
      };
      setMessages(prev => [...prev, assistantMessage]);
      
      if (response.file_diff && file) {
        const updatedFile = { ...file };
        response.file_diff.forEach((change: DiffChange) => {
          const sectionIndex = updatedFile.sections?.findIndex((s: { id: string }) => s.id === change.field);
          if (sectionIndex !== undefined && sectionIndex >= 0 && updatedFile.sections) {
            updatedFile.sections[sectionIndex] = {
              ...updatedFile.sections[sectionIndex],
              content: change.new,
              done: true,
            };
          }
        });
        setFile(updatedFile);
      }
      
      setProgressSections(response.progress.sections);
      setProgressDone(response.progress.done);
    } catch (err) {
      console.error('Failed to confirm classification:', err);
      if (err instanceof Error) {
        setError('Failed to confirm classification. Please try again.');
      }
    } finally {
      setIsChatLoading(false);
    }
  };

  // Finalize file
  const finalizeFile = async () => {
    if (!fileId) return;
    
    setIsChatLoading(true);
    setError(null);
    setMissingSections(null);
    
    try {
      const response = await fetchJson<FinalizeResponse>(`/api/a1/file/${fileId}/finalize`, {
        method: 'POST',
      });
      
      console.log('File finalized:', response);
      setWorkspaceState('poster_view');
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        const body = err.body as MissingSectionsError;
        setMissingSections(body.missing_sections || []);
        setError('File is incomplete. Please fill in all required sections.');
      } else if (err instanceof Error) {
        console.error('Failed to finalize file:', err);
        setError('Failed to finalize file. Please try again.');
      }
    } finally {
      setIsChatLoading(false);
    }
  };

  // Render Seed Selector
  const renderSeedSelector = () => (
    <div className="min-h-screen starry-gradient p-8">
      <div className="max-w-6xl mx-auto">
        <div className="glass-panel p-8 mb-8">
          <h1 className="text-3xl font-bold text-stardust-300 mb-2 glow-starlight">A1 Workbench</h1>
          <p className="text-void-400">Choose a seed to start your creative journey</p>
        </div>
        
        {isLoadingSeeds ? (
          <div className="glass-panel p-12 text-center">
            <div className="w-12 h-12 border-4 border-stardust-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-stardust-300">Loading seeds...</p>
          </div>
        ) : error ? (
          <div className="glass-panel p-8 bg-cosmos-error/10 border-cosmos-error/30">
            <p className="text-cosmos-error">{error}</p>
          </div>
        ) : (
          <>
            {/* Seed Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              {seeds.map(seed => (
                <div
                  key={seed.id}
                  onClick={() => startSession(seed.id)}
                  className="glass-card p-6 cursor-pointer hover:border-stardust-400/40 transition-all"
                >
                  <div className="flex items-center gap-2 mb-3">
                    <div className="text-stardust-400 text-xl">✦</div>
                    <h3 className="text-stardust-300 text-lg font-medium">{seed.name}</h3>
                  </div>
                  <div className="text-nebula-400 text-sm mb-2">{seed.genre}</div>
                  <p className="text-gray-300 text-sm leading-relaxed">{seed.description}</p>
                </div>
              ))}
            </div>
            
            {/* Custom Input */}
            <div className="glass-panel p-8">
              <h2 className="text-stardust-300 text-xl font-medium mb-4">Or start with your own idea</h2>
              <div className="flex gap-4">
                <input
                  type="text"
                  value={customIdea}
                  onChange={(e) => setCustomIdea(e.target.value)}
                  placeholder="Describe your creative concept..."
                  className="flex-1 bg-space-800 text-white placeholder-void-500 rounded-lg px-4 py-3 border border-white/10 focus:border-stardust-400 focus:outline-none"
                />
                <button
                  onClick={() => startSession(undefined, customIdea)}
                  disabled={!customIdea.trim()}
                  className="bg-stardust-400 text-space-950 px-6 py-3 rounded-lg font-medium hover:bg-stardust-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Start
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );

  // Render Guided Chat
  const renderGuidedChat = () => (
    <div className="min-h-screen starry-gradient">
      <div className="h-screen flex">
        {/* Left: Chat Area */}
        <div className="flex-1 flex flex-col">
          <div className="glass-panel p-4 border-b border-white/5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="text-stardust-400 text-xl">✦</div>
                <div>
                  <h1 className="text-stardust-300 text-lg font-medium">A1 Workbench</h1>
                  <p className="text-void-500 text-sm">IP Code: {ipCode || 'Loading...'}</p>
                </div>
              </div>
            <button
              onClick={() => window.location.href = '/a1'}
              className="text-void-400 hover:text-stardust-300 transition-colors"
            >
              ← Back to Seeds
            </button>
            </div>
          </div>
          
          <GuidedChat
            messages={messages}
            onSend={sendMessage}
            disabled={isChatLoading}
          />
        </div>
        
        {/* Right: File Panel + Progress */}
        <div className="w-[400px] overflow-y-auto starry-scroll p-6 space-y-6">
          {file && (
            <StructuredFilePanel
              file={file}
              className="sticky top-6"
            />
          )}
          
          {progressSections.length > 0 && (
            <DimensionProgress
              sections={progressSections}
              className="glass-panel"
            />
          )}
          
          {progressDone >= 10 && (
            <button
              onClick={finalizeFile}
              disabled={isChatLoading}
              className="w-full bg-stardust-400 text-space-950 px-6 py-4 rounded-lg font-medium hover:bg-stardust-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all glow-starlight"
            >
              {isChatLoading ? 'Processing...' : 'Finalize IP File'}
            </button>
          )}
          
          {error && (
            <div className={`glass-panel p-4 ${
              missingSections ? 'bg-cosmos-warning/20 border-cosmos-warning/30' : 'bg-cosmos-error/10 border-cosmos-error/30'
            }`}>
              <p className={missingSections ? 'text-cosmos-warning' : 'text-cosmos-error'}>{error}</p>
              {missingSections && missingSections.length > 0 && (
                <div className="mt-3">
                  <p className="text-stardust-300 text-sm mb-2">Missing sections:</p>
                  <ul className="text-void-400 text-sm space-y-1">
                    {missingSections.map(section => (
                      <li key={section}>• {section}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      
      {/* Classification Modal */}
      {showClassificationModal && classificationProposal && (
        <div className="fixed inset-0 bg-space-950/90 backdrop-blur-sm z-50 flex items-center justify-center p-8">
          <div className="glass-panel max-w-2xl w-full p-8">
            <h2 className="text-stardust-300 text-xl font-medium mb-4">Classification Proposal</h2>
            <p className="text-gray-200 mb-6">{classificationProposal}</p>
            <div className="flex gap-4">
              <button
                onClick={() => confirmClassification('accept')}
                className="flex-1 bg-cosmos-success text-space-950 px-6 py-3 rounded-lg font-medium hover:bg-cosmos-success/80 transition-colors"
              >
                Accept
              </button>
              <button
                onClick={() => confirmClassification('reject')}
                className="flex-1 bg-cosmos-error text-white px-6 py-3 rounded-lg font-medium hover:bg-cosmos-error/80 transition-colors"
              >
                Reject
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  // Render Poster View
  const renderPosterView = () => {
    if (!fileId) return null;
    
    return (
      <div className="min-h-screen starry-gradient">
        <div className="glass-panel p-4 border-b border-white/5">
          <div className="flex items-center justify-between max-w-7xl mx-auto">
            <div className="flex items-center gap-3">
              <div className="text-stardust-400 text-xl">✦</div>
              <div>
                <h1 className="text-stardust-300 text-lg font-medium">A1 Workbench</h1>
                <p className="text-void-500 text-sm">IP Code: {ipCode || 'Loading...'}</p>
              </div>
            </div>
            <button
              onClick={() => window.location.href = '/a1'}
              className="text-void-400 hover:text-stardust-300 transition-colors"
            >
              ← Back to Editor
            </button>
          </div>
        </div>
        
        <PosterPreview fileId={fileId} />
        
        <div className="max-w-7xl mx-auto p-8">
          <button
            onClick={() => window.location.href = `/a1/poster?fileId=${fileId}`}
            className="w-full bg-stardust-400 text-space-950 px-8 py-4 rounded-lg font-medium hover:bg-stardust-300 transition-all glow-starlight"
          >
            View Full Poster Page
          </button>
        </div>
      </div>
    );
  };

  return (
    <div>
      {workspaceState === 'seed_selector' && renderSeedSelector()}
      {workspaceState === 'guided_chat' && renderGuidedChat()}
      {workspaceState === 'poster_view' && renderPosterView()}
    </div>
  );
}

// Poster Preview Component
function PosterPreview({ fileId }: { fileId: string }) {
  const [posterData, setPosterData] = useState<PosterResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    fetchJson<PosterResponse>(`/api/a1/file/${fileId}/poster`)
      .then((data: PosterResponse) => {
        setPosterData(data);
        setIsLoading(false);
      })
      .catch((err: Error) => {
        console.error('Failed to load poster:', err);
        setError('Failed to load poster');
        setIsLoading(false);
      });
  }, [fileId]);
  
  if (isLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-stardust-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-stardust-300">Loading poster preview...</p>
        </div>
      </div>
    );
  }
  
  if (error || !posterData) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="glass-panel p-8 bg-cosmos-error/10 border-cosmos-error/30">
          <p className="text-cosmos-error">{error || 'Failed to load poster'}</p>
        </div>
      </div>
    );
  }
  
  return (
    <PosterBoard
      panels={posterData.panels}
      className="min-h-[60vh]"
    />
  );
}