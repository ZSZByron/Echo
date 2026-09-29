/**
 * D21 api client tests (plan task T7)
 *
 * Covers: method/path/body/response-parsing for the five D21 endpoints,
 * plus the 404 dual-path error shapes (ApiError with .status AND the
 * degraded Error("HTTP 404") from fetchWithTimeout).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  getClosingState,
  resolveAlignment,
  nudgeCoords,
  getDraftVersion,
  getImpulseCoords,
} from "../a1";
import { ApiError } from "../client";

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  fetchMock.mockReset();
});

function okResponse(body: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: () => Promise.resolve(body),
  } as unknown as Response;
}

describe("getClosingState", () => {
  it("GETs /api/a1/file/{id}/closing-state and parses the full shape", async () => {
    fetchMock.mockResolvedValueOnce(
      okResponse({
        file_id: "f1",
        closing_step: 2,
        closing_settled: false,
        triggered: true,
        preview: {
          file_id: "f1",
          exists: true,
          closing: { questions_complete: true, pending_count: 1, complete: false },
          module_coverage: [
            { module_id: "world", done_ratio: 0.5, done_fields: 3, total_fields: 6 },
          ],
          gaps: [{ module_id: "world", field: "physics", key: "world.physics", label: "物理" }],
          version_chain: null,
          stale: false,
          stale_warning: null,
          consumers: [{ id: "world_bible", kind: "d22" }],
        },
      })
    );

    const state = await getClosingState("f1");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/a1/file/f1/closing-state",
      expect.objectContaining({ method: "GET" })
    );
    expect(state.closing_step).toBe(2);
    expect(state.triggered).toBe(true);
    expect(state.preview.closing.complete).toBe(false);
    expect(state.preview.module_coverage[0].done_ratio).toBe(0.5);
    expect(state.preview.consumers[0].id).toBe("world_bible");
  });
});

describe("resolveAlignment", () => {
  it("POSTs {accept} to /alignment/{key}/resolve with the key URL-encoded", async () => {
    fetchMock.mockResolvedValueOnce(okResponse({ applied: true, accept: true }));

    const res = await resolveAlignment("f1", "world.physics/gravity", true);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(
      "/api/a1/file/f1/alignment/world.physics%2Fgravity/resolve"
    );
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ accept: true });
    expect(res).toEqual({ applied: true, accept: true });
  });

  it("propagates the not_found body (stale key arrives as 200, not an error)", async () => {
    fetchMock.mockResolvedValueOnce(
      okResponse({ applied: false, accept: true, error: "not_found" })
    );
    const res = await resolveAlignment("f1", "gone", true);
    expect(res.applied).toBe(false);
    expect(res.error).toBe("not_found");
  });

  it("propagates ApiError (fetchJson path) with .status on non-2xx", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: "file not found" }),
    } as unknown as Response);

    await expect(resolveAlignment("f1", "k", false)).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
    });
  });
});

describe("nudgeCoords", () => {
  it("POSTs {signal} to /impulse-coords/signal and parses the response", async () => {
    fetchMock.mockResolvedValueOnce(
      okResponse({
        file_id: "f1",
        session_id: "s1",
        applied: true,
        axis: 6.35,
        confidence: 0.4,
      })
    );

    const res = await nudgeCoords("f1", "user_nudge_story");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/a1/file/f1/impulse-coords/signal");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ signal: "user_nudge_story" });
    expect(res.applied).toBe(true);
    expect(res.axis).toBe(6.35);
    expect(res.confidence).toBe(0.4);
  });

  it("propagates ApiError 400 for out-of-whitelist signals (typed at compile time, mocked here)", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: () => Promise.resolve({ detail: "signal must be one of [...]" }),
    } as unknown as Response);

    const err = await nudgeCoords("f1", "user_nudge_story").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(400);
  });
});

describe("getDraftVersion", () => {
  it("parses the available:false variant", async () => {
    fetchMock.mockResolvedValueOnce(okResponse({ available: false }));
    const res = await getDraftVersion("f1");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/a1/file/f1/draft-version",
      expect.objectContaining({ method: "GET" })
    );
    expect(res.available).toBe(false);
  });

  it("parses the available:true variant with version/baseline/round", async () => {
    fetchMock.mockResolvedValueOnce(
      okResponse({ available: true, version: "α0.11", baseline: 1, round: 1 })
    );
    const res = await getDraftVersion("f1");
    if (!res.available) throw new Error("expected available draft");
    expect(res.version).toBe("α0.11");
    expect(res.baseline).toBe(1);
    expect(res.round).toBe(1);
  });
});

describe("getImpulseCoords", () => {
  it("GETs /impulse-coords and parses the dashboard shape", async () => {
    fetchMock.mockResolvedValueOnce(
      okResponse({
        file_id: "f1",
        session_id: "s1",
        axis: 7.0,
        confidence: 0.5,
        safety_flag: false,
        anchor: 7.0,
        anchor_source: "storyteller",
        adjustments: 1,
        reorder_count: 0,
        audit: [
          {
            round: 3,
            signal: "user_nudge_story",
            key: "",
            axis_before: 7.0,
            confidence_before: 0.45,
            applied: true,
            axis_after: 7.1,
            confidence_after: 0.5,
            axis_delta: 0.1,
          },
        ],
      })
    );

    const res = await getImpulseCoords("f1");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/a1/file/f1/impulse-coords",
      expect.objectContaining({ method: "GET" })
    );
    expect(res.safety_flag).toBe(false);
    expect(res.axis).toBe(7.0);
    expect(res.audit[0].signal).toBe("user_nudge_story");
  });
});

describe("404 dual-path propagation", () => {
  it("path A: fetchJson-based client throws ApiError with .status = 404", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: "not found" }),
    } as unknown as Response);

    const err = await resolveAlignment("missing", "k", true).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(404);
    expect((err as ApiError).message).toBe("HTTP 404");
  });

  it("path B: fetchWithTimeout-based client propagates the degraded Error('HTTP 404')", async () => {
    // confirmFillProposal uses fetchWithTimeout; simulate its degraded path
    // by rejecting with the exact error that wrapper throws on !response.ok
    fetchMock.mockRejectedValueOnce(new Error("HTTP 404"));

    const err = await getImpulseCoords("missing").catch((e) => e);
    // the client must NOT swallow/transform: plain Error, message "HTTP 404"
    expect(err).toBeInstanceOf(Error);
    expect(err).not.toBeInstanceOf(ApiError);
    expect((err as Error).message).toBe("HTTP 404");
  });
});
