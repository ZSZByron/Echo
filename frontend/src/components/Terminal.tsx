import { useState, useRef, useEffect } from 'react';
import { useAction } from '../hooks/useAction';
import { useGameState, useAddLine, useGameDispatch } from '../hooks/useGameState';
import { TypewriterText } from './TypewriterText';
import { ActionHints } from './ActionHints';

export interface TerminalProps {
  /** Prefilled input text from scene object click; player still presses Enter manually. */
  pendingInput?: string;
  /** Called after pendingInput is consumed so parent can clear its state. */
  onPendingInputConsumed?: () => void;
}

export function Terminal({ pendingInput, onPendingInputConsumed }: TerminalProps) {
  const [input, setInput] = useState('');
  const { loading, error, submitAction, reset } = useAction();
  const { history, availableActions } = useGameState();
  const addLine = useAddLine();
  const dispatch = useGameDispatch();
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when history changes
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history]);

  // Sync pendingInput (from scene object click) into the input bar without submitting.
  useEffect(() => {
    if (pendingInput) {
      setInput(pendingInput);
      if (inputRef.current) {
        inputRef.current.focus();
      }
      onPendingInputConsumed?.();
    }
  }, [pendingInput, onPendingInputConsumed]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const playerInput = input.trim();
    setInput('');

    // Add player input to history
    addLine({ type: 'player', text: `> ${playerInput}` });

    // Submit action
    const result = await submitAction(playerInput);

    if (result) {
      // Update player state from response
      dispatch({ type: 'SET_PLAYER_STATE', payload: result.updated_state });

      // Update latest judgment for god watch indicator
      dispatch({ type: 'SET_LATEST_JUDGMENT', payload: result.judgment });

      // Calculate god watch level from god_intervention
      if (result.judgment.god_intervention) {
        const interventionLevel = result.judgment.god_intervention.length > 30 ? 3 :
                                  result.judgment.god_intervention.length > 15 ? 2 : 1;
        dispatch({ type: 'SET_GOD_WATCH', payload: interventionLevel });
      } else {
        dispatch({ type: 'SET_GOD_WATCH', payload: 0 });
      }

      // Add narrative response
      addLine({ type: 'narrative', text: result.narrative });

      // Add echo vision line if present
      if (result.echo_vision) {
        addLine({ type: 'echo', text: result.echo_vision });
      }

      // Store available actions for hint display
      dispatch({ type: 'SET_AVAILABLE_ACTIONS', payload: result.available_actions });

      // Add system message for judgment result
      if (result.judgment.result === 'fail') {
        addLine({ type: 'system', text: `[SYSTEM: Action failed - ${result.judgment.reason}]` });
      } else if (result.judgment.god_intervention) {
        addLine({ type: 'system', text: `[WARNING: GOD INTERVENTION - ${result.judgment.god_intervention}]` });
      }
    } else if (error) {
      addLine({ type: 'error', text: `[ERROR: ${error}]` });
    }
  };

  const handleReset = async () => {
    await reset();
    // Reset will be handled by the parent or we could add a CLEAR_HISTORY action
  };

  return (
    <div className="flex flex-col h-full w-full p-4">
      {/* Terminal output area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto mb-4 p-4 bg-black border-2 border-neon-green rounded"
        style={{ minHeight: '0' }}
      >
        {history.length === 0 && (
          <div className="text-neon-cyan text-glow-cyan mb-4">
             <TypewriterText
               text="欢迎来到回声终端。请输入指令开始..."
               type="system"
               speed={20}
             />
          </div>
        )}
        {history.map((line) => (
          <div key={line.id} className="mb-2">
            {line.type === 'narrative' ? (
              <TypewriterText text={line.text} type={line.type} speed={15} />
            ) : line.type === 'echo' ? (
              <div
                className="font-mono"
                style={{ color: '#ff00ff', textShadow: '0 0 8px #ff00ff, 0 0 16px #ff0066' }}
              >
                [ECHO VISION] {line.text}
              </div>
            ) : (
              <div
                className={`font-mono ${
                  line.type === 'player'
                    ? 'text-neon-green text-glow-green'
                    : line.type === 'system'
                    ? 'text-neon-cyan text-glow-cyan'
                    : line.type === 'error'
                    ? 'text-neon-red text-glow-red'
                    : 'text-white'
                }`}
              >
                {line.text}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="text-neon-cyan text-glow-cyan animate-pulse">
            {'>'} PROCESSING...
          </div>
        )}
      </div>

      {/* Action hints */}
      <ActionHints
        actions={availableActions}
        onActionClick={(action) => {
          setInput(action);
          inputRef.current?.focus();
        }}
      />

      {/* Input area */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
          className="flex-1 bg-black border-2 border-neon-green text-neon-green p-2 rounded font-mono focus:outline-none focus:border-neon-cyan disabled:opacity-50"
          placeholder="输入指令..."
          autoFocus
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-6 py-2 bg-neon-green text-black font-mono rounded hover:bg-neon-cyan disabled:opacity-50 disabled:cursor-not-allowed"
        >
          提交
        </button>
        <button
          type="button"
          onClick={handleReset}
          disabled={loading}
          className="px-4 py-2 bg-neon-red text-black font-mono rounded hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          重置
        </button>
      </form>
    </div>
  );
}
