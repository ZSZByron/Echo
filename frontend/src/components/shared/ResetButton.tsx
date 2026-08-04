import { useGameDispatch } from '../../hooks/useGameState';
import { apiClient } from '../../api/client';

export function ResetButton() {
  const dispatch = useGameDispatch();

  const handleReset = async () => {
    const confirmed = confirm('确定要重置游戏状态吗？此操作无法撤销。');
    if (!confirmed) return;

    // Call backend reset
    const newState = await apiClient.reset();

    // Clear history
    dispatch({ type: 'CLEAR_HISTORY' });

    // Reset god watch level
    dispatch({ type: 'SET_GOD_WATCH', payload: 0 });

    // Reset latest judgment
    dispatch({ type: 'SET_LATEST_JUDGMENT', payload: null });

    // Update player state from backend response
    dispatch({ type: 'SET_PLAYER_STATE', payload: newState });
  };

  return (
    <button
      onClick={handleReset}
      className="px-4 py-2 bg-neon-red text-black font-mono rounded hover:bg-red-600 transition-colors"
    >
      重置系统
    </button>
  );
}
