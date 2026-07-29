import { createContext, useContext, useReducer, useCallback } from 'react';
import React from 'react';
import type { ReactNode, Context, Dispatch } from 'react';
import type { PlayerState } from '../types/player';

interface TerminalLine {
  id: string;
  type: 'player' | 'system' | 'narrative' | 'error' | 'echo';
  text: string;
  timestamp: number;
}

interface GameState {
  playerState: PlayerState | null;
  history: TerminalLine[];
  godWatchLevel: number;
  latestJudgment: any | null;
  availableActions: string[];
}

type GameAction =
  | { type: 'SET_PLAYER_STATE'; payload: PlayerState }
  | { type: 'ADD_LINE'; payload: TerminalLine }
  | { type: 'CLEAR_HISTORY' }
  | { type: 'SET_GOD_WATCH'; payload: number }
  | { type: 'SET_LATEST_JUDGMENT'; payload: any }
  | { type: 'SET_AVAILABLE_ACTIONS'; payload: string[] };

const initialState: GameState = {
  playerState: null,
  history: [],
  godWatchLevel: 0,
  latestJudgment: null,
  availableActions: [],
};

function gameReducer(state: GameState, action: GameAction): GameState {
  switch (action.type) {
    case 'SET_PLAYER_STATE':
      return { ...state, playerState: action.payload };
    case 'ADD_LINE':
      return { ...state, history: [...state.history, action.payload] };
    case 'CLEAR_HISTORY':
      return { ...state, history: [] };
    case 'SET_GOD_WATCH':
      return { ...state, godWatchLevel: action.payload };
    case 'SET_LATEST_JUDGMENT':
      return { ...state, latestJudgment: action.payload };
    case 'SET_AVAILABLE_ACTIONS':
      return { ...state, availableActions: action.payload };
    default:
      return state;
  }
}

// Create contexts without complex generics to avoid TypeScript parsing issues
const createGameContext = (): Context<GameState | null> => {
  return createContext<GameState | null>(null);
};

const createGameDispatchContext = (): Context<Dispatch<GameAction> | null> => {
  return createContext<Dispatch<GameAction> | null>(null);
};

const GameContext = createGameContext();
const GameDispatchContext = createGameDispatchContext();

export function GameStateProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(gameReducer, initialState);

  return React.createElement(GameContext.Provider, { value: state },
    React.createElement(GameDispatchContext.Provider, { value: dispatch }, children)
  );
}

export function useGameState() {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error('useGameState must be used within GameStateProvider');
  }
  return context;
}

export function useGameDispatch() {
  const context = useContext(GameDispatchContext);
  if (!context) {
    throw new Error('useGameDispatch must be used within GameStateProvider');
  }
  return context;
}

// Helper hooks for specific actions
export function useAddLine() {
  const dispatch = useGameDispatch();
  return useCallback((line: Omit<TerminalLine, 'id' | 'timestamp'>) => {
    dispatch({
      type: 'ADD_LINE',
      payload: {
        ...line,
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        timestamp: Date.now(),
      },
    });
  }, [dispatch]);
}
