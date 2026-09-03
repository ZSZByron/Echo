/**
 * A1Workspace Page
 *
 * Three-state flow for 世界观工坊:
 * 1. SeedSelector - Choose from 8 seeds or custom input
 * 2. GuidedChat - Interactive chat with file panel and progress tracking
 * 3. PosterView - Display generated poster with link to poster page
 */

import { useState, useEffect, useMemo } from 'react';
import { fetchJson, ApiError } from '../../api/client';
import { GuidedChat, type Message } from '../../components/guided/GuidedChat';
import { StructuredFilePanel, type DiffChange, type StructuredFile } from '../../components/structured/StructuredFilePanel';
import { DimensionProgress } from '../../components/structured/DimensionProgress';
import { PosterBoard } from '../../components/poster/PosterBoard';
import { A1GraphSection } from '../../components/graph/A1GraphSection';
import { UploadToolbar } from './UploadToolbar';
import { CopyrightDialog, type CopyrightReport } from './CopyrightDialog';
import type { A1Proposal } from '../../types/a1';
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

interface QuestionPayload {
  section: string;
  section_label?: string;
  sub_id?: string;
  sub_label?: string;
  question: string;
  hint: string;
  example?: string;
}

interface DiceRecommendation {
  field: string;
  value: string;
  reason: string;
}

interface DiceRecommendationResponse {
  recommendations: DiceRecommendation[];
  summary: string;
}

interface SeedInfo {
  name: string;
  genre: string;
  description: string;
}

interface SessionStartResponse {
  session_id: string;
  file_id: string;
  ip_code: string;
  first_question: QuestionPayload | null;
  file: StructuredFile;
  seed?: SeedInfo;
}

interface ChatResponse {
  reply: string;
  next_question: QuestionPayload | null;
  file_diff?: DiffChange[];
  progress: {
    sections: Array<{ 
      id: string; 
      label: string; 
      done: boolean;
      subs?: Array<{
        id: string;
        label: string;
        done: boolean;
      }>;
    }>;
    done: number;
    /** True when every module has >50% subfields answered (finalize gate). */
    finalizable?: boolean;
  };
  phase: string;
  classification_proposal?: ClassificationProposalData;
  dice_recommendation?: DiceRecommendationResponse;
  proposals?: A1Proposal[];
  divergent_question?: string;
  needs_clarification?: boolean;
}

interface FileData {
  file_id: string;
  status: 'draft' | 'finalized';
  answers: Record<string, string>;
  graph_code: string | null;
  session_id: string;
  sections: Array<{
    id: string;
    label: string;
    done: boolean;
    content?: string;
    subs?: Array<{ id: string; label: string; content?: string; done: boolean }>;
  }>;
  open_questions: string[];
  edge_stats: {
    semantic_total: number;
    semantic_confirmed: number;
    rule_total: number;
    structure_total: number;
    pending_review: number;
  };
  confirmed_edges: Record<string, { from_node_id: string; to_node_id: string; relation: string; confidence: string; confirmed: boolean }>;
  rejected_edges: Record<string, { from_node_id: string; to_node_id: string; relation: string; confidence: string; confirmed: boolean }>;
}

interface FinalizeResponse {
  graph_id: string;
  graph_code: string;
  warnings?: string[];
}

interface VisualBgImage {
  path: string;
  filename: string;
  url: string;
  score: number;
  comment: string;
  reasoning: string;
  closest: boolean;
}

interface PosterResponse {
  panels: Array<{ id: string; title: string; content: string }>;
  ai_image_prompt: string;
  ai_image_status: string;
  visual_bg_status: string | null;
  visual_bg_images: VisualBgImage[];
  visual_bg_best: string | null;
  visual_bg_prompt: string | null;
}

interface MissingSectionsError {
  missing_sections: string[];
}

interface ProposalSuggestion {
  field: string;
  category: string;
}

interface ClassificationProposalData {
  suggestions: ProposalSuggestion[];
}

// Upload API Types
interface UploadRequest {
  user_id: string;
  filename: string;
  content: string;
}

interface CopyrightHit {
  term: string;
  work: string;
  evidence: string;
}

interface UploadResponseCopyrightHit {
  status: 'copyright_hit';
  upload_id: string;
  report: {
    risk_level: string;
    matches: CopyrightHit[];
  };
}

interface UploadResponseParsed {
  status: 'parsed';
  session_id: string;
  file_id: string;
  ip_code: string;
  file: StructuredFile;
  answers: Record<string, string>; // Key format: "module.field"
  innovations: Array<{ field: string; suggestion: string }>;
}

