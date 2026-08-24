
## T4: Graph Registry + Stale Marker (2026-08-20)

- **ISO timestamp sort pitfall**: datetime.isoformat() with +00:00 timezone suffix breaks lexicographic DESC sort in SQLite. Fix: use strftime('%Y-%m-%dT%H:%M:%S.%f') for UTC without offset.
- **Write tool path escaping**: backslashes in filePath get mangled on some paths. Workaround: use Bash Set-Content to copy from temp, or use forward slashes.
- **Test ordering with time.sleep**: 10ms sleep insufficient on Windows for sub-second timestamp discrimination. 50ms works reliably.
- **graph_code_issuer.py pattern**: sync sqlite3 + WAL + PRAGMA busy_timeout=5000 + per-operation connections. Reused for stale_marker.py.
- **Route registration**: main.py uses include_router pattern, 2-line addition (import + include).
- **DB path convention**: ASSETS_DIR / "ugc.db" from pp.config.paths, module-level constant _REGISTRY_DB.
- **Pyright dict typing**: dict[str, list[dict]] causes false positives when accessing string keys. Use dict[str, dict] for heterogeneous dict values.

## T4 Stale Marker (2026-08-20)

- graph_registry is a standalone table (not modifying graph_nodes). Schema: graph_id(PK), user_id, scene_id, graph_code, ip_code, display_name, stage, instance_no, version, status, parent_graph_code, change_set, used_stale, created_at. UNIQUE(user_id, graph_code).
- stale_marker.py uses sync sqlite3 with per-call connections (same pattern as graph_code_issuer.py). Functions accept db_path: str|Path.
- mark_downstream_stale is idempotent: WHERE status != 'stale' ensures no double-count. Returns rowcount.
- GET /api/graphs lives in a SEPARATE router (graph_registry_routes.py), NOT in graph_routes.py. Existing endpoints untouched.
- Route uses monkeypatch-friendly module-level _REGISTRY_DB for test injection.
- ip_code extracted via simple split('-')[0] — works for all StageCode formats.
- list_user_graphs groups by ip_code, orders artifacts by created_at DESC + graph_code DESC.
- Full suite: 475 passed (468 baseline + 7 new), 0 failed.
