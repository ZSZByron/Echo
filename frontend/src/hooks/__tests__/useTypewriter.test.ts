import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useTypewriter } from '../useTypewriter';

describe('useTypewriter', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it('starts with empty text', () => {
    const { result } = renderHook(() => useTypewriter('test'));
    expect(result.current.displayedText).toBe('');
    expect(result.current.isTyping).toBe(true);
    expect(result.current.isComplete).toBe(false);
  });

  it('progressively reveals characters', async () => {
    const { result } = renderHook(() => useTypewriter('ABC', { speed: 100 }));
    expect(result.current.displayedText).toBe('');

    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(result.current.displayedText).toBe('A');

    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(result.current.displayedText).toBe('AB');

    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(result.current.displayedText).toBe('ABC');
    expect(result.current.isTyping).toBe(false);
    expect(result.current.isComplete).toBe(true);
  });

  it('skip() shows full text immediately', () => {
    const { result } = renderHook(() => useTypewriter('ABC', { speed: 100 }));
    expect(result.current.displayedText).toBe('');

    act(() => {
      result.current.skip();
    });

    expect(result.current.displayedText).toBe('ABC');
    expect(result.current.isTyping).toBe(false);
    expect(result.current.isComplete).toBe(true);
  });

  it('onComplete callback fires when typing finishes', async () => {
    const onComplete = vi.fn();
    renderHook(() => useTypewriter('AB', { speed: 100, onComplete }));

    expect(onComplete).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(200);
    });

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalled();
    });
  });

  it('onComplete callback fires when skip is called', async () => {
    const onComplete = vi.fn();
    const { result } = renderHook(() => useTypewriter('ABC', { speed: 100, onComplete }));

    expect(onComplete).not.toHaveBeenCalled();

    act(() => {
      result.current.skip();
    });

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalled();
    });
  });

  it('resets when text prop changes', () => {
    const { rerender } = renderHook(
      ({ text }) => useTypewriter(text, { speed: 100 }),
      { initialProps: { text: 'ABC' } }
    );

    rerender({ text: 'XYZ' });
    const { result } = renderHook(() => useTypewriter('XYZ', { speed: 100 }));
    expect(result.current.displayedText).toBe('');
    expect(result.current.isTyping).toBe(true);
    expect(result.current.isComplete).toBe(false);
  });

  it('handles empty text immediately', () => {
    const { result } = renderHook(() => useTypewriter(''));
    expect(result.current.displayedText).toBe('');
    expect(result.current.isTyping).toBe(false);
    expect(result.current.isComplete).toBe(true);
  });
});
