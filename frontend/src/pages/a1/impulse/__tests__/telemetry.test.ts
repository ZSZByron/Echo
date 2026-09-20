import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  exportImpulseTelemetry,
  getImpulseTelemetry,
  logImpulseEvent,
  type ImpulseTelemetryEventName,
} from '../telemetry';

const ALL_EVENT_NAMES: ImpulseTelemetryEventName[] = [
  'impulse_card_shown',
  'impulse_card_selected',
  'impulse_card_skipped',
  'first_question_answered',
  'module_completed',
];

describe('telemetry (a1_telemetry_v1)', () => {
  beforeEach(() => {
    localStorage.removeItem('a1_telemetry_v1');
    localStorage.removeItem('user_id');
  });

  it('accepts all 5 typed event names', () => {
    for (const name of ALL_EVENT_NAMES) {
      logImpulseEvent(name);
    }
    const events = getImpulseTelemetry();
    expect(events).toHaveLength(5);
    expect(events.map((e) => e.event)).toEqual(ALL_EVENT_NAMES);
  });

  it('enforces FIFO cap of 500 (writes 502, reads 500, first is the 3rd)', () => {
    for (let i = 0; i < 502; i++) {
      logImpulseEvent('impulse_card_shown', { i });
    }
    const events = getImpulseTelemetry();
    expect(events).toHaveLength(500);
    expect(events[0].data).toEqual({ i: 2 });
    expect(events[499].data).toEqual({ i: 501 });
  });

  it('recovers from corrupted storage without throwing', () => {
    localStorage.setItem('a1_telemetry_v1', 'not-json');
    expect(() => logImpulseEvent('impulse_card_shown')).not.toThrow();
    const events = getImpulseTelemetry();
    expect(events).toHaveLength(1);
    expect(events[0].event).toBe('impulse_card_shown');
  });

  it('exports exactly the stored content', () => {
    logImpulseEvent('impulse_card_selected', { primary: 'plot', secondary: null });
    const stored = JSON.parse(localStorage.getItem('a1_telemetry_v1')!);
    const clickSpy = vi.fn();
    const createElementSpy = vi
      .spyOn(document, 'createElement')
      .mockReturnValue({
        click: clickSpy,
        set href(v: string) {},
        set download(v: string) {},
      } as unknown as HTMLElement);
    const createObjectURLSpy = vi
      .spyOn(URL, 'createObjectURL')
      .mockReturnValue('blob:mock');

    exportImpulseTelemetry();

    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(createObjectURLSpy).toHaveBeenCalledTimes(1);
    const blob = createObjectURLSpy.mock.calls[0][0] as Blob;
    // Blob content equals stored content
    return blob.text().then((text) => {
      expect(JSON.parse(text)).toEqual(stored);
      createElementSpy.mockRestore();
      createObjectURLSpy.mockRestore();
    });
  });

  it('does not download when there are no events', () => {
    const createObjectURLSpy = vi.spyOn(URL, 'createObjectURL');
    exportImpulseTelemetry();
    expect(createObjectURLSpy).not.toHaveBeenCalled();
    createObjectURLSpy.mockRestore();
  });

  it('always sets schema_version to 1', () => {
    logImpulseEvent('module_completed', { module_id: 'm1' });
    const events = getImpulseTelemetry();
    expect(events[0].schema_version).toBe(1);
  });

  it('falls back to empty user_id when key missing', () => {
    logImpulseEvent('impulse_card_shown');
    expect(getImpulseTelemetry()[0].user_id).toBe('');
  });

  it('reads existing user_id from localStorage', () => {
    localStorage.setItem('user_id', 'u-123');
    logImpulseEvent('first_question_answered', { elapsed_ms: 100 });
    const events = getImpulseTelemetry();
    expect(events[0].user_id).toBe('u-123');
    expect(typeof events[0].ts).toBe('number');
  });
});
