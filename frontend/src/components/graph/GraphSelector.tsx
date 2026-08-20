import { useState } from 'react';

export interface ChangeSet {
  diff_summary: string;
  upstream_version: string;
}

export interface GraphInfo {
  graph_id: string;
  graph_code: string;
  status: 'finalized' | 'stale';
  change_set?: ChangeSet;
}

export interface GraphSelectorProps {
  graphs: GraphInfo[];
  selectedId: string | null;
  onSelect: (graphId: string) => void;
  onUseStale?: (graphId: string, choice: 'leave_trace' | 'regenerate') => void;
}

export function GraphSelector({ graphs, selectedId, onSelect, onUseStale }: GraphSelectorProps) {
  const [showChangeSet, setShowChangeSet] = useState<string | null>(null);
  const [showConfirmCard, setShowConfirmCard] = useState<string | null>(null);

  const handleGraphClick = (graph: GraphInfo) => {
    if (graph.status === 'stale' && onUseStale) {
      setShowConfirmCard(graph.graph_id);
    } else {
      onSelect(graph.graph_id);
    }
  };

  const handleConfirmChoice = (graphId: string, choice: 'leave_trace' | 'regenerate') => {
    onUseStale?.(graphId, choice);
    setShowConfirmCard(null);
  };

  return (
    <div className="bg-slate-950 rounded-lg border border-slate-800 p-6 space-y-4">
      <h2 className="text-lg font-semibold text-white mb-4">Select Upstream Graph</h2>

      {graphs.map((graph) => (
        <div key={graph.graph_id} className="relative">
          {/* Graph item */}
          <div
            onClick={() => handleGraphClick(graph)}
            className={`p-4 rounded-lg border cursor-pointer transition-all ${
              selectedId === graph.graph_id
                ? 'border-indigo-500 bg-indigo-950/30'
                : 'border-slate-700 bg-slate-900 hover:border-slate-600'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="text-white font-medium">{graph.graph_code}</div>
                <div className="text-slate-400 text-sm">{graph.graph_id}</div>
              </div>

              <div className="flex items-center gap-3">
                {graph.status === 'stale' && (
                  <>
                    <span className="px-3 py-1 bg-yellow-900/50 text-yellow-300 border border-yellow-700/50 rounded-full text-xs font-medium">
                      STALE
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowChangeSet(showChangeSet === graph.graph_id ? null : graph.graph_id);
                      }}
                      className="text-indigo-400 hover:text-indigo-300 text-sm"
                    >
                      View Changes
                    </button>
                  </>
                )}
                <div
                  className={`w-4 h-4 rounded-full border-2 ${
                    selectedId === graph.graph_id
                      ? 'bg-indigo-600 border-indigo-600'
                      : 'border-slate-600'
                  }`}
                />
              </div>
            </div>

            {/* Change set tooltip */}
            {showChangeSet === graph.graph_id && graph.change_set && (
              <div className="mt-3 p-3 bg-slate-800 rounded border border-slate-700">
                <div className="text-yellow-400 text-xs font-medium mb-1">
                  Changes from {graph.change_set.upstream_version}
                </div>
                <p className="text-slate-300 text-sm">{graph.change_set.diff_summary}</p>
              </div>
            )}

            {/* Confirmation card for stale graphs */}
            {showConfirmCard === graph.graph_id && (
              <div className="mt-4 p-4 bg-slate-800 rounded-lg border border-slate-600">
                <div className="text-white font-medium mb-3">
                  This graph is stale. Choose an action:
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => handleConfirmChoice(graph.graph_id, 'leave_trace')}
                    className="flex-1 bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 transition-colors"
                  >
                    Use with Trace
                  </button>
                  <button
                    onClick={() => handleConfirmChoice(graph.graph_id, 'regenerate')}
                    className="flex-1 bg-slate-700 text-white px-4 py-2 rounded hover:bg-slate-600 transition-colors"
                  >
                    Regenerate
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
