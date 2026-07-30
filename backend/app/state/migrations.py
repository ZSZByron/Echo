"""Database initialization scripts."""

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS player_state (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# -- Knowledge graph tables (graph.db) --

CREATE_GRAPH_NODES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS graph_nodes (
    id TEXT NOT NULL,
    scene_id TEXT NOT NULL,
    serial_number TEXT NOT NULL,
    level INTEGER NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    background_flag INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, scene_id)
);
"""

CREATE_GRAPH_EDGES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS graph_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id TEXT NOT NULL,
    from_node_id TEXT NOT NULL,
    to_node_id TEXT NOT NULL,
    edge_type TEXT NOT NULL DEFAULT 'tree',
    visual_description TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
