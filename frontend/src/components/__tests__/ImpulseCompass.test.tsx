/**
 * ImpulseCompass tests (D21-12, T8)
 *
 * Axis semantics pinned by impulse spec §10.1: 连续 [0,100]，100=纯叙事，0=纯建构；
 * anchor 默认 70（说不清初值）。Backend impulse_coords.py _AXIS_MIN/_AXIS_MAX = 0.0/100.0。
 * Button labels verbatim from ux-flow §5.3: 更像讲故事 / 差不多 / 更像建设定。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ImpulseCompass, compassPhrase } from '../guided/ImpulseCompass';
import { nudgeCoords } from '../../api/a1';
import type { ImpulseCoords, ImpulseSignalResponse } from '../../types/a1';

vi.mock('../../api/a1', () => ({
  nudgeCoords: vi.fn(),
}));

const nudgeMock = vi.mocked(nudgeCoords);

function makeCoords(overrides: Partial<ImpulseCoords> = {}): ImpulseCoords {
  return {
    file_id: 'f-1',
    session_id: 's-1',
    axis: 70,
    confidence: 0.5,
    safety_flag: false,
    anchor: 70,
    anchor_source: 'unclear_default',
    adjustments: 0,
    reorder_count: 0,
    audit: [],
    ...overrides,
  };
}

function signalResponse(overrides: Partial<ImpulseSignalResponse> = {}): ImpulseSignalResponse {
  return {
    file_id: 'f-1',
    session_id: 's-1',
    applied: true,
    axis: 74,
    confidence: 0.55,
    ...overrides,
  };
}

beforeEach(() => {
  nudgeMock.mockReset();
});

describe('compassPhrase (pure function)', () => {
  it('axis=70 (story side) → 「讲故事的 70%」', () => {
    expect(compassPhrase(70)).toContain('讲故事的');
    expect(compassPhrase(70)).toContain('70%');
  });

  it('axis=30 (builder side) → 「建设定的 70%」 (mirror percentage)', () => {
    expect(compassPhrase(30)).toContain('建设定的');
    expect(compassPhrase(30)).toContain('70%');
  });

  it('axis=100 → 纯叙事端；axis=0 → 纯建构端', () => {
    expect(compassPhrase(100)).toContain('讲故事的 100%');
    expect(compassPhrase(0)).toContain('建设定的 100%');
  });
});

describe('ImpulseCompass component', () => {
  it('renders the one-line coordinate reading', () => {
    render(<ImpulseCompass fileId="f-1" coords={makeCoords()} />);
    expect(screen.getByText(/目前感觉你更像/)).toBeInTheDocument();
    expect(screen.getByText(/讲故事的 70%/)).toBeInTheDocument();
  });

  it('renders shell without crashing when coords is null (degraded)', () => {
    render(<ImpulseCompass fileId="f-1" coords={null} />);
    expect(screen.getByText(/目前感觉你更像/)).toBeInTheDocument();
  });

  it('three buttons fire nudgeCoords with verbatim signal enums', async () => {
    nudgeMock.mockResolvedValue(signalResponse({ axis: 74 }));
    render(<ImpulseCompass fileId="f-1" coords={makeCoords()} />);

    fireEvent.click(screen.getByRole('button', { name: '更像讲故事' }));
    await waitFor(() => expect(nudgeMock).toHaveBeenCalledWith('f-1', 'user_nudge_story'));

    fireEvent.click(screen.getByRole('button', { name: '差不多' }));
    await waitFor(() => expect(nudgeMock).toHaveBeenCalledWith('f-1', 'user_nudge_confirm'));

    fireEvent.click(screen.getByRole('button', { name: '更像建设定' }));
    await waitFor(() => expect(nudgeMock).toHaveBeenCalledWith('f-1', 'user_nudge_builder'));

    expect(nudgeMock).toHaveBeenCalledTimes(3);
  });

  it('applied=true → display updates from response axis', async () => {
    nudgeMock.mockResolvedValue(signalResponse({ applied: true, axis: 85 }));
    render(<ImpulseCompass fileId="f-1" coords={makeCoords()} />);
    fireEvent.click(screen.getByRole('button', { name: '更像讲故事' }));
    await waitFor(() => expect(screen.getByText(/85%/)).toBeInTheDocument());
  });

  it('applied=false (damped) → displayed value unchanged, no error popup', async () => {
    nudgeMock.mockResolvedValue(signalResponse({ applied: false, axis: 70 }));
    render(<ImpulseCompass fileId="f-1" coords={makeCoords()} />);
    fireEvent.click(screen.getByRole('button', { name: '更像讲故事' }));
    await waitFor(() => expect(nudgeMock).toHaveBeenCalled());
    // Display stays at the original reading.
    expect(screen.getByText(/讲故事的 70%/)).toBeInTheDocument();
    // Silent honesty: no error surface.
    expect(screen.queryByText(/失败|错误|error/i)).toBeNull();
  });

  it('nudgeCoords rejection → silent, display unchanged, buttons stay clickable', async () => {
    nudgeMock.mockRejectedValue(new Error('HTTP 500'));
    render(<ImpulseCompass fileId="f-1" coords={makeCoords()} />);
    fireEvent.click(screen.getByRole('button', { name: '更像讲故事' }));
    await waitFor(() => expect(nudgeMock).toHaveBeenCalled());
    expect(screen.getByText(/讲故事的 70%/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '更像建设定' })).not.toBeDisabled();
  });

  it('safety_flag=true → buttons disabled + gray hint (no safety terminology)', () => {
    render(<ImpulseCompass fileId="f-1" coords={makeCoords({ safety_flag: true })} />);
    expect(screen.getByRole('button', { name: '更像讲故事' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '差不多' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '更像建设定' })).toBeDisabled();
    expect(screen.getByText('当前以你的感受为准')).toBeInTheDocument();
    // Coordinates still displayed.
    expect(screen.getByText(/讲故事的 70%/)).toBeInTheDocument();
  });
});
