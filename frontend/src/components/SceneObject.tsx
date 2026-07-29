/**
 * SceneObject — a positioned sprite within a SceneView.
 *
 * Primary objects glow cyan on hover and sit above secondary objects (z-10).
 * Secondary objects render at reduced opacity without glow.
 * Asset fallback handled by AssetPlaceholder when img is missing or errors.
 */

import { useState } from 'react';
import type { SceneObjectDTO } from '../types/scene';
import { AssetPlaceholder } from './AssetPlaceholder';

export interface SceneObjectProps {
  object: SceneObjectDTO;
  onClick?: (objectId: string, objectName: string, isPrimary: boolean) => void;
  className?: string;
}

export function SceneObject({ object, onClick, className = '' }: SceneObjectProps) {
  const [assetBroken, setAssetBroken] = useState(false);
  const hasAsset = object.asset !== null && !assetBroken;
  const isHolographic = object.id.includes('holographic_altar');

  const positionStyle: React.CSSProperties = {
    left: `${object.position.x}%`,
    top: `${object.position.y}%`,
    transform: 'translate(-50%, -50%)',
    ...(isHolographic ? { mixBlendMode: 'screen' as const } : {}),
  };

  const stateClasses = object.is_primary
    ? 'z-10 cursor-pointer hover:shadow-[0_0_20px_#00ffff] hover:scale-105 transition-all duration-200'
    : 'opacity-70 hover:opacity-90 transition-opacity';

  const handleClick = () => {
    onClick?.(object.id, object.name, object.is_primary);
  };

  return (
    <div
      className={`absolute flex flex-col items-center justify-center ${stateClasses} ${className}`}
      style={positionStyle}
      onClick={handleClick}
      role={object.is_primary ? 'button' : undefined}
      aria-label={object.name}
    >
      {hasAsset ? (
        <img
          src={object.asset as string}
          alt={object.name}
          className="max-w-[120px] max-h-[120px] object-contain"
          onError={() => setAssetBroken(true)}
        />
      ) : (
        <AssetPlaceholder mode="object" name={object.name} type={object.type} />
      )}
    </div>
  );
}