type UploadResponse = UploadResponseCopyrightHit | UploadResponseParsed;

interface ConvertRequest {
  user_id: string;
  upload_id: string;
  decision: 'convert' | 'cancel';
}

interface ConvertResponse {
  status: 'parsed';
  session_id: string;
  file_id: string;
  ip_code: string;
  file: StructuredFile;
  answers: Record<string, string>;
  innovations: Array<{ field: string; suggestion: string }>;
}

// Workspace States
type WorkspaceState = 'seed_selector' | 'guided_chat' | 'graph_view';

// Format a question payload for display, with example hint for the user.
function formatQuestion(nq: QuestionPayload | null): string {
  if (!nq) return '';
  const header = nq.sub_label
    ? `【${nq.section_label || nq.section} · ${nq.sub_label}】`
    : `【${nq.section_label || nq.section}】`;
  const example = nq.example ? `\n💡 示例：${nq.example}` : '';
  return `${header}${nq.question}${example}`;
}

const A1_STORAGE_KEY = 'a1_workspace_v1';

export function A1Workspace() {
  // Persisted state: survive page reload / tab switch (auto-restores session)
  const [persisted] = useState<Record<string, unknown>>(() => {
    try { return JSON.parse(localStorage.getItem(A1_STORAGE_KEY) || '{}'); }
    catch { return {}; }
  });
  const [workspaceState, setWorkspaceState] = useState<WorkspaceState>(() => {
    // Read as plain string: legacy values ('poster_view') need migration.
    const persistedState = persisted.workspaceState as string | undefined;

    // Migration: poster_view -> graph_view
    if (persistedState === 'poster_view') {
      return 'graph_view';
    }

    // Check for return intent from poster page
    const returnIntent = localStorage.getItem('a1_return_intent');
    if (returnIntent === 'chat' && persisted.sessionId) {
      return 'guided_chat';
    }

    return (persistedState as WorkspaceState) || 'seed_selector';
  });
  const [userId] = useState<string>(() => localStorage.getItem('user_id') || '');
  
  // Seed Selector State
  const [seeds, setSeeds] = useState<Seed[]>([]);
  const [customIdea, setCustomIdea] = useState('');
  const [isLoadingSeeds, setIsLoadingSeeds] = useState(true);
  
  // Session State
  const [sessionId, setSessionId] = useState<string | null>(
    (persisted.sessionId as string) || null
  );
  const [fileId, setFileId] = useState<string | null>(
    (persisted.fileId as string) || null
  );
  const [ipCode, setIpCode] = useState<string | null>(
    (persisted.ipCode as string) || null
  );
  const [seedInfo, setSeedInfo] = useState<SeedInfo | null>(
    (persisted.seedInfo as SeedInfo) || null
  );
  
  // Chat State
  const [messages, setMessages] = useState<Message[]>(
    (persisted.messages as Message[]) || []
  );
  const [file, setFile] = useState<StructuredFile | null>(null);
  const [progressSections, setProgressSections] = useState<Array<{ 
    id: string; 
    label: string; 
    done: boolean;
    subs?: Array<{
      id: string;
      label: string;
      done: boolean;
    }>;
  }>>([]);
  const [finalizable, setFinalizable] = useState(false);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [pendingProposals, setPendingProposals] = useState<A1Proposal[]>([]);
  
  // Graph State
  const [graphCode, setGraphCode] = useState<string | null>(null);
  
  // File metadata state for graph section
  const [, setFileData] = useState<FileData | null>(null);
  
  // Classification Proposal State
  const [classificationProposal, setClassificationProposal] = useState<ClassificationProposalData | null>(null);
  const [showClassificationModal, setShowClassificationModal] = useState(false);
  
  // Upload State
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [copyrightReport, setCopyrightReport] = useState<CopyrightReport | null>(null);
  const [pendingUploadId, setPendingUploadId] = useState<string | null>(null);
  const [uploadedInnovations, setUploadedInnovations] = useState<Array<{ field: string; suggestion: string }>>([]);
  const [isConverting, setIsConverting] = useState(false);
  
  // Error State
  const [error, setError] = useState<string | null>(null);
  const [missingSections, setMissingSections] = useState<string[] | null>(null);

  // Persist key state to localStorage (survive reload / tab switch)
  useEffect(() => {
    try {
      localStorage.setItem(A1_STORAGE_KEY, JSON.stringify({
        workspaceState, sessionId, fileId, ipCode, seedInfo, messages,
      }));
    } catch { /* quota exceeded, ignore */ }
  }, [workspaceState, sessionId, fileId, ipCode, seedInfo, messages]);

  // Load seeds on mount (skip in graph_view — not needed and would trigger re-renders)
  useEffect(() => {
    if (workspaceState === 'graph_view') return;
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

  // Hydration effect: restore file state on mount (runs once)
  useEffect(() => {
    // Clean up return intent flag
    localStorage.removeItem('a1_return_intent');
  }, []); // Run once on mount

  // Hydrate file state when fileId changes (skip in graph_view to avoid
  // re-render cycle — GraphViewContent loads its own file data locally)
  useEffect(() => {
    // If we have a fileId, restore the complete file state
    if (fileId && workspaceState !== 'graph_view') {
      const hydrateFileState = async () => {
        try {
          const response = await fetchJson<{
            file_id: string;
            status: string;
            answers: Record<string, string>;
            graph_code?: string;
            session_id: string;
            sections: Array<{
              id: string;
              label: string;
              done: boolean;
              content?: string;
              subs?: Array<{ id: string; label: string; content?: string; done: boolean }>;
            }>;
          }>(`/api/a1/file/${fileId}`);
          
          // Set file state
          setFile({
            status: response.status === 'finalized' ? 'finalized' : 'draft',
            sections: response.sections,
          });
          
          // Set progress sections
          setProgressSections(response.sections);
          
          // Calculate finalizable: each module has non-empty subs and >50% done ratio
          const allFinalizable = response.sections.every(section => {
            if (!section.subs || section.subs.length === 0) return false;
            const doneCount = section.subs.filter(sub => sub.done).length;
            return doneCount / section.subs.length > 0.5;
          });
          setFinalizable(allFinalizable);
          
          // Set graph code if available
          if (response.graph_code) {
            setGraphCode(response.graph_code);
          }
        } catch (err) {
          console.error('Failed to hydrate file state:', err);
          // Don't show error to user - hydration is optional
        }
      };
      
      hydrateFileState();
    }
  }, [fileId]); // Run when fileId changes

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
      setSeedInfo(response.seed ?? null);
      setFile(response.file);

      // Initialize messages with first question, anchored on the seed
      const fq = response.first_question;
      const seedPrefix = response.seed?.name
        ? `你选择了种子「${response.seed.name}」（${response.seed.genre}）：${response.seed.description}。我将围绕这个基调引导你展开世界观。\n\n`
        : response.seed?.description
        ? `你的初始创意：${response.seed.description}。我将围绕它引导你展开世界观。\n\n`
        : '';
      const questionText = formatQuestion(fq);
      
      setMessages([{
        id: Date.now().toString(),
        type: 'assistant',
        text: seedPrefix + questionText,
      }]);
      
      setWorkspaceState('guided_chat');
    } catch (err) {
      console.error('Failed to start session:', err);
      setError('Failed to start session. Please try again.');
    } finally {
      setIsChatLoading(false);
    }
  };

  // Refresh the structured file panel from the server (single source of
  // truth). Called after each chat turn so refinements show up immediately.
  const refreshFile = async (id: string) => {
    try {
      const response = await fetchJson<{
        status: string;
        sections: Array<{
          id: string;
          label: string;
          done: boolean;
          content?: string;
          subs?: Array<{ id: string; label: string; content?: string; done: boolean }>;
        }>;
        open_questions: string[];
        edge_stats: {
          semantic_total: number;
          semantic_confirmed: number;
          rule_total: number;
          structure_total: number;
          pending_review: number;
        };
        confirmed_edges: Record<string, { from_node_id: string; to_node_id: string; relation: string; confidence: string; confirmed: boolean }>;
        rejected_edges: Record<string, { from_node_id: string; to_node_id: string; relation: string; confidence: string; confirmed: boolean }>;
      }>(`/api/a1/file/${id}`);
      
      // Update file state for panel
      setFile({
        status: response.status === 'finalized' ? 'finalized' : 'draft',
        sections: response.sections,
      });
      
      // Update file data for graph section
      setFileData({
        file_id: id,
        status: response.status === 'finalized' ? 'finalized' : 'draft',
        answers: {}, // Will be populated if needed
        graph_code: null,
        session_id: sessionId || '',
        sections: response.sections,
        open_questions: response.open_questions,
        edge_stats: response.edge_stats,
        confirmed_edges: response.confirmed_edges,
        rejected_edges: response.rejected_edges,
      });
    } catch (err) {
      console.error('Failed to refresh file:', err);
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
        timeoutMs: 120_000,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: text,
        }),
        timeoutMs: 120000,
      });
      
      // Add assistant reply
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        text: response.reply,
        diceRecommendation: response.dice_recommendation,
      };
      setMessages(prev => [...prev, assistantMessage]);
      
      // Add next question with two-level formatting (only if no proposals - 单问句铁律)
      if (response.next_question && (!response.proposals || response.proposals.length === 0)) {
        const questionText = formatQuestion(response.next_question);

        setMessages(prev => [...prev, {
          id: (Date.now() + 2).toString(),
          type: 'assistant',
          text: questionText,
        }]);
      }

      // Handle proposals from guard
      if (response.proposals && response.proposals.length > 0) {
        setPendingProposals(response.proposals);
      }

      // Refresh the file panel from the server so every refinement
      // (first write, overwrite, skip) is reflected immediately.
      if (fileId && response.file_diff?.length) {
        await refreshFile(fileId);
      }

      setProgressSections(response.progress.sections);
      setFinalizable(response.progress.finalizable ?? false);


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
    if (!sessionId || !classificationProposal) return;

    setIsChatLoading(true);
    setShowClassificationModal(false);

    try {
      const response = await fetchJson<ChatResponse>('/api/a1/chat/confirm', {
        method: 'POST',
        timeoutMs: 120_000,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          proposal: classificationProposal,
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
      
      // Add next question with two-level formatting
      if (response.next_question) {
        const questionText = formatQuestion(response.next_question);

        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          text: questionText,
        }]);
      }

      if (fileId && response.file_diff?.length) {
        await refreshFile(fileId);
      }

      setProgressSections(response.progress.sections);
      setFinalizable(response.progress.finalizable ?? false);
    } catch (err) {
      console.error('Failed to confirm classification:', err);
      if (err instanceof Error) {
        setError('Failed to confirm classification. Please try again.');
      }
    } finally {
      setIsChatLoading(false);
    }
  };

  // Handle proposal resolution
  const handleProposalResolved = async (key: string) => {
    setPendingProposals(prev => prev.filter(p => p.key !== key));
    
    // Refresh file after proposal is resolved to show updated answers
    if (fileId) {
      await refreshFile(fileId);
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
        // Finalize runs concept-edge LLM extraction (measured 60-120s with a
        // real provider) — the 30s global timeout aborts before completion
        // and the workspace never switches to graph view.
        timeoutMs: 180_000,
      });
      
      console.log('File finalized:', response);
      
      // Save graph code to state
      setGraphCode(response.graph_code);
      
      // Transition to graph view
      setWorkspaceState('graph_view');
      
      // Hydrate file state to finalized status
      if (fileId) {
        try {
          const fileResponse = await fetchJson<{
            status: string;
            sections: Array<{
              id: string;
              label: string;
              done: boolean;
              content?: string;
              subs?: Array<{ id: string; label: string; content?: string; done: boolean }>;
            }>;
          }>(`/api/a1/file/${fileId}`);
          
          setFile({
            status: fileResponse.status === 'finalized' ? 'finalized' : 'draft',
            sections: fileResponse.sections,
          });
          
          setProgressSections(fileResponse.sections);
          
          const allFinalizable = fileResponse.sections.every(section => {
            if (!section.subs || section.subs.length === 0) return false;
            const doneCount = section.subs.filter(sub => sub.done).length;
            return doneCount / section.subs.length > 0.5;
          });
          setFinalizable(allFinalizable);
        } catch (err) {
          console.error('Failed to hydrate after finalize:', err);
        }
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // FastAPI wraps errors as {detail: {...}}; support both shapes.
        const detail = (err.body as { detail?: MissingSectionsError })?.detail;
        const missing = detail?.missing_sections
          ?? (err.body as MissingSectionsError)?.missing_sections
          ?? [];
        setMissingSections(missing);
        setError('File is incomplete. Please fill in all required sections.');
      } else if (err instanceof Error) {
        console.error('Failed to finalize file:', err);
        setError('Failed to finalize file. Please try again.');
      }
    } finally {
      setIsChatLoading(false);
    }
  };

  // Handle file upload
  const handleFileUpload = async (filename: string, content: string) => {
    setIsUploading(true);
    setUploadError(null);

    // Check for client-side validation errors
    if (!content) {
      setUploadError('文件选择失败或文件格式不正确');
      setIsUploading(false);
      return;
    }
    
    try {
      const response = await fetchJson<UploadResponse>('/api/a1/upload', {
        method: 'POST',
        timeoutMs: 180_000,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          filename,
          content,
        } as UploadRequest),
      });

      if (response.status === 'copyright_hit') {
        setPendingUploadId(response.upload_id);
        setCopyrightReport({
          risk_level: response.report.risk_level,
          matches: response.report.matches,
        });
      } else if (response.status === 'parsed') {
        // Successfully parsed, enter guided chat
        handleUploadSuccess(response, filename);
      }
    } catch (err) {
      console.error('Failed to upload file:', err);
      if (err instanceof ApiError && err.status === 503) {
        setUploadError('上传解析需要 LLM 服务');
      } else if (err instanceof ApiError && err.status === 422) {
        setUploadError('文件格式不正确，请确保文件至少包含 200 字符的有效文本内容');
      } else {
        setUploadError('上传失败，请重试');
      }
    } finally {
      setIsUploading(false);
    }
  };

  // Handle successful upload response
  const handleUploadSuccess = (response: UploadResponseParsed, filename?: string) => {
    setSessionId(response.session_id);
    setFileId(response.file_id);
    setIpCode(response.ip_code);
    setSeedInfo(filename ? { name: filename, genre: '上传', description: '来自世界观文档' } : null);
    setFile(response.file);
    setUploadedInnovations(response.innovations);

    // Seed the progress panel from the prefilled sections so the
    // DimensionProgress grid is visible before the first chat turn.
    const sections = response.file.sections ?? [];
    if (sections.length > 0) {
      setProgressSections(sections.map(section => ({
        id: section.id,
        label: section.label,
        done: Boolean(section.done),
        subs: (section.subs ?? []).map(sub => ({
          id: sub.id,
          label: sub.label,
          done: sub.done,
        })),
      })));
      // Finalize gate: every module must have strictly >50% subs answered.
      setFinalizable(sections.every(section => {
        const subs = section.subs ?? [];
        return subs.length > 0
          && subs.filter(sub => sub.done).length / subs.length > 0.5;
      }));
    }

    // Initialize chat with welcome message
    setMessages([{
      id: Date.now().toString(),
      type: 'assistant',
      text: '已成功解析您的世界观文档。我已预填了基础信息，您可以查看右侧面板并继续完善细节。',
    }]);

    setWorkspaceState('guided_chat');
  };

  // Handle copyright conversion
  const handleCopyrightConvert = async () => {
    if (!pendingUploadId) return;

    setIsConverting(true);
    
    try {
      const response = await fetchJson<ConvertResponse>('/api/a1/upload/convert', {
        method: 'POST',
        timeoutMs: 180_000,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          upload_id: pendingUploadId,
          decision: 'convert',
        } as ConvertRequest),
      });

      // Clear copyright modal state
      setCopyrightReport(null);
      setPendingUploadId(null);
      
      // Enter guided chat with converted content
      handleUploadSuccess(response);
    } catch (err) {
      console.error('Failed to convert content:', err);
      setUploadError('转换失败，请重试');
    } finally {
      setIsConverting(false);
    }
  };

  // Handle copyright cancel
  const handleCopyrightCancel = () => {
    // Notify the backend to drop the pending upload (fire-and-forget).
    if (pendingUploadId) {
      fetchJson('/api/a1/upload/convert', {
        method: 'POST',
        timeoutMs: 180_000,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          upload_id: pendingUploadId,
          decision: 'cancel',
        } as ConvertRequest),
      }).catch((err: Error) => {
        console.error('Failed to cancel upload:', err);
      });
    }
    setCopyrightReport(null);
    setPendingUploadId(null);
    setUploadError(null);
  };

  // Render Seed Selector
  const renderSeedSelector = () => (
    <div className="min-h-screen starry-gradient p-8">
      <div className="max-w-6xl mx-auto">
        <div className="glass-panel p-8 mb-8">
          <h1 className="text-3xl font-bold text-stardust-300 mb-2 glow-starlight">世界观工坊</h1>
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
            
            {/* Upload Toolbar */}
            <UploadToolbar
              onUpload={handleFileUpload}
              isUploading={isUploading}
              uploadError={uploadError}
            />
            
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
        
        {/* Copyright Dialog */}
        {copyrightReport && (
          <CopyrightDialog
            report={copyrightReport}
            onConvert={handleCopyrightConvert}
            onCancel={handleCopyrightCancel}
            isProcessing={isConverting}
          />
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
                  <h1 className="text-stardust-300 text-lg font-medium">世界观工坊</h1>
                  <p className="text-void-500 text-sm">
                    IP Code: {ipCode || 'Loading...'}
                    {seedInfo?.name && (
                      <span className="ml-2 text-nebula-400">
                        | 种子: {seedInfo.name}（{seedInfo.genre}）
                      </span>
                    )}
                    {!seedInfo?.name && seedInfo?.description && (
                      <span className="ml-2 text-nebula-400">| 自定义创意</span>
                    )}
                  </p>
                </div>
              </div>
            <button
              onClick={() => { localStorage.removeItem(A1_STORAGE_KEY); window.location.href = '/a1'; }}
              className="text-void-400 hover:text-stardust-300 transition-colors"
            >
              ← 返回种子选择
            </button>
            </div>
          </div>
          
          <GuidedChat
            messages={messages}
            onSend={sendMessage}
            disabled={isChatLoading}
            proposals={pendingProposals}
            sessionId={sessionId || ''}
            onProposalResolved={handleProposalResolved}
          />
        </div>
        
        {/* Right: File Panel + Progress (scrollable) + fixed Finalize footer */}
        <div className="w-[400px] flex flex-col border-l border-white/5">
          <div className="flex-1 overflow-y-auto starry-scroll p-6 space-y-6">
          {file && (
            <StructuredFilePanel file={file} />
          )}
          
          {progressSections.length > 0 && (
            <DimensionProgress
              sections={progressSections}
              className="glass-panel"
            />
          )}
          
          {/* Innovations Module Display */}
          {uploadedInnovations.length > 0 && (
            <div className="glass-panel p-6">
              <h3 className="text-stardust-300 text-lg font-medium mb-4 flex items-center gap-2">
                <span>✦</span>
                创新模块
              </h3>
              <div className="space-y-3">
                {uploadedInnovations.map((innovation, index) => (
                  <div key={index} className="bg-space-800/40 border border-nebula-400/20 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <div className="text-nebula-400 text-lg">💡</div>
                      <div className="flex-1">
                        <div className="text-stardust-300 text-sm font-medium mb-2">
                          {innovation.field}
                        </div>
                        <div className="text-gray-300 text-sm leading-relaxed">
                          {innovation.suggestion}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
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
          </div>{/* end scrollable content */}

          {/* Fixed footer: Finalize button always visible */}
          <div className="p-6 border-t border-white/5 bg-space-900/70 backdrop-blur-sm space-y-2">
            <button
              onClick={finalizeFile}
              disabled={!finalizable || isChatLoading}
              title={finalizable
                ? '定稿并生成知识图谱与展板'
                : '每个板块需完成超过50%的字段后方可定稿'}
              className={`w-full px-6 py-4 rounded-lg font-medium transition-all ${
                finalizable
                  ? 'bg-stardust-400 text-space-950 hover:bg-stardust-300 glow-starlight'
                  : 'bg-space-800/60 text-gray-500 cursor-not-allowed border border-nebula-400/10'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {isChatLoading ? '处理中...' : finalizable ? '定稿并生成知识图谱' : '定稿（需各板块完成过半字段）'}
            </button>
            {!finalizable && (
              <p className="text-void-400 text-xs text-center">
                {progressSections
                  .filter(s => {
                    const subs = s.subs ?? [];
                    if (subs.length === 0) return false;
                    return subs.filter(b => b.done).length / subs.length <= 0.5;
                  })
                  .map(s => s.label)
                  .join('、') || '部分'}板块完成度未过半——在对话中告诉我缺失模块的设定即可补全
              </p>
            )}
            {file?.status === 'finalized' && (
              <p className="text-cosmos-success text-xs text-center">
                已定稿 · 继续对话修改将打回草稿并需重新定稿
              </p>
            )}
          </div>
        </div>
      </div>
      
      {/* Classification Modal */}
      {showClassificationModal && classificationProposal && (
        <div className="fixed inset-0 bg-space-950/90 backdrop-blur-sm z-50 flex items-center justify-center p-8">
          <div className="glass-panel max-w-2xl w-full p-8">
            <h2 className="text-stardust-300 text-xl font-medium mb-4">Classification Proposal</h2>
            <p className="text-gray-200 mb-4">
              这条内容无法直接映射到词典枚举值，请选择处理方式：
            </p>
            <div className="mb-6 space-y-2">
              {classificationProposal.suggestions.map((s, idx) => (
                <div key={idx} className="bg-space-800/40 border border-white/5 rounded p-3 text-sm">
                  <span className="text-gray-300">{s.field}</span>
                  <span className="text-void-400 ml-2">→ 建议分类: {s.category}</span>
                </div>
              ))}
            </div>
            <div className="flex gap-4">
              <button
                onClick={() => confirmClassification('其他')}
                className="flex-1 bg-cosmos-success text-space-950 px-6 py-3 rounded-lg font-medium hover:bg-cosmos-success/80 transition-colors"
              >
                保留原文（其他）
              </button>
              <button
                onClick={() => confirmClassification('放弃')}
                className="flex-1 bg-cosmos-error text-white px-6 py-3 rounded-lg font-medium hover:bg-cosmos-error/80 transition-colors"
              >
                放弃
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  // Render Graph View
  const renderGraphView = () => {
    if (!fileId) return null;
    
    const returnToChat = () => {
      setWorkspaceState('guided_chat');
      // Re-hydrate file state when returning from graph/poster view
      if (fileId) {
        fetchJson<{
          status: string;
          sections: Array<{
            id: string;
            label: string;
            done: boolean;
            content?: string;
            subs?: Array<{ id: string; label: string; content?: string; done: boolean }>;
          }>;
          graph_code?: string;
        }>(`/api/a1/file/${fileId}`)
          .then((response) => {
            setFile({
              status: response.status === 'finalized' ? 'finalized' : 'draft',
              sections: response.sections,
            });
            setProgressSections(response.sections);
            
            const allFinalizable = response.sections.every(section => {
              if (!section.subs || section.subs.length === 0) return false;
              const doneCount = section.subs.filter(sub => sub.done).length;
              return doneCount / section.subs.length > 0.5;
            });
            setFinalizable(allFinalizable);
            
            if (response.graph_code) {
              setGraphCode(response.graph_code);
            }
          })
          .catch((err) => {
            console.error('Failed to re-hydrate file state:', err);
          });
      }
    };
    
    return (
      <div className="min-h-screen starry-gradient">
        {/* Top Bar */}
        <div className="glass-panel p-4 border-b border-white/5">
          <div className="flex items-center justify-between max-w-7xl mx-auto">
            <div className="flex items-center gap-3">
              <div className="text-stardust-400 text-xl">✦</div>
              <div>
                <h1 className="text-stardust-300 text-lg font-medium">世界观工坊</h1>
                <p className="text-void-500 text-sm">
                  IP Code: {ipCode || 'Loading...'} · Graph: {graphCode || '待定稿'}
                </p>
              </div>
            </div>
            <div className="flex gap-4">
              <button
                onClick={returnToChat}
                className="text-void-400 hover:text-stardust-300 transition-colors"
              >
                ← 返回继续深化设定
              </button>
              <button
                onClick={() => window.location.href = `/a1/poster?fileId=${fileId}`}
                className="text-stardust-300 hover:text-stardust-200 transition-colors"
              >
                查看完整展示板 →
              </button>
            </div>
          </div>
        </div>
        
        <GraphViewContent fileId={fileId} returnToChat={returnToChat} graphCode={graphCode} fileStatus={file?.status} />
      </div>
    );
  };

  return (
    <div>
      {workspaceState === 'seed_selector' && renderSeedSelector()}
      {workspaceState === 'guided_chat' && renderGuidedChat()}
      {workspaceState === 'graph_view' && renderGraphView()}
    </div>
  );
}

// Graph View Content Component with Tabs
// Defined OUTSIDE A1Workspace to prevent remount on every parent re-render
// (inner component definition causes React to treat each render as a new component type)
function GraphViewContent({
  fileId,
  returnToChat,
  graphCode,
  fileStatus,
}: {
  fileId: string;
  returnToChat: () => void;
  graphCode: string | null;
  fileStatus: string | undefined;
}) {
  const [activeTab, setActiveTab] = useState<'graph' | 'poster'>('graph');
  const [localFileData, setLocalFileData] = useState<FileData | null>(null);

  // Load file data when component mounts
  useEffect(() => {
    if (fileId) {
      fetchJson<FileData>(`/api/a1/file/${fileId}`)
        .then((data) => {
          setLocalFileData(data);
        })
        .catch((err) => {
          console.error('Failed to load file data:', err);
        });
    }
  }, [fileId]);

  // Stable prop identities: useMemo prevents new []/{} on each render
  const stableOpenQuestions = useMemo(() => localFileData?.open_questions ?? [], [localFileData]);
  const stableRejectedEdges = useMemo(() => localFileData?.rejected_edges ?? {}, [localFileData]);

  return (
    <div className="max-w-7xl mx-auto">
      {/* Tab Navigation */}
      <div className="flex gap-4 border-b border-white/5 bg-space-900/30 backdrop-blur-sm">
        <button
          onClick={() => setActiveTab('graph')}
          className={`px-6 py-3 font-medium transition-colors border-b-2 -mb-px ${
            activeTab === 'graph'
              ? 'border-stardust-400 text-stardust-300'
              : 'border-transparent text-void-400 hover:text-stardust-300'
          }`}
        >
          知识图谱
        </button>
        <button
          onClick={() => setActiveTab('poster')}
          className={`px-6 py-3 font-medium transition-colors border-b-2 -mb-px ${
            activeTab === 'poster'
              ? 'border-stardust-400 text-stardust-300'
              : 'border-transparent text-void-400 hover:text-stardust-300'
          }`}
        >
          展板预览
        </button>
      </div>

      {/* Tab Content */}
      <div className="p-8">
        {activeTab === 'graph' && (
          <A1GraphSection
            fileId={fileId}
            returnToChat={returnToChat}
            version={graphCode ? parseInt(graphCode.split('_')[1]?.replace('v', '') || '1', 10) : 1}
            isStale={fileStatus === 'draft' && graphCode !== null}
            openQuestions={stableOpenQuestions}
            rejectedEdges={stableRejectedEdges}
          />
        )}
        {activeTab === 'poster' && <PosterPreview fileId={fileId} />}
      </div>
    </div>
  );
}

// Poster Preview Component
function PosterPreview({ fileId }: { fileId: string }) {
  const [posterData, setPosterData] = useState<PosterResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [visualBgIndex, setVisualBgIndex] = useState(0);
  
  useEffect(() => {
    fetchJson<PosterResponse>(`/api/a1/file/${fileId}/poster`)
      .then((data: PosterResponse) => {
        setPosterData(data);
        setIsLoading(false);
      })
      .catch((err: Error) => {
        console.error('Failed to load poster:', err);
        setError('加载展示板失败');
        setIsLoading(false);
      });
  }, [fileId]);

  // Carousel effect
  useEffect(() => {
    if (!posterData || posterData.visual_bg_status !== 'completed' || posterData.visual_bg_images.length === 0) return;
    const interval = setInterval(() => {
      setVisualBgIndex((prev) => (prev + 1) % posterData.visual_bg_images.length);
    }, 5000);
    return () => clearInterval(interval);
  }, [posterData]);
  
  if (isLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-stardust-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-stardust-300">加载展示板中...</p>
        </div>
      </div>
    );
  }
  
  if (error || !posterData) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="glass-panel p-8 bg-cosmos-error/10 border-cosmos-error/30">
          <p className="text-cosmos-error">{error || '加载失败'}</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="relative">
      {/* 背景图轮播层 */}
      {posterData.visual_bg_status === 'completed' && posterData.visual_bg_images.length > 0 && (
        <div className="absolute inset-0 z-0 overflow-hidden">
          {posterData.visual_bg_images.map((image, index) => (
            <div
              key={image.filename}
              className={`absolute inset-0 transition-opacity duration-1000 ${
                index === visualBgIndex ? 'opacity-100' : 'opacity-0'
              }`}
            >
              <img
                src={image.url}
                alt={`背景图 ${index + 1}`}
                className="absolute inset-0 w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-b from-space-950/40 via-space-900/20 to-space-950/40" />
            </div>
          ))}
          {/* 轮播指示器 */}
          <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 z-10 flex gap-2">
            {posterData.visual_bg_images.map((image, index) => (
              <div
                key={image.filename}
                className={`w-2 h-2 rounded-full transition-all duration-300 ${
                  index === visualBgIndex ? 'bg-stardust-300 w-4' : 'bg-void-600'
                } ${image.closest && posterData.visual_bg_best === image.filename ? 'ring-2 ring-stardust-400' : ''}`}
              />
            ))}
          </div>
        </div>
      )}
      {/* 前景：内容面板（glass-panel 已在 theme.css 降到 0.3 透明度让背景图透出） */}
      <div className="relative z-10">
        <PosterBoard panels={posterData.panels} className="min-h-[60vh]" transparent />
      </div>
    </div>
  );
}