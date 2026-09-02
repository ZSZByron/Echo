# Learnings
## T9-Part2: A1 Routes API
- Files already existed (a1_routes.py, test_a1_routes.py, main.py registration) - task was verification+fix
- stale_marker.ensure_registry() must be called before register_graph/mark_downstream_stale
- Path corruption bug in bash tool: H:\UGC paths get mangled inline. Workaround: assign to PS variables first
- RealSemanticCompiler(provider=None) gives L1/L2 only, skip section with empty answer
- GraphCodeIssuer W-stage: first call W1-v1, second bumps to W1-v2
- Full regression: 588 passed (baseline 579, +9 new A1 tests)

## 2026-09-02 守卫保护对象辨析（用户值 vs LLM 猜测值）
- 写入守卫（Metis G1）保护的是"用户已确定的内容"，不是"会话里已有的任何值"。
  prefill 值是上传时 LLM 的猜测，用户从未确认——对猜测值走提案制是认知错位，
  曾造成产品级死锁：prefill→finalize门禁→topup全被拦→按钮永灰→进不了图谱。
- 修复模式：来源标记豁免。session.prefill_fields 记录猜测键；_apply_fills
  拦截前检查来源，猜测值被用户口述**直接覆盖**（file_diff 记录 old→new 供右栏
  展示，审核权不丢失），并从 prefill_fields 移除——此后该字段回归正常守卫。
- 通用教训：给拦截类守卫加"数据来源"维度（confirmed vs guessed），
  豁免只针对来源，不弱化守卫本身；豁免必须一次性（用后即收回）。
- 验证教训：Windows 下用 Start-Process 启动的 uvicorn，主进程 PID 对
  Get-Process/Get-CimInstance 不可见，需通过 multiprocessing.spawn 子进程
  的 parent_pid 或 netstat 定位并杀子进程才能释放端口。
