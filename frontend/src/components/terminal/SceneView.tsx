/**
 * SceneView — fullscreen scene container.
 *
 * Parent controls overall positioning (relative/fixed); this component fills
 * its bounding box with absolute inset-0 at z-0 so terminal/status panels
 * can layer above it.
 *
 * Background: <img> when background_asset present, else AssetPlaceholder.
 * Objects: mapped to <SceneObject> with click wiring passed through.
 */

import { useState } from 'react';
import { useScene } from '../../hooks/useScene';
import { AssetPlaceholder } from '../shared/AssetPlaceholder';
import { SceneObject } from './SceneObject';

export interface SceneViewProps {
  /** Forwarded to SceneObject onClick. T6 wires this to the input bar. */
  onObjectClick?: (objectId: string, objectName: string, isPrimary: boolean) => void;
  className?: string;
}

export function SceneView({ onObjectClick, className = '' }: SceneViewProps) {
  const { scene, loading, error } = useScene();
  const [bgBroken, setBgBroken] = useState(false);

  const hasBackground = scene?.background_asset && !bgBroken;

  return (
    <div className={`absolute inset-0 z-0 overflow-hidden ${className}`}>
      {/* Background layer */}
      {hasBackground ? (
        <img
          src={scene!.background_asset as string}
          alt={scene?.name ?? '场景背景'}
          className="w-full h-full object-cover"
          onError={() => setBgBroken(true)}
        />
      ) : (
        <AssetPlaceholder mode="background" />
      )}

      {/* Objects layer */}
      {scene?.objects?.map((obj) => (
        <SceneObject key={obj.id} object={obj} onClick={onObjectClick} />
      ))}

      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <span className="text-neon-cyan animate-pulse font-mono text-sm tracking-widest">
            加载场景中...
          </span>
        </div>
      )}

      {/* Error overlay — keep placeholder bg visible, surface neon-red notice */}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <span className="text-neon-red font-mono text-sm tracking-widest text-glow-red">
            场景加载失败: {error}
          </span>
        </div>
      )}
    </div>
  );
}
