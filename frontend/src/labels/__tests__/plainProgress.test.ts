import { describe, it, expect } from "vitest";
import { plainProgressLabel } from "../plainProgress";

describe("plainProgressLabel", () => {
  it("returns 聊聊你的世界 done/total", () => {
    expect(plainProgressLabel(3, 7)).toBe("聊聊你的世界 3/7");
  });

  it("handles zero progress", () => {
    expect(plainProgressLabel(0, 10)).toBe("聊聊你的世界 0/10");
  });

  it("handles empty state", () => {
    expect(plainProgressLabel(0, 0)).toBe("聊聊你的世界 0/0");
  });
});
