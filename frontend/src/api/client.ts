const API_BASE = '/api';
const TIMEOUT_MS = 30000;

export async function fetchWithTimeout(url: string, options: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response;
  } finally {
    clearTimeout(timeout);
  }
}

export const apiClient = {
  async action(req: { player_input: string }) {
    const res = await fetchWithTimeout(`${API_BASE}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return res.json();
  },
  async getState() {
    const res = await fetchWithTimeout(`${API_BASE}/state`, { method: 'GET' });
    return res.json();
  },
  async reset() {
    const res = await fetchWithTimeout(`${API_BASE}/reset`, { method: 'POST' });
    return res.json();
  },
  async health() {
    const res = await fetchWithTimeout(`${API_BASE}/health`, { method: 'GET' });
    return res.json();
  },
};

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    super(`HTTP ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

export async function fetchJson<T>(
  url: string,
  init?: RequestInit & { timeoutMs?: number }
): Promise<T> {
  const timeoutMs = init?.timeoutMs ?? TIMEOUT_MS;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...init,
      signal: controller.signal,
    });

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new ApiError(response.status, body);
    }

    return response.json() as Promise<T>;
  } finally {
    clearTimeout(timeout);
  }
}
