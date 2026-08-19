/**
 * identity.ts — identity and user registration API client.
 *
 * Provides user registration and identity management endpoints.
 * Mirrors backend identity/auth routes.
 */
import { fetchJson } from './client';

export interface IdentityInfo {
  user_id: string;
  tier: string;
}

/**
 * Register a new user and retrieve their identity information.
 * POST /api/identity/register
 *
 * @returns Promise<IdentityInfo> - User identity with ID and tier
 */
export async function registerUser(): Promise<IdentityInfo> {
  return fetchJson<IdentityInfo>('/api/identity/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  });
}
