// T4 (D21-11)：访问问题去头（「【section_label · sub_label】」头删除）
// 纯函数测试先行：输出为纯问句（question + example），零模块名泄漏。
import { describe, expect, it } from 'vitest';
import { plainQuestion } from '../plainQuestion';

// fixture 故意携带模块名，用于断言零泄漏
const nqWithModule = {
  section: 'ip_location',
  section_label: 'IP定位',
  sub_id: 'opening',
  sub_label: '世界观背景',
  question: '你故事的开场是哪一幕？',
  hint: '从最有画面感的一刻说起',
  example: '比如主角第一次踏入那个陌生城市。',
};

describe('plainQuestion', () => {
  it('输出不含「【」字符', () => {
    expect(plainQuestion(nqWithModule)).not.toContain('【');
  });

  it('输出不含 section_label / sub_label 值（零模块名泄漏）', () => {
    const out = plainQuestion(nqWithModule);
    expect(out).not.toContain('IP定位');
    expect(out).not.toContain('世界观背景');
  });

  it('question + example 拼接保持（example 以换行 + 💡 示例： 前缀）', () => {
    const out = plainQuestion(nqWithModule);
    expect(out).toContain('你故事的开场是哪一幕？');
    expect(out).toContain('💡 示例：比如主角第一次踏入那个陌生城市。');
    expect(out).toBe('你故事的开场是哪一幕？\n💡 示例：比如主角第一次踏入那个陌生城市。');
  });

  it('无 example 时仅返回问句本体', () => {
    expect(plainQuestion({ ...nqWithModule, example: undefined })).toBe(
      '你故事的开场是哪一幕？'
    );
  });

  it('null 输入返回空串', () => {
    expect(plainQuestion(null)).toBe('');
  });
});
