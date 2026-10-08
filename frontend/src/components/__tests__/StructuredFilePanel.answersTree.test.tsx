/**
 * StructuredFilePanel answers_tree rendering tests (D23)
 *
 * answers_tree values with non-empty children render as nested child-entry
 * lists; plain strings rendering is unchanged (no tree block without children).
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StructuredFilePanel } from '../structured/StructuredFilePanel';
import type { AnswerNode } from '../../types/a1';

const baseFile = {
  name: 'Test File',
  status: 'draft' as const,
  sections: [],
};

describe('StructuredFilePanel answers_tree', () => {
  it('renders child entries (one indent level) for tree values with children', () => {
    const tree: Record<string, AnswerNode> = {
      'world.history': {
        text: '纪元总述',
        children: [
          { text: '第一纪元：星陨', children: [] },
          { text: '第二纪元：归墟', children: [{ text: '深层补遗', children: [] }] },
        ],
      },
    };

    render(<StructuredFilePanel file={baseFile} answersTree={tree} />);

    expect(screen.getByTestId('answers-tree')).toBeInTheDocument();
    expect(screen.getByText('已确定内容')).toBeInTheDocument();
    const childEntries = screen.getAllByTestId('answer-child-entry');
    expect(childEntries).toHaveLength(3);
    expect(screen.getByText('第一纪元：星陨')).toBeInTheDocument();
    expect(screen.getByText('深层补遗')).toBeInTheDocument();
  });

  it('does not render the tree block when answersTree is absent', () => {
    render(<StructuredFilePanel file={baseFile} />);
    expect(screen.queryByTestId('answers-tree')).not.toBeInTheDocument();
  });

  it('does not render the tree block when no entry has children', () => {
    const tree: Record<string, AnswerNode> = {
      'world.history': { text: '平铺文本', children: [] },
    };
    render(<StructuredFilePanel file={baseFile} answersTree={tree} />);
    expect(screen.queryByTestId('answers-tree')).not.toBeInTheDocument();
  });
});
