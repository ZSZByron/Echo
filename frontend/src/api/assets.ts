/**
 * assets.ts — typed API client for /api/assets endpoints.
 *
 * Mirrors backend/app/api/assets_routes.py. Backend returns Pydantic models
 * with snake_case field names (default); the frontend types match 1:1.
 */
import { fetchWithTimeout } from './client';

const ASSETS_BASE = '/api/assets';

export type AssetStatus =
  | 'pending'
  | 'generating'
  | 'completed'
  | 'approved'
  | 'rejected'
  | 'failed';

export type AssetType = 'background' | 'object';

export interface Asset {
  id: string;
  type: AssetType;
  name: string;
  prompt: string;
  negative_prompt: string;
  status: AssetStatus;
  generation_status: string;
  file_path: string | null;
  url: string | null;  // Computed field: converts file_path to /assets/filename.png
  parent_scene: string;
  seed: number | null;
  created_at: string;
  approved_at: string | null;
  reviewer_note: string | null;
  error_message: string | null;
  
  // New LOD views fields (optional - backward compatible)
  views?: Record<string, Record<string, unknown>> | null;
  lod_level?: string | null;
  puzzle_role?: string | null;
  parent_object?: string | null;
  depth?: string | null;
}

interface ListAssetsResponse {
  assets: Asset[];
}

interface GenerateResponse {
  task_id: string;
  status: string;
}

interface StatusResponse {
  status: string;
  generation_status: string;
}

interface GenerateAllResponse {
  triggered: number;
  task_ids: string[];
}

interface BulkApproveResponse {
  approved: number;
}

const JSON_HEADERS = { 'Content-Type': 'application/json' };

/** GET /api/assets — list all assets. */
export async function listAssets(): Promise<Asset[]> {
  const res = await fetchWithTimeout(`${ASSETS_BASE}`, { method: 'GET' });
  const data = (await res.json()) as ListAssetsResponse;
  return data.assets;
}

/** GET /api/assets/{id} — fetch a single asset. */
export async function getAsset(id: string): Promise<Asset> {
  const res = await fetchWithTimeout(`${ASSETS_BASE}/${encodeURIComponent(id)}`, {
    method: 'GET',
  });
  return (await res.json()) as Asset;
}

/** POST /api/assets/{id}/generate — trigger async generation. */
export async function generateAsset(id: string): Promise<GenerateResponse> {
  const res = await fetchWithTimeout(
    `${ASSETS_BASE}/${encodeURIComponent(id)}/generate`,
    { method: 'POST', headers: JSON_HEADERS },
  );
  return (await res.json()) as GenerateResponse;
}

/** GET /api/assets/{id}/status — poll generation status. */
export async function getAssetStatus(id: string): Promise<StatusResponse> {
  const res = await fetchWithTimeout(
    `${ASSETS_BASE}/${encodeURIComponent(id)}/status`,
    { method: 'GET' },
  );
  return (await res.json()) as StatusResponse;
}

/** POST /api/assets/{id}/approve — approve a completed asset. */
export async function approveAsset(id: string): Promise<Asset> {
  const res = await fetchWithTimeout(
    `${ASSETS_BASE}/${encodeURIComponent(id)}/approve`,
    { method: 'POST', headers: JSON_HEADERS },
  );
  return (await res.json()) as Asset;
}

/** POST /api/assets/{id}/reject — reject a completed asset. */
export async function rejectAsset(id: string, reviewerNote?: string): Promise<Asset> {
  const res = await fetchWithTimeout(
    `${ASSETS_BASE}/${encodeURIComponent(id)}/reject`,
    {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ reviewer_note: reviewerNote ?? '' }),
    },
  );
  return (await res.json()) as Asset;
}

/** PUT /api/assets/{id}/prompt — update prompt + negative prompt. */
export async function updatePrompt(
  id: string,
  prompt: string,
  negativePrompt: string,
): Promise<Asset> {
  const res = await fetchWithTimeout(
    `${ASSETS_BASE}/${encodeURIComponent(id)}/prompt`,
    {
      method: 'PUT',
      headers: JSON_HEADERS,
      body: JSON.stringify({ prompt, negative_prompt: negativePrompt }),
    },
  );
  return (await res.json()) as Asset;
}

/** POST /api/assets/generate-all — trigger generation for all pending assets. */
export async function generateAll(): Promise<GenerateAllResponse> {
  const res = await fetchWithTimeout(`${ASSETS_BASE}/generate-all`, {
    method: 'POST',
    headers: JSON_HEADERS,
  });
  return (await res.json()) as GenerateAllResponse;
}

/** POST /api/assets/bulk-approve — approve all completed assets. */
export async function bulkApprove(): Promise<BulkApproveResponse> {
  const res = await fetchWithTimeout(`${ASSETS_BASE}/bulk-approve`, {
    method: 'POST',
    headers: JSON_HEADERS,
  });
  return (await res.json()) as BulkApproveResponse;
}
