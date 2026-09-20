import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTypewriter } from '../useTypewriter';

describe('useTypewriter', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('reveals the first character immediately on mount', () => {
    const { result } = renderHook(() => useTypewriter('test'));
    // The effect calls tick() synchronously, so char #1 is already shown.
    expect(result.current.displayedText).toBe('t');
    expect(result.current.isTyping).toBe(true);
    expect(result.current.isComplete).toBe(false);
  });

  it('progressively reveals characters', () => {
    const { result } = renderHook(() => useTypewriter('ABC', { speed: 100 }));
    expect(result.current.displayedText).toBe('A');

    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(result.current.displayedText).toBe('AB');

    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(result.current.displayedText).toBe('ABC');

    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(result.current.displayedText).toBe('ABC');
    expect(result.current.isTyping).toBe(false);
    expect(result.current.isComplete).toBe(true);
  });

  it('skip() shows full text immediately', () => {
    const { result } = renderHook(() => useTypewriter('ABC', { speed: 100 }));
    expect(result.current.displayedText).toBe('A');

    act(() => {
      result.current.skip();
    });

    expect(result.current.displayedText).toBe('ABC');
    expect(result.current.isTyping).toBe(false);
    expect(result.current.isComplete).toBe(true);
  });

  it('onComplete callback fires when typing finishes', () => {
    const onComplete = vi.fn();
    renderHook(() => useTypewriter('AB', { speed: 100, onComplete }));

    expect(onComplete).not.toHaveBeenCalled();

    // Sync tick reveals 'A'; two more ticks finish 'B' then complete.
    act(() => {
      vi.advanceTimersByTime(200);
    });

    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it('onComplete callback fires when skip is called', () => {
    const onComplete = vi.fn();
    const { result } = renderHook(() => useTypewriter('ABC', { speed: 100, onComplete }));

    expect(onComplete).not.toHaveBeenCalled();

    act(() => {
      result.current.skip();
    });

    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it('resets when text prop changes', () => {
    const { result, rerender } = renderHook(
      ({ text }) => useTypewriter(text, { speed: 100 }),
      { initialProps: { text: 'ABC' } }
    );

    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(result.current.isComplete).toBe(true);

    act(() => {
      rerender({ text: 'XYZ' });
    });
    // Effect resets state then ticks once synchronously: shows char #1 of new text.
    expect(result.current.displayedText).toBe('X');
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
