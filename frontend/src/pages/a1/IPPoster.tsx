/**
 * IPPoster Page
 *
 * Full-screen poster display page with back navigation to A1 workspace.
 * Receives fileId from location.state or fetches from URL param.
 */

import { useState, useEffect } from 'react';
import { fetchJson } from '../../api/client';
import { PosterBoard } from '../../components/poster/PosterBoard';
import '../../components/theme.css';

interface PosterResponse {
  panels: Array<{ id: string; title: string; content: string }>;
  ai_image_prompt: string;
  ai_image_status: string;
}

export function IPPoster() {
  const [posterData, setPosterData] = useState<PosterResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Get fileId from URL search params
  const getFileId = (): string | null => {
    const params = new URLSearchParams(window.location.search);
    return params.get('fileId');
  };
  
  const fileId = getFileId();
  
  useEffect(() => {
    if (!fileId) {
      setError('No file ID provided');
      setIsLoading(false);
      return;
    }
    
    fetchJson<PosterResponse>(`/api/a1/file/${fileId}/poster`)
      .then((data: PosterResponse) => {
        setPosterData(data);
        setIsLoading(false);
      })
      .catch((err: Error) => {
        console.error('Failed to load poster:', err);
        setError('Failed to load poster data');
        setIsLoading(false);
      });
  }, [fileId]);
  
  const handleBackToWorkspace = () => {
    window.location.href = '/a1';
  };
  
  if (isLoading) {
    return (
      <div className="min-h-screen starry-gradient flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-stardust-400 border-t-transparent rounded-full animate-spin mx-auto mb-6" />
          <p className="text-stardust-300 text-lg">Loading poster...</p>
          <p className="text-void-500 text-sm mt-2">Preparing your IP showcase</p>
        </div>
      </div>
    );
  }
  
  if (error || !posterData) {
    return (
      <div className="min-h-screen starry-gradient flex items-center justify-center p-8">
        <div className="glass-panel max-w-2xl w-full p-8 bg-cosmos-error/10 border-cosmos-error/30">
          <h2 className="text-cosmos-error text-xl font-medium mb-4">Failed to Load Poster</h2>
          <p className="text-gray-300 mb-6">{error || 'Unable to load poster data'}</p>
          <button
            onClick={handleBackToWorkspace}
            className="bg-stardust-400 text-space-950 px-6 py-3 rounded-lg font-medium hover:bg-stardust-300 transition-colors"
          >
            Return to Workspace
          </button>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen starry-gradient relative">
      {/* Top Navigation Bar */}
      <div className="absolute top-0 left-0 right-0 z-20 glass-panel border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="text-stardust-400 text-2xl animate-twinkle">✦</div>
            <div>
              <h1 className="text-stardust-300 text-xl font-medium glow-starlight">IP Poster</h1>
              <p className="text-void-500 text-sm">Full showcase display</p>
            </div>
          </div>
          
          <button
            onClick={handleBackToWorkspace}
            className="flex items-center gap-2 text-stardust-300 hover:text-stardust-200 transition-colors px-4 py-2 rounded-lg hover:bg-white/5"
          >
            <span>←</span>
            <span>Back to Workspace</span>
          </button>
        </div>
      </div>
      
      {/* Full-screen Poster Board */}
      <div className="pt-20">
        <PosterBoard
          panels={posterData.panels}
          className="min-h-screen"
        />
      </div>
      
      {/* AI Image Status Indicator */}
      {posterData.ai_image_status && (
        <div className="absolute bottom-6 right-6 z-20 glass-panel px-4 py-3">
          <div className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full ${
              posterData.ai_image_status === 'completed' 
                ? 'bg-cosmos-success glow-success' 
                : posterData.ai_image_status === 'generating'
                ? 'bg-cosmos-warning animate-pulse'
                : 'bg-void-600'
            }`} />
            <div className="text-right">
              <div className="text-stardust-300 text-xs font-medium">AI Image</div>
              <div className="text-void-500 text-xs capitalize">{posterData.ai_image_status}</div>
            </div>
          </div>
        </div>
      )}
      
      {/* Bottom Gradient Fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-space-950 to-transparent pointer-events-none" />
    </div>
  );
}