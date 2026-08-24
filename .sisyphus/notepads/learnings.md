# Learnings
## T9-Part2: A1 Routes API
- Files already existed (a1_routes.py, test_a1_routes.py, main.py registration) - task was verification+fix
- stale_marker.ensure_registry() must be called before register_graph/mark_downstream_stale
- Path corruption bug in bash tool: H:\UGC paths get mangled inline. Workaround: assign to PS variables first
- RealSemanticCompiler(provider=None) gives L1/L2 only, skip section with empty answer
- GraphCodeIssuer W-stage: first call W1-v1, second bumps to W1-v2
- Full regression: 588 passed (baseline 579, +9 new A1 tests)
