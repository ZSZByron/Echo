import { useState, useCallback } from 'react';
import { apiClient } from '../api/client';
import type { ActionResponse } from '../types/api';

export function useAction() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ActionResponse | null>(null);

  const submitAction = useCallback(async (playerInput: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.action({ player_input: playerInput });
      setResponse(result);
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(async () => {
    setLoading(true);
    try {
      await apiClient.reset();
      setResponse(null);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reset failed');
    } finally {
      setLoading(false);
    }
  }, []);

  return { loading, error, response, submitAction, reset };
}
