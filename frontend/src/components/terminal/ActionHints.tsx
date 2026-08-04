interface ActionHintsProps {
  actions: string[];
  onActionClick?: (action: string) => void;
}

export function ActionHints({ actions, onActionClick }: ActionHintsProps) {
  if (!actions || actions.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-1 mb-2">
      <span className="text-neon-green font-mono text-xs mr-1">提示：</span>
      {actions.map((action, idx) => (
        <button
          key={`${action}-${idx}`}
          onClick={() => onActionClick?.(action)}
          className="inline-block px-2 py-1 mr-2 mb-1 text-xs text-neon-cyan border border-neon-cyan/50 rounded hover:bg-neon-cyan/10 hover:border-neon-cyan cursor-pointer transition-colors font-mono"
        >
          {action}
        </button>
      ))}
    </div>
  );
}
