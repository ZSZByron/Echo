import { useTypewriter } from '../../hooks/useTypewriter';

interface TypewriterTextProps {
  text: string;
  type?: 'player' | 'system' | 'narrative' | 'error';
  speed?: number;
  onComplete?: () => void;
}

export function TypewriterText({ text, type = 'narrative', speed = 30, onComplete }: TypewriterTextProps) {
  const { displayedText, isTyping, isComplete, skip } = useTypewriter(text, { speed, onComplete });

  const getColorClass = () => {
    switch (type) {
      case 'player':
        return 'text-neon-green text-glow-green';
      case 'system':
        return 'text-neon-cyan text-glow-cyan';
      case 'error':
        return 'text-neon-red text-glow-red';
      case 'narrative':
      default:
        return 'text-white';
    }
  };

  return (
    <span className={`${getColorClass()} font-mono`}>
      {displayedText}
      {isTyping && <span className="animate-pulse">█</span>}
      {!isComplete && isTyping && (
        <button
          onClick={skip}
          className="ml-2 text-xs text-gray-500 hover:text-gray-300 underline"
        >
          [SKIP]
        </button>
      )}
    </span>
  );
}
