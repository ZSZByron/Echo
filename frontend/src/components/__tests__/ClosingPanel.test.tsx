/**
 * ClosingPanel Component Tests
 *
 * D21 T9: 收尾三连问面板 — footer panel shown when the closing flow triggers.
 * The three closing questions themselves arrive via the chat reply text stream
 * (backend interjects plain-language questions); this panel only provides the
 * read-only output preview and three explicit action entries.
 * TDD: tests written first to define behavior before implementation.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ClosingPanel, consumerLabel } from '../guided/ClosingPanel';
import type { ConsumerArtifact } from '../../types/a1';

const mockOnFinalize = vi.fn();
const mockOnContinue = vi.fn();

function makeConsumers(): ConsumerArtifact[] {
  return [
    { id: 'world_bible', kind: 'd22' },
    { id: 'character_codex', kind: 'd22' },
    { id: 'story_outline', kind: 'd22' },
    { id: 'dice_projection', kind: 'trpg' },
    { id: 'character_projection', kind: 'trpg' },
  ];
}

describe('ClosingPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render when triggered=false (no closing-panel testid)', () => {
    const { container } = render(
      <ClosingPanel
        triggered={false}
        consumers={makeConsumers()}
        onFinalize={mockOnFinalize}
        onContinue={mockOnContinue}
      />
    );
    expect(container.querySelector('[data-testid="closing-panel"]')).toBeNull();
  });

  it('renders preview items (human names, read-only) and three action buttons when triggered', () => {
    render(
      <ClosingPanel
        triggered={true}
        consumers={makeConsumers()}
        onFinalize={mockOnFinalize}
        onContinue={mockOnContinue}
      />
    );
    // Preview zone: one read-only row per consumer, no download buttons
    const items = screen.getAllByTestId('closing-preview-item');
    expect(items).toHaveLength(5);
    // No download/export affordances anywhere in the panel
    const panel = screen.getByTestId('closing-panel');
    expect(panel.querySelectorAll('a')).toHaveLength(0);
    expect(panel.querySelectorAll('[data-testid*="download"]')).toHaveLength(0);
    // Three explicit action entries (verbatim labels)
    expect(screen.getByTestId('closing-action-finalize')).toHaveTextContent('生成文档');
    expect(screen.getByTestId('closing-action-continue')).toHaveTextContent('继续访谈录入设定');
    expect(screen.getByTestId('closing-action-later')).toHaveTextContent('改天继续');
  });

  it('panel text never leaks internal module ids (snake_case forms)', () => {
    render(
      <ClosingPanel
        triggered={true}
        consumers={makeConsumers()}
        onFinalize={mockOnFinalize}
        onContinue={mockOnContinue}
      />
    );
    const text = document.body.textContent || '';
    expect(text).not.toMatch(/[a-z_]+_[a-z_]+/);
  });

  it('clicking 生成文档 invokes the onFinalize callback (props injection)', () => {
    render(
      <ClosingPanel
        triggered={true}
        consumers={makeConsumers()}
        onFinalize={mockOnFinalize}
        onContinue={mockOnContinue}
      />
    );
    fireEvent.click(screen.getByTestId('closing-action-finalize'));
    expect(mockOnFinalize).toHaveBeenCalledTimes(1);
  });

  it('clicking 继续访谈录入设定 invokes onContinue (panel closes via parent)', () => {
    render(
      <ClosingPanel
        triggered={true}
        consumers={makeConsumers()}
        onFinalize={mockOnFinalize}
        onContinue={mockOnContinue}
      />
    );
    fireEvent.click(screen.getByTestId('closing-action-continue'));
    expect(mockOnContinue).toHaveBeenCalledTimes(1);
  });

  it('clicking 改天继续 shows the saved-progress hint with NO navigation', () => {
    const pushSpy = vi.spyOn(window.history, 'pushState');
    render(
      <ClosingPanel
        triggered={true}
        consumers={makeConsumers()}
        onFinalize={mockOnFinalize}
        onContinue={mockOnContinue}
      />
    );
    fireEvent.click(screen.getByTestId('closing-action-later'));
    expect(screen.getByTestId('closing-later-hint')).toHaveTextContent(
      '好的，进度都保存在这个会话里，随时回来'
    );
    // No new session / no route change: no history navigation, no links
    expect(pushSpy).not.toHaveBeenCalled();
    expect(mockOnContinue).not.toHaveBeenCalled();
    expect(mockOnFinalize).not.toHaveBeenCalled();
    pushSpy.mockRestore();
  });
});

describe('consumerLabel (pure function)', () => {
  it('maps known internal ids to human names', () => {
    expect(consumerLabel('world_bible')).toBe('世界观圣经');
    expect(consumerLabel('character_codex')).toBe('角色图鉴');
    expect(consumerLabel('story_outline')).toBe('故事大纲');
    expect(consumerLabel('dice_projection')).toBe('跑团投影');
    expect(consumerLabel('character_projection')).toBe('角色投影');
  });

  it('falls back to a generic human phrase for unknown ids (no id leakage)', () => {
    const label = consumerLabel('unknown_artifact_x');
    expect(label).toBe('一份设定产出');
    expect(label).not.toMatch(/[a-z_]+_[a-z_]+/);
  });
});
