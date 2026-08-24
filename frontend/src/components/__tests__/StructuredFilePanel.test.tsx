// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StructuredFilePanel } from "../structured/StructuredFilePanel";

describe("StructuredFilePanel", () => {
  const mockFile = {
    id: "file-1",
    name: "Test File",
    path: "/test/file",
    type: "IP",
    sections: [
      {
        id: "section-1",
        label: "IP定位",
        content: "Test content for IP定位",
        done: true,
      },
      {
        id: "section-2",
        label: "世界本体",
        done: false,
      },
    ],
  };

  const mockFileWithSubs = {
    id: "file-2",
    name: "Test File with Subs",
    path: "/test/file-with-subs",
    type: "IP",
    sections: [
      {
        id: "section-1",
        label: "IP定位",
        done: true,
        subs: [
          { id: "sub-1-1", label: "核心概念", content: "科幻赛博朋克", done: true },
          { id: "sub-1-2", label: "目标受众", content: "年轻成人", done: true },
        ],
      },
      {
        id: "section-2",
        label: "世界本体",
        done: false,
        subs: [
          { id: "sub-2-1", label: "物理法则", done: false },
          { id: "sub-2-2", label: "魔法系统", content: "能量水晶", done: true },
        ],
      },
    ],
  };

  it("renders file header with basic information", () => {
    render(<StructuredFilePanel file={mockFile} />);

    expect(screen.getByText("Test File")).toBeInTheDocument();
    expect(screen.getByText("IP")).toBeInTheDocument();
    expect(screen.getByText("/test/file")).toBeInTheDocument();
  });

  it("renders sections with legacy single-content structure", () => {
    render(<StructuredFilePanel file={mockFile} />);

    expect(screen.getByText("IP定位")).toBeInTheDocument();
    expect(screen.getByText("Test content for IP定位")).toBeInTheDocument();
    expect(screen.getByText("世界本体")).toBeInTheDocument();
  });

  it("renders sections with two-level subs structure", () => {
    const { container } = render(<StructuredFilePanel file={mockFileWithSubs} />);

    expect(screen.getByText("IP定位")).toBeInTheDocument();
    expect(container.textContent).toContain("核心概念");
    expect(container.textContent).toContain("科幻赛博朋克");
    expect(container.textContent).toContain("目标受众");
    expect(container.textContent).toContain("年轻成人");

    expect(screen.getByText("世界本体")).toBeInTheDocument();
    expect(container.textContent).toContain("物理法则");
    expect(container.textContent).toContain("魔法系统");
  });

  it("displays completion checkmarks for completed sections/subs", () => {
    const { container } = render(<StructuredFilePanel file={mockFileWithSubs} />);

    const checkmarks = container.querySelectorAll(".text-cosmos-success");
    expect(checkmarks.length).toBeGreaterThan(0);
  });

  it("shows 'Not yet filled' for empty content", () => {
    render(<StructuredFilePanel file={mockFile} />);

    expect(screen.getByText("Not yet filled")).toBeInTheDocument();
  });

  it("handles sections without content or subs gracefully", () => {
    const fileWithEmptySections = {
      ...mockFile,
      sections: [
        { id: "section-1", label: "Empty Section", done: false },
      ],
    };

    render(<StructuredFilePanel file={fileWithEmptySections} />);

    expect(screen.getByText("Empty Section")).toBeInTheDocument();
    expect(screen.getByText("Not yet filled")).toBeInTheDocument();
  });

  it("applies correct styling based on completion status", () => {
    const { container } = render(<StructuredFilePanel file={mockFileWithSubs} />);

    const completedSection = container.querySelector(".border-cosmos-success\\/30");
    expect(completedSection).toBeInTheDocument();

    const incompleteSub = container.querySelector(".bg-void-600");
    expect(incompleteSub).toBeInTheDocument();
  });
});
