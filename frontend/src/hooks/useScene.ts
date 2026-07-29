import { useCallback, useEffect, useRef, useState } from 'react';
import type { SceneResponse } from '../types/scene';

const SCENE_ENDPOINT = '/api/scene?scene_id=temple_ruins';
const TIMEOUT_MS = 30000;
const ASSETS_CHANGED_EVENT = 'echo-assets-changed';
const DEBOUNCE_MS = 500;

export interface UseSceneResult {
  scene: SceneResponse | null;
  loading: boolean;
  error: string | null;
}

/**
 * Fetches the active scene on mount. Re-fetches when an 'echo-assets-changed'
 * CustomEvent is dispatched on `window` (e.g. after asset approve/reject/generate).
 * Uses debounce to coalesce rapid events (e.g. bulk-approve).
 * On refresh failure, keeps the previous scene data.
 */
export function useScene(): UseSceneResult {
  const [scene, setScene] = useState<SceneResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const fetchingRef = useRef(false);

  const fetchScene = useCallback(async (isInitial: boolean) => {
    if (fetchingRef.current) return;
    fetchingRef.current = true;

    if (isInitial) setLoading(true);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);

    try {
      const res = await fetch(SCENE_ENDPOINT, { signal: controller.signal });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: SceneResponse = await res.json();
      setScene(data);
      setError(null);
    } catch (err) {
      if (controller.signal.aborted) {
        fetchingRef.current = false;
        return;
      }
      // On refresh failure, keep old scene data; on initial load, surface the error
      if (isInitial) {
        setError(err instanceof Error ? err.message : 'Failed to load scene');
      }
    } finally {
      clearTimeout(timeout);
      setLoading(false);
      fetchingRef.current = false;
    }
  }, []);

  // Initial load
  useEffect(() => {
    void fetchScene(true);
  }, [fetchScene]);

  // Listen for asset-changed events with debounce
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | null = null;

    const handler = () => {
      if (timer !== null) clearTimeout(timer);
      timer = setTimeout(() => {
        void fetchScene(false);
      }, DEBOUNCE_MS);
    };

    window.addEventListener(ASSETS_CHANGED_EVENT, handler);
    return () => {
      window.removeEventListener(ASSETS_CHANGED_EVENT, handler);
      if (timer !== null) clearTimeout(timer);
    };
  }, [fetchScene]);

  return { scene, loading, error };
}
