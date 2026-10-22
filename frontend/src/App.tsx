import { useEffect, useState } from 'react';
import { GameStateProvider, useGameDispatch } from './hooks/useGameState';
import { Terminal } from './components/terminal/Terminal';
import { StatusPanel } from './components/terminal/StatusPanel';
import { GodWatchIndicator } from './components/terminal/GodWatchIndicator';
import { ResetButton } from './components/shared/ResetButton';
import { SceneView } from './components/terminal/SceneView';
import { AssetReview } from './pages/graph/AssetReview';
import { GraphAssetReview } from './pages/graph/GraphAssetReview';
import GraphEditorWrapper from './pages/graph/GraphEditor';
import { apiClient } from './api/client';
import { A1Workspace } from './pages/a1/A1Workspace';
import { IPPoster } from './pages/a1/IPPoster';

function App() {
  return (
    <GameStateProvider>
      <AppContent />
    </GameStateProvider>
  );
}

function AppContent() {
  const dispatch = useGameDispatch();
  const isAdmin = window.location.pathname.startsWith('/admin/assets');
  const isGraphAssets = window.location.pathname.startsWith('/admin/graph-assets');
  const isGraphEditor = window.location.pathname.startsWith('/graph/editor');
  const isA1Poster = window.location.pathname.startsWith('/a1v2/poster');
  // 注意前缀陷阱：'/a1v1'.startsWith('/a1') === true，禁止裸 startsWith('/a1')
  const isA1Workspace = (window.location.pathname.startsWith('/a1v1') || window.location.pathname.startsWith('/a1v2')) && !isA1Poster;
  const isA0Demo = window.location.pathname.startsWith('/a0');
  const [pendingInput, setPendingInput] = useState('');

  // 未匹配任何已知路由（含 / 与旧 /a1）：replace 到主线入口，不留历史记录
  useEffect(() => {
    if (!isAdmin && !isGraphAssets && !isGraphEditor && !isA1Poster && !isA1Workspace && !isA0Demo) {
      window.location.replace('/a1v2');
    }
  }, [isAdmin, isGraphAssets, isGraphEditor, isA1Poster, isA1Workspace, isA0Demo]);

  const handleObjectClick = (objectId: string, objectName: string, isPrimary: boolean) => {
    const text = isPrimary
      ? `检查 ${objectName}（${objectId}）`
      : `查看 ${objectName}`;
    setPendingInput(text);
  };

  useEffect(() => {
    // Initialize player state on mount
    const initializeState = async () => {
      try {
        const state = await apiClient.getState();
        dispatch({ type: 'SET_PLAYER_STATE', payload: state });
      } catch (error) {
        console.error('Failed to initialize state:', error);
      }
    };
    initializeState();
  }, [dispatch]);

  if (isAdmin) {
    return <AssetReview />;
  }

  if (isGraphAssets) {
    return <GraphAssetReview />;
  }

  if (isGraphEditor) {
    return <GraphEditorWrapper />;
  }

  if (isA1Poster) {
    return <IPPoster />;
  }

  if (isA1Workspace) {
    return <A1Workspace />;
  }

  if (isA0Demo) {
    return (
      <div className="relative min-h-screen w-screen overflow-hidden bg-black text-neon-green font-mono">
      {/* Scene background layer (z-0) */}
      <SceneView onObjectClick={handleObjectClick} />

      {/* God watch full-screen overlay (z-50, pointer-events-none) */}
      <GodWatchIndicator />

      {/* Top bar overlay (z-20) — title + reset, leaves right 320px for status panel */}
      <div className="absolute top-0 left-0 right-[320px] z-20 flex justify-between items-center p-3 bg-black/70 backdrop-blur-sm border-b border-neon-green">
        <h1 className="text-2xl text-neon-cyan text-glow-cyan">回声终端</h1>
        <ResetButton />
      </div>

      {/* Terminal overlay (z-20) — bottom 45%, leaves right 320px for status panel */}
      <div
        className="absolute bottom-0 left-0 right-[320px] z-20 bg-black/70 backdrop-blur-sm border-t border-neon-green"
        style={{ height: '45%' }}
      >
        <Terminal
          pendingInput={pendingInput}
          onPendingInputConsumed={() => setPendingInput('')}
        />
      </div>

      {/* Status panel overlay (z-20) — right 300px full-height */}
      <div className="absolute top-0 right-0 w-[300px] h-full z-20 bg-black/70 backdrop-blur-sm border-l border-neon-green">
        <StatusPanel />
      </div>
      </div>
    );
  }

  // 未知路径（含 / 与旧 /a1）：渲染空 + useEffect 重定向到 /a1v2
  return null;
}

export default App;
