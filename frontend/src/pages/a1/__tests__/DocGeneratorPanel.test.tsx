/**
 * DocGeneratorPanel tests — written first (RED).
 *
 * Coverage:
 * ① Click markdown doc button → POST generate + GET markdown → modal shows content
 * ② Loading state while generating (LLM latency, seconds)
 * ③ 409 pending_finalize → honest error in modal, never silent
 * ④ TC missing_dice_template → auto generateDiceTemplate then retry once
 * ⑤ Modal close (close button / ESC / backdrop)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { DocGeneratorPanel } from '../../../components/poster/DocGeneratorPanel';

vi.mock('../../../api/client', () => ({
  ApiError: class extends Error {
    status: number;
    body: unknown;
    constructor(status: number, body: unknown) {
      super(`HTTP ${status}`);
      this.name = 'ApiError';
      this.status = status;
      this.body = body;
    }
  },
}));

vi.mock('../../../api/a1', () => ({
  generateDoc: vi.fn(),
  fetchDocMarkdown: vi.fn(),
  generateWorldBible: vi.fn(),
  fetchWorldBibleMarkdown: vi.fn(),
  generateCharacterCodex: vi.fn(),
  fetchCharacterCodexMarkdown: vi.fn(),
  generateStoryOutline: vi.fn(),
  fetchStoryOutlineMarkdown: vi.fn(),
  generateDiceTemplate: vi.fn(),
  generateCharacterTemplate: vi.fn(),
}));

import {
  generateDoc,
  fetchDocMarkdown,
  generateDiceTemplate,
  generateCharacterTemplate,
} from '../../../api/a1';
import { ApiError } from '../../../api/client';

describe('DocGeneratorPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    render(<DocGeneratorPanel fileId="f-123" />);
  });

  it('renders 生成文档 section with 6 buttons', () => {
    expect(screen.getByText('生成文档')).toBeInTheDocument();
    for (const label of ['主模组', '世界圣经', '人物志', '故事大纲', '骰子模板', '角色模板']) {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument();
    }
  });

  it('① click 主模组 → POST generate → GET markdown → modal shows content', async () => {
    vi.mocked(generateDoc).mockResolvedValue({
      doc_code: 'IP-M01-v1',
      graph_id: 'g1',
      used_stale: false,
      ledger: [],
    });
    vi.mocked(fetchDocMarkdown).mockResolvedValue('# 主模组\n\n第一幕：觉醒');

    fireEvent.click(screen.getByRole('button', { name: '主模组' }));

    await waitFor(() => {
      expect(generateDoc).toHaveBeenCalledWith('f-123');
      expect(fetchDocMarkdown).toHaveBeenCalledWith('f-123');
      expect(screen.getByText('第一幕：觉醒')).toBeInTheDocument();
    });
  });

  it('② shows loading state while generating', async () => {
    vi.mocked(generateDoc).mockReturnValue(new Promise(() => {}));

    fireEvent.click(screen.getByRole('button', { name: '主模组' }));

    await waitFor(() => {
      expect(screen.getByText('生成中...')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: '主模组' })).toBeDisabled();
  });

  it('③ 409 pending_finalize → honest error message in modal', async () => {
    vi.mocked(generateDoc).mockRejectedValue(
      new ApiError(409, { detail: 'pending_finalize' })
    );

    fireEvent.click(screen.getByRole('button', { name: '主模组' }));

    await waitFor(() => {
      expect(screen.getByText(/尚未定稿/)).toBeInTheDocument();
    });
  });

  it('④ TC missing_dice_template → auto dice-template then retry once', async () => {
    vi.mocked(generateCharacterTemplate)
      .mockRejectedValueOnce(new ApiError(409, { detail: 'missing_dice_template' }))
      .mockResolvedValueOnce({
        graph_code: 'IP-TC01-v1',
        template: { name: '角色卡', attributes: { 力量: '3d6' } },
        used_stale: false,
        warnings: [],
      });
    vi.mocked(generateDiceTemplate).mockResolvedValue({
      graph_code: 'IP-TD01-v1',
      template: { dice: '3d6' },
      used_stale: false,
      warnings: [],
    });

    fireEvent.click(screen.getByRole('button', { name: '角色模板' }));

    await waitFor(() => {
      expect(generateDiceTemplate).toHaveBeenCalledWith('f-123');
      expect(generateCharacterTemplate).toHaveBeenCalledTimes(2);
      expect(screen.getByText('力量')).toBeInTheDocument();
    });
  });

  it('④b TC retry still failing → honest error, not silent', async () => {
    vi.mocked(generateCharacterTemplate)
      .mockRejectedValueOnce(new ApiError(409, { detail: 'missing_dice_template' }))
      .mockRejectedValueOnce(new ApiError(409, { detail: 'missing_dice_template' }));
    vi.mocked(generateDiceTemplate).mockResolvedValue({
      graph_code: 'IP-TD01-v1',
      template: { dice: '3d6' },
      used_stale: false,
      warnings: [],
    });

    fireEvent.click(screen.getByRole('button', { name: '角色模板' }));

    await waitFor(() => {
      expect(generateCharacterTemplate).toHaveBeenCalledTimes(2);
      expect(screen.getByText(/角色模板生成失败/)).toBeInTheDocument();
    });
  });

  it('⑤ dice template renders structured key-value cards, not raw JSON', async () => {
    vi.mocked(generateDiceTemplate).mockResolvedValue({
      graph_code: 'IP-TD01-v1',
      template: { 属性投法: { 力量: '3d6' }, notes: 'zero-llm' },
      used_stale: false,
      warnings: [],
    });

    fireEvent.click(screen.getByRole('button', { name: '骰子模板' }));

    await waitFor(() => {
      expect(screen.getByText('属性投法')).toBeInTheDocument();
      expect(screen.getByText('力量')).toBeInTheDocument();
      expect(screen.getByText('3d6')).toBeInTheDocument();
    });
    expect(screen.queryByText(/{"属性投法"/)).not.toBeInTheDocument();
  });

  it('⑤ close button closes the modal', async () => {
    vi.mocked(generateDoc).mockResolvedValue({
      doc_code: 'IP-M01-v1',
      graph_id: 'g1',
      used_stale: false,
      ledger: [],
    });
    vi.mocked(fetchDocMarkdown).mockResolvedValue('# 主模组');

    fireEvent.click(screen.getByRole('button', { name: '主模组' }));
    await waitFor(() => expect(screen.getByRole('dialog')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: '关闭' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('⑤ ESC key closes the modal', async () => {
    vi.mocked(generateDoc).mockResolvedValue({
      doc_code: 'IP-M01-v1',
      graph_id: 'g1',
      used_stale: false,
      ledger: [],
    });
    vi.mocked(fetchDocMarkdown).mockResolvedValue('# 主模组');

    fireEvent.click(screen.getByRole('button', { name: '主模组' }));
    await waitFor(() => expect(screen.getByRole('dialog')).toBeInTheDocument());

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
