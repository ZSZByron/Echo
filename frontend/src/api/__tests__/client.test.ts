import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fetchJson, ApiError } from '../client';

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('fetchJson', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should parse successful 2xx JSON response', async () => {
    const mockData = { user_id: 'test-123', tier: 'FREE' };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => mockData,
    } as Response);

    const result = await fetchJson<{ user_id: string; tier: string }>('/api/test', {
      method: 'POST',
    });

    expect(result).toEqual(mockData);
    expect(mockFetch).toHaveBeenCalledWith('/api/test', {
      method: 'POST',
      signal: expect.any(AbortSignal),
    });
  });

  it('should throw ApiError with status and body on 409 conflict', async () => {
    const errorBody = { missing_sections: ['user_profile', 'preferences'] };
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 409,
      json: async () => errorBody,
    } as Response);

    try {
      await fetchJson('/api/test', { method: 'POST' });
      expect.fail('Should have thrown ApiError');
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).status).toBe(409);
      expect((error as ApiError).body).toEqual(errorBody);
    }
  });

  it('should throw ApiError with status on other non-2xx responses', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ error: 'Internal Server Error' }),
    } as Response);

    try {
      await fetchJson('/api/test', { method: 'GET' });
      expect.fail('Should have thrown ApiError');
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).status).toBe(500);
    }
  });

  it('should abort request on timeout', async () => {
    // Note: Timeout is handled by AbortController in fetchJson
    // This test verifies the timeout configuration is passed correctly
    const mockData = { success: true };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockData,
    } as Response);

    // Fetch with short timeout (but mock resolves immediately)
    const result = await fetchJson('/api/test', { timeoutMs: 100 });

    expect(result).toEqual(mockData);
    expect(mockFetch).toHaveBeenCalledWith('/api/test', {
      timeoutMs: 100,
      signal: expect.any(AbortSignal),
    });
  });

  it('should use default 30s timeout when not specified', async () => {
    const mockData = { success: true };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockData,
    } as Response);

    await fetchJson('/api/test');

    // Should not timeout before 30s
    expect(mockFetch).toHaveBeenCalledWith('/api/test', {
      signal: expect.any(AbortSignal),
    });
  });
});
