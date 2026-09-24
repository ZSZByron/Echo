import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  attachSessionId,
  computeSkipRate,
  computeStatedBehaviorMismatchMap,
  computeModuleCompletion,
  exportImpulseTelemetry,
  getImpulseTelemetry,
  logImpulseEvent,
  type ImpulseTelemetryEvent,
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

  it('always sets schema_version to 2 (v2 write, plan M4c)', () => {
    logImpulseEvent('module_completed', { module_id: 'm1' });
    const events = getImpulseTelemetry();
    expect(events[0].schema_version).toBe(2);
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

  it('backfills session_id on events missing it', () => {
    logImpulseEvent('impulse_card_shown');
    logImpulseEvent('impulse_card_selected', { primary: 'plot', secondary: null });
    attachSessionId('a1_abc123');
    const events = getImpulseTelemetry();
    expect(events).toHaveLength(2);
    expect(events[0].session_id).toBe('a1_abc123');
    expect(events[1].session_id).toBe('a1_abc123');
  });

  it('does not overwrite an existing session_id (idempotent)', () => {
    logImpulseEvent('impulse_card_shown');
    attachSessionId('a1_abc123');
    attachSessionId('a1_def456');
    expect(getImpulseTelemetry()[0].session_id).toBe('a1_abc123');
  });

  it('tolerates corrupted storage without throwing', () => {
    localStorage.setItem('a1_telemetry_v1', '{broken json');
    expect(() => attachSessionId('a1_abc123')).not.toThrow();
    expect(getImpulseTelemetry()).toHaveLength(0);
  });
});

describe('telemetry v2 (M4c: 三项指标 + E0 v1 兼容读取)', () => {
  beforeEach(() => {
    localStorage.removeItem('a1_telemetry_v1');
    localStorage.removeItem('user_id');
  });

  it('E0 v1 compatibility: stored v1 payloads (schema_version 1, no new fields) still parse', () => {
    // v1 存量数据（升级前写入）——版本容忍读取，不得丢弃/报错
    const v1Event: Record<string, unknown> = {
      schema_version: 1,
      event: 'impulse_card_selected',
      ts: 1700000000000,
      user_id: 'u-legacy',
      data: { primary: 'plot', secondary: null },
    };
    localStorage.setItem(
      'a1_telemetry_v1',
      JSON.stringify([v1Event]),
    );
    const events = getImpulseTelemetry();
    expect(events).toHaveLength(1);
    expect(events[0].schema_version).toBe(1);
    expect(events[0].event).toBe('impulse_card_selected');
    expect(events[0].user_id).toBe('u-legacy');
  });

  it('mixed v1+v2 payloads coexist in one log', () => {
    const v1: Record<string, unknown> = {
      schema_version: 1,
      event: 'impulse_card_shown',
      ts: 1700000000000,
      user_id: 'u',
    };
    logImpulseEvent('impulse_card_shown'); // v2 write
    localStorage.setItem(
      'a1_telemetry_v1',
      JSON.stringify([v1, ...getImpulseTelemetry()]),
    );
    const events = getImpulseTelemetry();
    expect(events).toHaveLength(2);
    expect(events.map((e) => e.schema_version).sort()).toEqual([1, 2]);
  });

  it('skip_rate = skipped / (selected + skipped); 0 decisions → 0', () => {
    expect(computeSkipRate([])).toBe(0);
    const events: ImpulseTelemetryEvent[] = [
      { schema_version: 2, event: 'impulse_card_skipped', ts: 1, user_id: 'u' },
      { schema_version: 2, event: 'impulse_card_skipped', ts: 2, user_id: 'u' },
      {
        schema_version: 2,
        event: 'impulse_card_selected',
        ts: 3,
        user_id: 'u',
        data: { primary: 'plot', secondary: null },
      },
    ];
    expect(computeSkipRate(events)).toBeCloseTo(2 / 3);
  });

  it('module_completion counts distinct completed modules + first question', () => {
    expect(computeModuleCompletion([])).toEqual({
      completed_modules: 0,
      first_question_answered: false,
    });
    const events: ImpulseTelemetryEvent[] = [
      {
        schema_version: 2,
        event: 'module_completed',
        ts: 1,
        user_id: 'u',
        data: { module_id: '剧情' },
      },
      {
        schema_version: 2,
        event: 'module_completed',
        ts: 2,
        user_id: 'u',
        data: { module_id: '剧情' }, // duplicate — counted once
      },
      {
        schema_version: 2,
        event: 'module_completed',
        ts: 3,
        user_id: 'u',
        data: { module_id: '世界本体' },
      },
      {
        schema_version: 2,
        event: 'first_question_answered',
        ts: 4,
        user_id: 'u',
        data: { elapsed_ms: 900 },
      },
    ];
    expect(computeModuleCompletion(events)).toEqual({
      completed_modules: 2,
      first_question_answered: true,
    });
  });

  it('mismatch map: stated impulse with zero module completion = mismatched', () => {
    // 语义：completed_modules 为全局去重完成数——存在任一完成行为即视为
    // 有行为面；仅当"自报了冲动但全局零完成"时标 mismatched。
    const events: ImpulseTelemetryEvent[] = [
      {
        schema_version: 2,
        event: 'impulse_card_selected',
        ts: 1,
        user_id: 'u',
        data: { primary: 'romance', secondary: null },
      },
      {
        schema_version: 2,
        event: 'impulse_card_selected',
        ts: 2,
        user_id: 'u',
        data: { primary: 'plot', secondary: null },
      },
    ];
    const map = computeStatedBehaviorMismatchMap(events);
    expect(map.romance).toEqual({
      selected: 1,
      skipped: 0,
      completed_modules: 0,
      mismatched: true,
    });
    expect(map.plot).toEqual({
      selected: 1,
      skipped: 0,
      completed_modules: 0,
      mismatched: true,
    });
  });

  it('mismatch map: any module completion behavior clears the mismatch flag', () => {
    const events: ImpulseTelemetryEvent[] = [
      {
        schema_version: 2,
        event: 'impulse_card_selected',
        ts: 1,
        user_id: 'u',
        data: { primary: 'romance', secondary: null },
      },
      {
        schema_version: 2,
        event: 'module_completed',
        ts: 2,
        user_id: 'u',
        data: { module_id: '剧情' },
      },
    ];
    const map = computeStatedBehaviorMismatchMap(events);
    expect(map.romance).toEqual({
      selected: 1,
      skipped: 0,
      completed_modules: 1,
      mismatched: false,
    });
  });

  it('mismatch map is empty for behavior-only logs (no stated impulse)', () => {
    const events: ImpulseTelemetryEvent[] = [
      {
        schema_version: 2,
        event: 'module_completed',
        ts: 1,
        user_id: 'u',
        data: { module_id: '剧情' },
      },
    ];
    expect(computeStatedBehaviorMismatchMap(events)).toEqual({});
  });

  it('metrics tolerate v1 events (version-tolerant derived computation)', () => {
    const v1: ImpulseTelemetryEvent = {
      schema_version: 1,
      event: 'impulse_card_skipped',
      ts: 1,
      user_id: 'u',
    };
    expect(computeSkipRate([v1])).toBe(1);
  });
});
