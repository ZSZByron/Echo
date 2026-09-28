// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DimensionProgress } from "../structured/DimensionProgress";

describe("DimensionProgress", () => {
  const mockSections = [
    { id: "1", label: "World Building", done: true },
    { id: "2", label: "Character Design", done: true },
    { id: "3", label: "Plot Structure", done: false },
    { id: "4", label: "Scene Mapping", done: false },
  ];

  const tenModuleSections = [
    { id: "1", label: "IP定位", done: true, done_fields: 3, total_fields: 5 },
    { id: "2", label: "世界本体", done: true, done_fields: 2, total_fields: 4 },
    { id: "3", label: "力量体系", done: false, done_fields: 1, total_fields: 6 },
    { id: "4", label: "地理空间", done: false, done_fields: 0, total_fields: 5 },
    { id: "5", label: "文明与社会", done: false, done_fields: 0, total_fields: 4 },
    { id: "6", label: "历史时间线", done: false, done_fields: 0, total_fields: 3 },
    { id: "7", label: "视觉设计", done: false, done_fields: 0, total_fields: 4 },
    { id: "8", label: "玩法设计DNA", done: false, done_fields: 0, total_fields: 5 },
    { id: "9", label: "骰子设定", done: false, done_fields: 0, total_fields: 3 },
    { id: "10", label: "设定边界", done: false, done_fields: 0, total_fields: 2 },
  ];

  // T5: 3/7 fixture — non-10 total guards against hardcoded /10 assumptions
  const sevenSections = [
    { id: "1", label: "IP定位", done: true },
    { id: "2", label: "世界本体", done: true },
    { id: "3", label: "力量体系", done: true },
    { id: "4", label: "地理空间", done: false },
    { id: "5", label: "文明与社会", done: false },
    { id: "6", label: "历史时间线", done: false },
    { id: "7", label: "视觉设计", done: false },
  ];

  it("renders plain progress label 聊聊你的世界 3/7 for a 7-section fixture", () => {
    render(<DimensionProgress sections={sevenSections} />);

    expect(screen.getByText(/聊聊你的世界 3\/7/)).toBeInTheDocument();
  });

  it("renders zero module label text (no leakage of module names)", () => {
    render(<DimensionProgress sections={tenModuleSections} />);

    expect(screen.queryByText("IP定位")).not.toBeInTheDocument();
    expect(screen.queryByText("历史时间线")).not.toBeInTheDocument();
    expect(screen.queryByText("世界本体")).not.toBeInTheDocument();
    const { container } = render(<DimensionProgress sections={tenModuleSections} />);
    expect(container.textContent).not.toContain("IP定位");
    expect(container.textContent).not.toContain("历史时间线");
  });

  it("renders one cell per section (count derived from sections.length, not hardcoded 10)", () => {
    const { container } = render(<DimensionProgress sections={sevenSections} />);

    const cells = container.querySelectorAll("[data-progress-cell]");
    expect(cells).toHaveLength(7);
  });

  it("preserves done/undone cell visual distinction", () => {
    const { container } = render(<DimensionProgress sections={sevenSections} />);

    const cells = container.querySelectorAll("[data-progress-cell]");
    expect(cells[0].className).toContain("bg-stardust-400");
    expect(cells[6].className).not.toContain("bg-stardust-400");
  });

  it("displays correct completion count", () => {
    render(<DimensionProgress sections={mockSections} />);

    expect(screen.getByText(/聊聊你的世界 2\/4/)).toBeInTheDocument();
  });

  it("handles empty sections array", () => {
    render(<DimensionProgress sections={[]} />);

    expect(screen.getByText(/聊聊你的世界 0\/0/)).toBeInTheDocument();
  });

  it("applies glow-starlight class to the progress count", () => {
    const { container } = render(
      <DimensionProgress sections={mockSections} />
    );

    const glowElement = container.querySelector(".glow-starlight");
    expect(glowElement).toBeInTheDocument();
  });

  // New tests for two-level structure with subs
  const mockSectionsWithSubs = [
    { 
      id: "1", 
      label: "IP定位", 
      done: true,
      subs: [
        { id: "1-1", label: "核心概念", done: true },
        { id: "1-2", label: "目标受众", done: true }
      ]
    },
    { 
      id: "2", 
      label: "世界本体", 
      done: true,
      subs: [
        { id: "2-1", label: "物理法则", done: true },
        { id: "2-2", label: "魔法系统", done: false }
      ]
    },
  ];

  it("renders count and no labels for sections with subs", () => {
    const { container } = render(<DimensionProgress sections={mockSectionsWithSubs} />);

    expect(screen.getByText(/聊聊你的世界 2\/2/)).toBeInTheDocument();
    expect(container.textContent).not.toContain("IP定位");
    expect(container.textContent).not.toContain("核心概念");
  });
});
