/**
 * A1 Graph Section Component Tests
 *
 * TDD: Tests written first to define component behavior before implementation
 * Task 10: Status badge + one-click refinalize + rejected list + pending questions closure
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { A1GraphSection } from '../graph/A1GraphSection';
import type { KnowledgeGraph } from '../../types/graph';

// ResizeObserver stub for jsdom (required by React Flow)
class ResizeObserverStub {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}

declare global {
  interface Window {
    ResizeObserver: typeof ResizeObserverStub;
  }
}

// Setup ResizeObserver before all tests
beforeEach(() => {
  window.ResizeObserver = ResizeObserverStub;
});

// Mock the API modules
vi.mock('../../api/client', () => ({
  fetchJson: vi.fn(),
  ApiError: class extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
    }
  },
}));

vi.mock('../../api/a1', () => ({
  confirmEdge: vi.fn(() => Promise.resolve({ success: true, message: 'Edge confirmed' })),
}));

import { fetchJson } from '../../api/client';
import { confirmEdge } from '../../api/a1';

describe('A1GraphSection - Status Badge (Mechanism 1)', () => {
  const mockFileId = 'test-file-123';
  const mockReturnToChat = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock localStorage
    globalThis.localStorage = {
      getItem: vi.fn(() => null),
      setItem: vi.fn(() => {}),
      removeItem: vi.fn(() => {}),
      clear: vi.fn(() => {}),
      length: 0,
      key: vi.fn(() => null),
    };
  });

  it('should display finalized badge with version number when graph is current', async () => {
    const mockGraph: KnowledgeGraph = {
      scene_id: 'test-scene',
      nodes: {},
      edges: [
        // Mock edge with all required fields for A1KnowledgeGraph
        {
          edge_type: 'tree' as const,
          from_node_id: 'node-1',
          to_node_id: 'node-2',
          visual_description: 'mock relation',
          confidence: '' as const,
          confirmed: true,
          relation: '',
        },
      ],
    };

    vi.mocked(fetchJson).mockResolvedValue(mockGraph);

    render(<A1GraphSection fileId={mockFileId} returnToChat={mockReturnToChat} version={2} isStale={false} />);

    await waitFor(() => {
      expect(screen.getByText(/已定稿 v2/)).toBeInTheDocument();
    });
  });

  it('should display stale warning badge when graph is outdated', async () => {
    const mockGraph: KnowledgeGraph = {
      scene_id: 'test-scene',
      nodes: {},
      edges: [],
    };

    vi.mocked(fetchJson).mockResolvedValue(mockGraph);

    render(<A1GraphSection fileId={mockFileId} returnToChat={mockReturnToChat} version={1} isStale={true} />);

    await waitFor(() => {
      expect(screen.getByText(/设定已更新/)).toBeInTheDocument();
    });
  });

  it('should show old graph with stale badge (not blank) during draft state', async () => {
    const mockGraph: KnowledgeGraph = {
      scene_id: 'test-scene',
      nodes: {
        'node-1': {
          id: 'node-1',
          serial_number: '1',
          level: 1,
          description: 'Test Node',
          status: 'completed',
        },
      },
      edges: [],
    };

    vi.mocked(fetchJson).mockResolvedValue(mockGraph);

    render(<A1GraphSection fileId={mockFileId} returnToChat={mockReturnToChat} version={1} isStale={true} />);

    await waitFor(() => {
      // Old graph should still be visible (nodes are prefixed with ✦)
      expect(screen.getByText('✦ Test Node')).toBeInTheDocument();
      // Stale badge should be shown
      expect(screen.getByText(/设定已更新/)).toBeInTheDocument();
    });
  });
});

describe('A1GraphSection - One-Click Refinalize', () => {
  const mockFileId = 'test-file-123';
  const mockReturnToChat = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.localStorage = {
      getItem: vi.fn(() => null),
      setItem: vi.fn(() => {}),
      removeItem: vi.fn(() => {}),
      clear: vi.fn(() => {}),
      length: 0,
      key: vi.fn(() => null),
    };
  });

  it('should call finalize API when stale badge is clicked', async () => {
    const mockGraph = { nodes: [], edges: [] };
    vi.mocked(fetchJson).mockResolvedValue(mockGraph);

    render(<A1GraphSection fileId={mockFileId} returnToChat={mockReturnToChat} version={1} isStale={true} />);

    await waitFor(() => {
      const staleBadge = screen.getByText(/设定已更新/);
      expect(staleBadge).toBeInTheDocument();
    });

    const refinalizeButton = screen.getByRole('button', { name: /点此重新定稿/ });
    fireEvent.click(refinalizeButton);

    await waitFor(() => {
      expect(fetchJson).toHaveBeenCalledWith(
        `/api/a1/file/${mockFileId}/finalize`,
        expect.objectContaining({ method: 'POST' })
      );
    });
  });

  it('should refresh graph after successful finalize', async () => {
    const mockGraph: KnowledgeGraph = {
      scene_id: 'test-scene',
      nodes: {
        'node-1': {
          id: 'node-1',
          serial_number: '1',
          level: 1,
          description: 'Old Node',
          status: 'completed',
        },
      },
      edges: [],
    };
    const mockUpdatedGraph: KnowledgeGraph = {
      scene_id: 'test-scene',
      nodes: {
        'node-1': {
          id: 'node-1',
          serial_number: '1',
          level: 1,
          description: 'Updated Node',
          status: 'completed',
        },
      },
      edges: [],
    };

    // T-D: file fetch added for concept_terms — mock by URL so extra calls don't
    // consume the sequential graph mocks. Graph returns old data until the
    // finalize POST happens, then updated data.
    let finalized = false;
    vi.mocked(fetchJson).mockImplementation(async (url: string) => {
      const u = typeof url === 'string' ? url : '';
      if (u.endsWith('/finalize')) {
        finalized = true;
        return { graph_code: 'updated', graph_id: 'new-id' };
      }
      if (u.includes('/graph')) {
        return finalized ? mockUpdatedGraph : mockGraph;
      }
      return {}; // file record (no concept_terms)
    }) as never;

    render(<A1GraphSection fileId={mockFileId} returnToChat={mockReturnToChat} version={1} isStale={true} />);

    await waitFor(() => {
      expect(screen.getByText('✦ Old Node')).toBeInTheDocument();
    });

    const refinalizeButton = screen.getByRole('button', { name: /点此重新定稿/ });
    fireEvent.click(refinalizeButton);

    await waitFor(() => {
      // Graph should reload with updated data
      expect(screen.getByText('✦ Updated Node')).toBeInTheDocument();
    });
  });
});

describe('A1GraphSection - Rejected List (Mechanism 4)', () => {
  const mockFileId = 'test-file-123';
  const mockReturnToChat = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.localStorage = {
      getItem: vi.fn(() => null),
      setItem: vi.fn(() => {}),
      removeItem: vi.fn(() => {}),
      clear: vi.fn(() => {}),
      length: 0,
      key: vi.fn(() => null),
    };
  });

  it('should display expandable rejected list section when rejected edges exist', async () => {
    const mockRejectedEdges = {
      'edge1': { from_node_id: 'A', to_node_id: 'B', relation: '影响' },
      'edge2': { from_node_id: 'C', to_node_id: 'D', relation: '依赖' },
    };

    const mockGraph: KnowledgeGraph = { scene_id: 'test-scene', nodes: {}, edges: [] };
    vi.mocked(fetchJson).mockResolvedValue(mockGraph);

    render(
      <A1GraphSection
        fileId={mockFileId}
        returnToChat={mockReturnToChat}
        version={1}
        isStale={false}
        rejectedEdges={mockRejectedEdges}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/已拒绝清单/)).toBeInTheDocument();
      expect(screen.getByText(/2 条已拒绝边/)).toBeInTheDocument();
    });
  });

  it('should show rejected edges when list is expanded', async () => {
    const mockRejectedEdges = {
      'edge1': { from_node_id: '力量体系', to_node_id: '文明', relation: '影响' },
    };

    const mockGraph: KnowledgeGraph = { scene_id: 'test-scene', nodes: {}, edges: [] };
    vi.mocked(fetchJson).mockResolvedValue(mockGraph);

    render(
      <A1GraphSection
        fileId={mockFileId}
        returnToChat={mockReturnToChat}
        version={1}
        isStale={false}
        rejectedEdges={mockRejectedEdges}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/已拒绝清单/)).toBeInTheDocument();
    });

    // Expand the list
    const expandButton = screen.getByRole('button', { name: /已拒绝清单/ });
    fireEvent.click(expandButton);

    await waitFor(() => {
      expect(screen.getByText('力量体系 → 文明')).toBeInTheDocument();
      expect(screen.getByText('影响')).toBeInTheDocument();
    });
  });

  it('should call confirmEdge when restore button is clicked', async () => {
    const mockRejectedEdges = {
      'edge1': { from_node_id: '力量', to_node_id: '文明', relation: '影响' },
    };

    const mockGraph: KnowledgeGraph = { scene_id: 'test-scene', nodes: {}, edges: [] };
    vi.mocked(fetchJson).mockResolvedValue(mockGraph);

    render(
      <A1GraphSection
        fileId={mockFileId}
        returnToChat={mockReturnToChat}
        version={1}
        isStale={false}
        rejectedEdges={mockRejectedEdges}
      />
    );

    await waitFor(() => {
      const expandButton = screen.getByText(/已拒绝清单/);
      fireEvent.click(expandButton);
    });

    await waitFor(() => {
      const restoreButton = screen.getByText('恢复');
      expect(restoreButton).toBeInTheDocument();
      fireEvent.click(restoreButton);
    });

    await waitFor(() => {
      expect(confirmEdge).toHaveBeenCalledWith(mockFileId, 'edge1');
    });
  });
});

describe('A1GraphSection - Pending Questions UI (P4)', () => {
  const mockFileId = 'test-file-123';
  const mockReturnToChat = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.localStorage = {
      getItem: vi.fn(() => null),
      setItem: vi.fn(() => {}),
      removeItem: vi.fn(() => {}),
      clear: vi.fn(() => {}),
      length: 0,
      key: vi.fn(() => null),
    };
  });

  it('should display pending questions list from open_questions data', async () => {
    const mockOpenQuestions = [
      '力量体系和文明的关系是怎样的？',
      '在这个世界中，骰子的运作机制是什么？',
    ];

    const mockGraph: KnowledgeGraph = { scene_id: 'test-scene', nodes: {}, edges: [] };
    vi.mocked(fetchJson).mockResolvedValue(mockGraph);

    render(
      <A1GraphSection
        fileId={mockFileId}
        returnToChat={mockReturnToChat}
        version={1}
        isStale={false}
        openQuestions={mockOpenQuestions}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/待问 2/)).toBeInTheDocument();
      expect(screen.getByText('力量体系和文明的关系是怎样的？')).toBeInTheDocument();
      expect(screen.getByText('在这个世界中，骰子的运作机制是什么？')).toBeInTheDocument();
    });
  });

  it('should set a1_return_intent to "chat" and call returnToChat when "去回答" is clicked', async () => {
    const mockOpenQuestions = ['力量体系和文明的关系是怎样的？'];
    const mockGraph: KnowledgeGraph = { scene_id: 'test-scene', nodes: {}, edges: [] };
    vi.mocked(fetchJson).mockResolvedValue(mockGraph);

    const mockSetItem = vi.fn();
    globalThis.localStorage.setItem = mockSetItem;

    render(
      <A1GraphSection
        fileId={mockFileId}
        returnToChat={mockReturnToChat}
        version={1}
        isStale={false}
        openQuestions={mockOpenQuestions}
      />
    );

    await waitFor(() => {
      const goAnswerButton = screen.getByText('去回答 →');
      expect(goAnswerButton).toBeInTheDocument();
      fireEvent.click(goAnswerButton);
    });

    await waitFor(() => {
      expect(mockSetItem).toHaveBeenCalledWith('a1_return_intent', 'chat');
      expect(mockReturnToChat).toHaveBeenCalled();
    });
  });

  it('should not display pending questions section when open_questions is empty', async () => {
    const mockGraph: KnowledgeGraph = { scene_id: 'test-scene', nodes: {}, edges: [] };
    vi.mocked(fetchJson).mockResolvedValue(mockGraph);

    render(
      <A1GraphSection
        fileId={mockFileId}
        returnToChat={mockReturnToChat}
        version={1}
        isStale={false}
        openQuestions={[]}
      />
    );

    await waitFor(() => {
      expect(screen.queryByText(/待问/)).not.toBeInTheDocument();
    });
  });
});

describe('A1GraphSection - Fullscreen Layout + Guide (T-C)', () => {
  const mockFileId = 'test-file-123';
  const mockReturnToChat = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.localStorage = {
      getItem: vi.fn(() => null),
      setItem: vi.fn(() => {}),
      removeItem: vi.fn(() => {}),
      clear: vi.fn(() => {}),
      length: 0,
      key: vi.fn(() => null),
    };
  });

  const mockGraph: KnowledgeGraph = {
    scene_id: 'test-scene',
    nodes: {
      'term:死亡转生': {
        id: 'term:死亡转生',
        serial_number: '',
        level: 4,
        description: '死亡转生',
        status: 'completed',
      },
    },
    edges: [
      {
        from_node_id: 'term:死亡转生',
        to_node_id: 'term:血月',
        edge_type: 'cross' as const,
        visual_description: 'AI 推断关联',
        relation: '关联',
        confidence: 'semantic' as const,
        confirmed: false,
      },
    ],
  };

  it('should render fullscreen fixed inset-0 container', async () => {
    vi.mocked(fetchJson).mockResolvedValue(mockGraph);
    const { container } = render(
      <A1GraphSection fileId={mockFileId} returnToChat={mockReturnToChat} />
    );

    await waitFor(() => {
      const shell = container.querySelector('[data-testid="a1-graph-fullscreen"]');
      expect(shell).toBeInTheDocument();
      expect(shell?.className).toContain('fixed');
      expect(shell?.className).toContain('inset-0');
    });
  });

  it('should show concept guide bar on first concept-net visit and dismiss via 知道了', async () => {
    vi.mocked(fetchJson).mockResolvedValue(mockGraph);
    render(<A1GraphSection fileId={mockFileId} returnToChat={mockReturnToChat} />);

    // Switch to concept tab
    fireEvent.click(await screen.findByText('概念网'));

    // Guide bar visible (first visit)
    const guideBar = await screen.findByTestId('concept-guide-bar');
    expect(guideBar.textContent).toContain('概念关联网');
    expect(guideBar.textContent).toContain('右侧清单');

    // Dismiss persists to localStorage
    fireEvent.click(screen.getByText('知道了'));
    expect(localStorage.setItem).toHaveBeenCalledWith('a1_concept_guide_seen', '1');
    expect(screen.queryByTestId('concept-guide-bar')).not.toBeInTheDocument();
  });

  it('should render EdgeReviewPanel with concept edges in concept mode', async () => {
    vi.mocked(fetchJson).mockResolvedValue(mockGraph);
    render(<A1GraphSection fileId={mockFileId} returnToChat={mockReturnToChat} />);

    fireEvent.click(await screen.findByText('概念网'));

    const panel = await screen.findByTestId('edge-review-panel');
    expect(panel).toBeInTheDocument();
    expect(panel.textContent).toContain('死亡转生');
  });
});
