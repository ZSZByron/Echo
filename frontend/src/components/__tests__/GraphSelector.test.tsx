// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { GraphSelector } from "../graph/GraphSelector";
import '@testing-library/jest-dom/vitest';

describe("GraphSelector", () => {
  const mockGraphs = [
    {
      graph_id: "graph-1",
      graph_code: "WORLD-001",
      status: "finalized" as const,
    },
    {
      graph_id: "graph-2",
      graph_code: "STORY-002",
      status: "stale" as const,
      change_set: {
        diff_summary: "Added 3 new nodes. Modified relationship weights.",
        upstream_version: "v1.2.0",
      },
    },
  ];

  it("renders stale badge for stale graphs", () => {
    render(
      <GraphSelector
        graphs={mockGraphs}
        selectedId={null}
        onSelect={vi.fn()}
      />
    );

    const staleBadge = screen.getByText("STALE");
    expect(staleBadge).toBeInTheDocument();
    expect(staleBadge).toHaveClass(
      "bg-yellow-900/50",
      "text-yellow-300"
    );
  });

  it("shows change set preview when clicking stale graph", () => {
    const onStaleChoose = vi.fn();
    render(
      <GraphSelector
        graphs={mockGraphs}
        selectedId={null}
        onSelect={vi.fn()}
        onUseStale={onStaleChoose}
      />
    );

    // Click on stale graph
    const staleGraph = screen.getByText("STORY-002").closest("div");
    fireEvent.click(staleGraph!);

    // Should show confirmation dialog
    expect(screen.getByText(/This graph is stale/)).toBeInTheDocument();
    expect(screen.getByText(/Use with Trace/)).toBeInTheDocument();
  });

  it("calls onUseStale with 'leave_trace' action when clicking Use with Trace", () => {
    const onUseStale = vi.fn();
    render(
      <GraphSelector
        graphs={mockGraphs}
        selectedId={null}
        onSelect={vi.fn()}
        onUseStale={onUseStale}
      />
    );

    // Click on stale graph to open dialog
    const staleGraph = screen.getByText("STORY-002").closest("div");
    fireEvent.click(staleGraph!);

    // Click "Use with Trace" button
    const useButton = screen.getByText("Use with Trace");
    fireEvent.click(useButton);

    expect(onUseStale).toHaveBeenCalledWith("graph-2", "leave_trace");
  });

  it("calls onUseStale with 'regenerate' action when clicking Regenerate", () => {
    const onUseStale = vi.fn();
    render(
      <GraphSelector
        graphs={mockGraphs}
        selectedId={null}
        onSelect={vi.fn()}
        onUseStale={onUseStale}
      />
    );

    // Click on stale graph to open dialog
    const staleGraph = screen.getByText("STORY-002").closest("div");
    fireEvent.click(staleGraph!);

    // Click "Regenerate" button
    const regenerateButton = screen.getByText("Regenerate");
    fireEvent.click(regenerateButton);

    expect(onUseStale).toHaveBeenCalledWith("graph-2", "regenerate");
  });

  it("calls onSelect directly for non-stale graphs", () => {
    const onSelect = vi.fn();
    render(
      <GraphSelector
        graphs={mockGraphs}
        selectedId={null}
        onSelect={onSelect}
      />
    );

    // Click on current (non-stale) graph
    const currentGraph = screen.getByText("WORLD-001").closest("div");
    fireEvent.click(currentGraph!);

    expect(onSelect).toHaveBeenCalledWith("graph-1");
  });

  it("highlights selected graph", () => {
    render(
      <GraphSelector
        graphs={mockGraphs}
        selectedId="graph-1"
        onSelect={vi.fn()}
      />
    );

    const selectedGraph = screen.getByText("WORLD-001").closest(".p-4");
    expect(selectedGraph).toHaveClass("border-indigo-500");
  });
});
