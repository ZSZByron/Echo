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

  it("renders 10 grid cells regardless of section count", () => {
    const { container } = render(
      <DimensionProgress sections={mockSections} />
    );

    const gridCells = container.querySelectorAll('.grid-cols-10 > div');
    expect(gridCells).toHaveLength(10);
  });

  it("displays correct completion count", () => {
    render(<DimensionProgress sections={mockSections} />);

    expect(screen.getByText("2/4")).toBeInTheDocument();
    expect(screen.getByText("50% Complete")).toBeInTheDocument();
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

  it("renders all section labels", () => {
    render(<DimensionProgress sections={mockSections} />);

    expect(screen.getByText("World Building")).toBeInTheDocument();
    expect(screen.getByText("Character Design")).toBeInTheDocument();
    expect(screen.getByText("Plot Structure")).toBeInTheDocument();
    expect(screen.getByText("Scene Mapping")).toBeInTheDocument();
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
});
