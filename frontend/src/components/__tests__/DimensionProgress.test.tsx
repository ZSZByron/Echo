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
    { id: "10", label: "AI生成边界", done: false, done_fields: 0, total_fields: 2 },
  ];

  it("renders 10 grid cells regardless of section count", () => {
    const { container } = render(
      <DimensionProgress sections={mockSections} />
    );

    const gridCells = container.querySelectorAll('.grid-cols-10 > div');
    expect(gridCells).toHaveLength(10);
  });

  it("renders exactly 10 cells for 10 modules (one-to-one mapping)", () => {
    const { container } = render(
      <DimensionProgress sections={tenModuleSections} />
    );

    const gridCells = container.querySelectorAll('.grid-cols-10 > div');
    expect(gridCells).toHaveLength(10);
  });

  it("displays correct completion count", () => {
    render(<DimensionProgress sections={mockSections} />);

    expect(screen.getByText("2/4")).toBeInTheDocument();
    expect(screen.getByText("50% Complete")).toBeInTheDocument();
  });

  it("displays field progress when available", () => {
    render(<DimensionProgress sections={tenModuleSections} />);

    // Check that module names appear (using getAllByText since they appear in multiple places)
    expect(screen.getAllByText("IP定位")).toHaveLength(2); // tooltip + section label
    expect(screen.getAllByText("世界本体")).toHaveLength(2);
    expect(screen.getAllByText("力量体系")).toHaveLength(2);
  });

  it("highlights completed sections with success glow", () => {
    const { container } = render(
      <DimensionProgress sections={mockSections} />
    );

    const completedIndicator = container.querySelector(".bg-cosmos-success");
    expect(completedIndicator).toBeInTheDocument();
  });

  it("shows checkmarks for completed sections", () => {
    render(<DimensionProgress sections={mockSections} />);

    const checkmarks = screen.getAllByText("✓");
    expect(checkmarks).toHaveLength(2);
  });

  it("renders all section labels including Chinese module names", () => {
    const { container } = render(<DimensionProgress sections={tenModuleSections} />);

    // Check that module names appear in the section labels area (not tooltips)
    const sectionLabels = container.querySelector('.space-y-2');
    expect(sectionLabels?.textContent).toContain("IP定位");
    expect(sectionLabels?.textContent).toContain("世界本体");
    expect(sectionLabels?.textContent).toContain("力量体系");
    expect(sectionLabels?.textContent).toContain("骰子设定");
    expect(sectionLabels?.textContent).toContain("AI生成边界");
  });

  it("handles empty sections array", () => {
    render(<DimensionProgress sections={[]} />);

    expect(screen.getByText("0/0")).toBeInTheDocument();
    expect(screen.getByText("0% Complete")).toBeInTheDocument();
  });

  it("applies glow-starlight class to percentage display", () => {
    const { container } = render(
      <DimensionProgress sections={mockSections} />
    );

    const glowElement = container.querySelector(".glow-starlight");
    expect(glowElement).toBeInTheDocument();
  });

  it("shows tooltips on hover for module cells", () => {
    const { container } = render(
      <DimensionProgress sections={tenModuleSections} />
    );

    const tooltips = container.querySelectorAll('.group-hover\\:opacity-100');
    expect(tooltips.length).toBeGreaterThan(0);
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
    { 
      id: "3", 
      label: "力量体系", 
      done: false,
      subs: [
        { id: "3-1", label: "等级制度", done: false },
        { id: "3-2", label: "能力限制", done: false }
      ]
    },
  ];

  it("displays sub-item progress for sections with subs", () => {
    render(<DimensionProgress sections={mockSectionsWithSubs} />);

    expect(screen.getAllByText(/sub-items/).length).toBeGreaterThan(0);
    expect(screen.getByText(/1\/2 sub-items/)).toBeInTheDocument();
  });

  it("handles sections without subs gracefully", () => {
    render(<DimensionProgress sections={mockSections} />);

    // Should not display sub-item counts for sections without subs
    expect(screen.queryByText(/sub-items/)).not.toBeInTheDocument();
  });
});
