/**
 * T11 (D21-13): IPPoster α version badge tests — written first (RED).
 *
 * Mount: getDraftVersion(fileId). available=true → 「α 草稿 v{version}」.
 * Endpoint error → degraded 「草稿」 badge, never crash.
 * Poster loaded (finalized file) + available=false → 「已定稿」.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { IPPoster } from '../IPPoster';

vi.mock('../../../api/client', () => ({
  fetchJson: vi.fn(),
  ApiError: class extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
    }
  },
}));

vi.mock('../../../api/a1', () => ({
  getDraftVersion: vi.fn(),
}));

import { fetchJson } from '../../../api/client';
import { getDraftVersion } from '../../../api/a1';

const posterPayload = {
  panels: [],
  ai_image_prompt: '',
  ai_image_status: 'pending',
  ai_image_url: null,
  visual_bg_status: null,
  visual_bg_images: [],
  visual_bg_best: null,
  visual_bg_prompt: null,
};

function mountWithFileId() {
  window.history.replaceState(null, '', '/a1/poster?fileId=f-123');
  return render(<IPPoster />);
}

describe('IPPoster - draft version badge (T11)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows α 草稿 v{version} when draft-version is available', async () => {
    vi.mocked(getDraftVersion).mockResolvedValue({
      available: true,
      version: 'α0.1',
      baseline: 0,
      round: 1,
    });
    vi.mocked(fetchJson).mockResolvedValue(posterPayload);

    mountWithFileId();

    await waitFor(() => {
      expect(screen.getByTestId('poster-draft-badge')).toHaveTextContent('α 草稿 vα0.1');
    });
  });

  it('shows 已定稿 when poster loads and no draft version is available', async () => {
    vi.mocked(getDraftVersion).mockResolvedValue({ available: false });
    vi.mocked(fetchJson).mockResolvedValue(posterPayload);

    mountWithFileId();

    await waitFor(() => {
      expect(screen.getByTestId('poster-draft-badge')).toHaveTextContent('已定稿');
    });
  });

  it('degrades to 草稿 badge (no fake version) when getDraftVersion throws', async () => {
    vi.mocked(getDraftVersion).mockRejectedValue(new Error('HTTP 404'));
    vi.mocked(fetchJson).mockRejectedValue(new Error('network down'));

    mountWithFileId();

    await waitFor(() => {
      const badge = screen.getByTestId('poster-draft-badge');
      expect(badge).toHaveTextContent('草稿');
      expect(badge.textContent).not.toMatch(/[0-9]/);
    });
  });
});
