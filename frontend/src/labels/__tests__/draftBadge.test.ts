/**
 * T11 (D21-13): draftBadge pure function tests — written first (RED).
 *
 * Display honesty rule: the version string is shown verbatim ONLY when the
 * draft-version endpoint returned available=true. Endpoint no-data /
 * session restart → never fabricate a version number, 「草稿」 text only.
 */
import { describe, it, expect } from "vitest";
import { draftBadge, draftStaleBarLabel, posterBadge } from "../draftBadge";

describe("draftBadge", () => {
  it("① draft + version → α 草稿 v{version} (version verbatim)", () => {
    expect(draftBadge("draft", "α0.1")).toBe("α 草稿 vα0.1");
    expect(draftBadge("draft", "α0.11")).toBe("α 草稿 vα0.11");
  });

  it("② draft without version → 「草稿」 only (no fake number, no α)", () => {
    const label = draftBadge("draft", null);
    expect(label).toBe("草稿");
    expect(label).not.toMatch(/α|[0-9]/);
  });

  it("②b draft with undefined version degrades the same way", () => {
    expect(draftBadge("draft")).toBe("草稿");
  });

  it("③ finalized → 「已定稿」", () => {
    expect(draftBadge("finalized")).toBe("已定稿");
  });
});

describe("draftStaleBarLabel", () => {
  it("④ stale bar copy contains the α draft-phase marker", () => {
    const label = draftStaleBarLabel(2);
    expect(label).toContain("α");
    expect(label).toContain("v2");
    expect(label).toContain("设定已更新");
    expect(label).toContain("点此重新定稿");
  });
});

describe("posterBadge (IPPoster three-state mapping)", () => {
  it("available=true → α badge with version, wins over finalized poster", () => {
    expect(posterBadge({ available: true, version: "α0.1", baseline: 0, round: 1 }, true)).toBe(
      "α 草稿 vα0.1"
    );
  });

  it("available=false + poster loaded (finalized file) → 已定稿", () => {
    expect(posterBadge({ available: false }, true)).toBe("已定稿");
  });

  it("available=false + poster not loaded → 草稿 (no fake version)", () => {
    expect(posterBadge({ available: false }, false)).toBe("草稿");
  });

  it("endpoint network error (null) → 草稿, never crashes", () => {
    expect(posterBadge(null, false)).toBe("草稿");
    expect(posterBadge(null, true)).toBe("已定稿");
  });
});
