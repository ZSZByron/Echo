"""Database initialization scripts."""

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS player_state (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
