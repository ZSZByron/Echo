import { useEffect, useState } from 'react';
import { GameStateProvider, useGameDispatch } from './hooks/useGameState';
import { Terminal } from './components/Terminal';
import { StatusPanel } from './components/StatusPanel';
import { GodWatchIndicator } from './components/GodWatchIndicator';
import { ResetButton } from './components/ResetButton';
import { SceneView } from './components/SceneView';
import { AssetReview } from './pages/AssetReview';
import { GraphAssetReview } from './pages/GraphAssetReview';
import GraphEditorWrapper from './pages/GraphEditor';
import { apiClient } from './api/client';

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
  const [pendingInput, setPendingInput] = useState('');

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

export default App;
