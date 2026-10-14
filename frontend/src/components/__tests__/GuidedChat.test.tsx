// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { GuidedChat, type DiceRecommendationResponse } from "../guided/GuidedChat";

describe("GuidedChat with Dice Recommendations", () => {
  const mockDiceRecommendation: DiceRecommendationResponse = {
    summary: "Based on your IP定位 responses, we recommend these dice settings:",
    recommendations: [
      {
        field: "力量判定",
        value: "2d6+4",
        reason: "IP定位中选择了高魔法设定，力量上限提升"
      },
      {
        field: "社交难度",
        value: "1d8-1",
        reason: "文明与社会模块显示孤立环境，社交难度降低"
      }
    ]
  };

  const mockMessagesWithDice = [
    {
      id: "1",
      type: "assistant" as const,
      text: "Based on your worldbuilding, here are some dice recommendations:",
      diceRecommendation: mockDiceRecommendation
    }
  ];

  const mockMessagesWithoutDice = [
    {
      id: "1",
      type: "user" as const,
      text: "Hello"
    }
  ];

  it("renders dice recommendation card when present", () => {
    render(<GuidedChat messages={mockMessagesWithDice} onSend={() => {}} />);

    expect(screen.getByText("🎲 Dice Recommendations")).toBeInTheDocument();
    expect(screen.getByText(mockDiceRecommendation.summary)).toBeInTheDocument();
  });

  it("renders all recommendation items", () => {
    render(<GuidedChat messages={mockMessagesWithDice} onSend={() => {}} />);

    expect(screen.getByText("力量判定: 2d6+4")).toBeInTheDocument();
    expect(screen.getByText("社交难度: 1d8-1")).toBeInTheDocument();
  });

  it("renders recommendation reasons", () => {
    render(<GuidedChat messages={mockMessagesWithDice} onSend={() => {}} />);

    expect(screen.getByText(/Based on: IP定位中选择了高魔法设定/)).toBeInTheDocument();
    expect(screen.getByText(/Based on: 文明与社会模块显示孤立环境/)).toBeInTheDocument();
  });

  it("applies glass-panel styling to dice card", () => {
    const { container } = render(
      <GuidedChat messages={mockMessagesWithDice} onSend={() => {}} />
    );

    const glassPanel = container.querySelector(".glass-panel");
    expect(glassPanel).toBeInTheDocument();
  });

  it("handles messages without dice recommendations", () => {
    render(<GuidedChat messages={mockMessagesWithoutDice} onSend={() => {}} />);

    expect(screen.queryByText("🎲 Dice Recommendations")).not.toBeInTheDocument();
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("renders dice icon in recommendations", () => {
    render(<GuidedChat messages={mockMessagesWithDice} onSend={() => {}} />);

    const diceIcons = screen.getAllByText("🎲");
    expect(diceIcons.length).toBeGreaterThan(0);
  });

  it("disables input when disabled prop is true", () => {
    render(
      <GuidedChat 
        messages={mockMessagesWithoutDice} 
        onSend={() => {}} 
        disabled={true} 
      />
    );

    const input = screen.getByPlaceholderText("Type your message...");
    expect(input).toBeDisabled();
  });
});

describe("GuidedChat multi-line input", () => {
  const messages = [
    { id: "1", type: "assistant" as const, text: "Hello" }
  ];

  it("renders a textarea instead of a single-line input", () => {
    render(<GuidedChat messages={messages} onSend={() => {}} />);
    const box = screen.getByPlaceholderText("Type your message...");
    expect(box.tagName.toLowerCase()).toBe("textarea");
  });

  it("Enter key sends the message", () => {
    const onSend = vi.fn();
    render(<GuidedChat messages={messages} onSend={onSend} />);

    const box = screen.getByPlaceholderText("Type your message...");
    fireEvent.change(box, { target: { value: "主线是复仇" } });
    fireEvent.keyDown(box, { key: "Enter" });

    expect(onSend).toHaveBeenCalledTimes(1);
    expect(onSend).toHaveBeenCalledWith("主线是复仇");
    expect(box).toHaveValue("");
  });

  it("Shift+Enter inserts a newline without sending", () => {
    const onSend = vi.fn();
    render(<GuidedChat messages={messages} onSend={onSend} />);

    const box = screen.getByPlaceholderText("Type your message...");
    fireEvent.change(box, { target: { value: "第一段" } });
    fireEvent.keyDown(box, { key: "Enter", shiftKey: true });
    fireEvent.change(box, { target: { value: "第一段\n第二段" } });

    expect(onSend).not.toHaveBeenCalled();
    expect(box).toHaveValue("第一段\n第二段");
  });

  it("Enter during IME composition does not send", () => {
    const onSend = vi.fn();
    render(<GuidedChat messages={messages} onSend={onSend} />);

    const box = screen.getByPlaceholderText("Type your message...");
    fireEvent.change(box, { target: { value: "拼音" } });
    fireEvent.keyDown(box, { key: "Enter", isComposing: true });

    expect(onSend).not.toHaveBeenCalled();
    expect(box).toHaveValue("拼音");
  });
});