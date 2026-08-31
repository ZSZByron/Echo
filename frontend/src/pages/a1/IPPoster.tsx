/**
 * IPPoster Page
 *
 * Full-screen poster display page with back navigation to A1 workspace.
 * Receives fileId from location.state or fetches from URL param.
 */

import { useState, useEffect } from 'react';
import { fetchJson, ApiError } from '../../api/client';
import { PosterBoard } from '../../components/poster/PosterBoard';
import '../../components/theme.css';

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
  ai_image_url: string | null;
  visual_bg_status: string | null;
  visual_bg_images: VisualBgImage[];
  visual_bg_best: string | null;
  visual_bg_prompt: string | null;
}

export function IPPoster() {
  const [posterData, setPosterData] = useState<PosterResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [visualBgIndex, setVisualBgIndex] = useState(0);
  
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

  // Carousel effect for visual background images
  useEffect(() => {
    // Only start carousel if we have completed visual bg images
    if (!posterData || 
        posterData.visual_bg_status !== 'completed' || 
        posterData.visual_bg_images.length === 0) {
      return;
    }

    const interval = setInterval(() => {
      setVisualBgIndex((prevIndex) => 
        (prevIndex + 1) % posterData.visual_bg_images.length
      );
    }, 5000); // 5 seconds

    return () => clearInterval(interval);
  }, [posterData]);
  
  const handleBackToWorkspace = () => {
    localStorage.setItem('a1_return_intent', 'chat');
    window.location.href = '/a1';
  };

  const handleGenerateImage = async () => {
    if (!fileId || isGenerating) return;

    setIsGenerating(true);
    setGenerateError(null);

    let timeoutId: ReturnType<typeof setTimeout>;

    try {
      // 触发视觉背景预生成（3图+评分，异步后台）
      await fetchJson(`/api/a1/file/${fileId}/visual-bg/pregenerate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        timeoutMs: 10000,
      });

      // 标记为 generating
      setPosterData(prev => prev ? {
        ...prev,
        visual_bg_status: 'generating',
        visual_bg_images: [],
      } : prev);

      // 轮询 poster 状态直到完成或失败
      const poll = async () => {
        try {
          const data = await fetchJson<PosterResponse>(
            `/api/a1/file/${fileId}/poster`
          );
          if (data.visual_bg_status === 'completed' || data.visual_bg_status === 'failed') {
            setPosterData(data);
            setIsGenerating(false);
            if (data.visual_bg_status === 'failed') {
              setGenerateError('背景图生成失败，请检查后端日志');
            }
          } else {
            setPosterData(data);
            timeoutId = setTimeout(poll, 5000);
          }
        } catch {
          timeoutId = setTimeout(poll, 5000);
        }
      };

      timeoutId = setTimeout(poll, 5000);

      // 超时保护（10分钟）
      setTimeout(() => {
        clearTimeout(timeoutId);
        setIsGenerating(false);
        setGenerateError('生成超时（10分钟），请检查后端日志');
      }, 600000);
    } catch (err) {
      const error = err instanceof ApiError ? err : null;
      if (error) {
        if (error.status === 409) {
          setGenerateError('预生成已在进行中，请等待');
        } else if (error.status === 404) {
          setGenerateError('文件未找到，请重新走 A1 流程');
        } else {
          setGenerateError(`触发失败 (HTTP ${error.status})`);
        }
      } else {
        setGenerateError('网络错误');
      }
      console.error('Failed to trigger visual bg:', err);
      setIsGenerating(false);
    }
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
          <h2 className="text-cosmos-error text-xl font-medium mb-4">加载展示板失败</h2>
          <p className="text-gray-300 mb-6">{error || '无法加载展示板数据'}</p>
           <button
             onClick={handleBackToWorkspace}
             className="bg-stardust-400 text-space-950 px-6 py-3 rounded-lg font-medium hover:bg-stardust-300 transition-colors"
           >
             返回世界观工坊（继续深化）
           </button>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen starry-gradient relative">
      {/* Visual Background Carousel Layer */}
      {posterData.visual_bg_status === 'completed' && posterData.visual_bg_images.length > 0 ? (
        <div className="absolute inset-0 z-0">
          {posterData.visual_bg_images.map((image, index) => (
            <div
              key={image.filename}
              className={`absolute inset-0 transition-opacity duration-1000 ${
                index === visualBgIndex ? 'opacity-100' : 'opacity-0'
              }`}
            >
              <img
                src={image.url}
                alt={`Visual Background Candidate ${index + 1}`}
                className="absolute inset-0 w-full h-full object-cover"
              />
              {/* Dark gradient overlay for text readability */}
              <div className="absolute inset-0 bg-gradient-to-b from-space-950/70 via-space-900/50 to-space-950/80 backdrop-blur-sm" />
            </div>
          ))}
          
          {/* Carousel Dot Indicators */}
          <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 z-10 flex gap-2">
            {posterData.visual_bg_images.map((image, index) => (
              <div
                key={image.filename}
                className={`w-2 h-2 rounded-full transition-all duration-300 ${
                  index === visualBgIndex
                    ? 'bg-stardust-300 w-3'
                    : 'bg-void-600 hover:bg-void-500'
                } ${
                  image.closest && posterData.visual_bg_best === image.filename
                    ? 'ring-2 ring-stardust-400 ring-offset-2 ring-offset-space-950'
                    : ''
                }`}
              />
            ))}
          </div>
        </div>
      ) : posterData.visual_bg_status === 'generating' ? (
        <div className="absolute inset-0 z-0 flex items-center justify-center">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-stardust-400 border-t-transparent rounded-full animate-spin mx-auto mb-6" />
            <p className="text-stardust-300 text-lg">背景图预生成中...</p>
            <p className="text-void-500 text-sm mt-2">Preparing visual backgrounds</p>
          </div>
        </div>
      ) : posterData.ai_image_status === 'completed' && posterData.ai_image_url ? (
        <div className="absolute inset-0 z-0">
          <img
            src={posterData.ai_image_url}
            alt="AI Generated Poster Background"
            className="absolute inset-0 w-full h-full object-cover"
          />
          {/* Dark gradient overlay for text readability */}
          <div className="absolute inset-0 bg-gradient-to-b from-space-950/70 via-space-900/50 to-space-950/80 backdrop-blur-sm" />
        </div>
      ) : null}

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
             <span>返回世界观工坊（继续深化）</span>
           </button>
        </div>
      </div>

      {/* Full-screen Poster Board */}
      <div className="pt-20 relative z-10">
        <PosterBoard
          panels={posterData.panels}
          className="min-h-screen"
          transparent
        />
      </div>

      {/* AI Image Generation Button / Status */}
      <div className="absolute bottom-6 right-6 z-20 glass-panel px-4 py-3">
        {posterData.visual_bg_status === 'failed' || posterData.visual_bg_status === null || posterData.visual_bg_images.length === 0 ? (
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <div className={`w-2 h-2 rounded-full ${
                posterData.visual_bg_status === 'failed'
                  ? 'bg-cosmos-error'
                  : posterData.ai_image_status === 'failed'
                  ? 'bg-cosmos-error'
                  : 'bg-void-600'
              }`} />
              <div className="text-right">
                <div className="text-stardust-300 text-xs font-medium">Visual BG</div>
                <div className="text-void-500 text-xs capitalize">
                  {posterData.visual_bg_status || 'pending'}
                </div>
              </div>
            </div>

            {!isGenerating && (
              <button
                onClick={handleGenerateImage}
                className="mt-2 bg-stardust-400 text-space-950 px-4 py-2 rounded-lg font-medium hover:bg-stardust-300 transition-colors text-sm flex items-center justify-center gap-2"
              >
                <span>Generate AI Image</span>
              </button>
            )}

            {isGenerating && (
              <div className="mt-2 flex items-center gap-2 text-stardust-300 text-sm">
                <div className="w-4 h-4 border-2 border-stardust-400 border-t-transparent rounded-full animate-spin" />
                <span>Generating...</span>
              </div>
            )}

            {generateError && (
              <div className="mt-2 text-xs text-cosmos-error bg-cosmos-error/10 px-2 py-1 rounded">
                {generateError}
              </div>
            )}
          </div>
        ) : posterData.visual_bg_status === 'generating' ? (
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-cosmos-warning animate-pulse" />
            <div className="text-right">
              <div className="text-stardust-300 text-xs font-medium">Visual BG</div>
              <div className="text-void-500 text-xs capitalize">generating</div>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-cosmos-success glow-success" />
            <div className="text-right">
              <div className="text-stardust-300 text-xs font-medium">Visual BG</div>
              <div className="text-void-500 text-xs capitalize">
                {posterData.visual_bg_images.length} images
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Gradient Fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-space-950 to-transparent pointer-events-none" />
    </div>
  );
}