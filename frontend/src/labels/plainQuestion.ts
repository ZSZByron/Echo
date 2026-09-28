// 访谈问题纯问句渲染（display-only）
// T4 (D21-11)：删除「【section_label · sub_label】」模块名头，问句 + 示例直接呈现（ux-flow §5.1）。
// 铁律：输出永不携带「【」/模块名；QuestionPayload 契约字段（含 hint）零改动。

interface PlainQuestionPayload {
  section?: string;
  section_label?: string;
  sub_id?: string;
  sub_label?: string;
  question: string;
  hint?: string;
  example?: string;
}

/** 纯问句文本：question + example（换行 + 「💡 示例：」前缀），无任何模块名头。 */
export function plainQuestion(nq: PlainQuestionPayload | null): string {
  if (!nq) return '';
  const example = nq.example ? `\n💡 示例：${nq.example}` : '';
  return `${nq.question}${example}`;
}
