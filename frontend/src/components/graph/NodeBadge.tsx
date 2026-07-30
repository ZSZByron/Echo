/**
 * NodeBadge component for displaying graph node lifecycle status.
 *
 * Shows compact status badges with different colors and styles for each state:
 * - pending: Gray, neutral state
 * - generating: Blue, active processing state
 * - completed: Green, successful completion
 * - failed: Red, error state
 *
 * Follows cyberpunk aesthetic with neon colors and glow effects.
 */

import type { NodeStatus } from "../../types/graph";

interface NodeBadgeProps {
  /** Node status to display */
  status: NodeStatus;
  /** Optional CSS class name for styling overrides */
  className?: string;
}

/**
 * Map status to Tailwind color classes and display text.
 */
const STATUS_CONFIG: Record<
  NodeStatus,
  { bg: string; text: string; glow: string; label: string }
> = {
  pending: {
    bg: "bg-gray-700",
    text: "text-gray-300",
    glow: "text-glow-gray",
    label: "Pending",
  },
  generating: {
    bg: "bg-blue-900",
    text: "text-neon-cyan",
    glow: "text-glow-cyan",
    label: "Generating",
  },
  completed: {
    bg: "bg-green-900",
    text: "text-neon-green",
    glow: "text-glow-green",
    label: "Completed",
  },
  failed: {
    bg: "bg-red-900",
    text: "text-neon-red",
    glow: "text-glow-red",
    label: "Failed",
  },
};

export function NodeBadge({ status, className = "" }: NodeBadgeProps) {
  const config = STATUS_CONFIG[status];

  return (
    <span
      className={`inline-flex items-center px-2 py-1 rounded-md border ${config.bg} ${config.text} ${config.glow} border-opacity-50 text-xs font-mono uppercase tracking-wider ${className}`}
      style={{
        borderColor: `var(--color-${status === "generating" ? "cyan" : status === "completed" ? "green" : status === "failed" ? "red" : "gray"})`,
      }}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
          status === "pending"
            ? "bg-gray-400"
            : status === "generating"
            ? "bg-neon-cyan animate-pulse"
            : status === "completed"
            ? "bg-neon-green"
            : "bg-neon-red"
        }`}
      />
      {config.label}
    </span>
  );
}
