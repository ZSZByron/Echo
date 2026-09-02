# Decisions

## Task 0 备份完成

**完成时间**: 2026-08-31

**备份详情**:
- 提交SHA: `d0f9a254ed7c905ea4fdda89e8ce46ab7c90bc86`
- 标签SHA: `8fb907b8905cb2a3db77cf6ad2408fbd55d35a9b` (tag object) → `d0f9a25` (commit)
- 标签名: `backup-8.31-pre-concept-net`
- 推送结果: 成功（分支 + 标签均已推送到 origin）

**基线测试计数**:
- 测试总数: **692 tests**
- 收集命令: `python -m pytest --co -q -p no:cacheprovider`
- 执行位置: `H:\UGC\backend`

**gitignore 清理**:
- 新增 6 个模式: `.coverage.*`, `/*.png`, `backend/experiments/results/`, `data/assets/visual_bg/`, `data/*.jsonl`, `backend/data/*.txt`
- 效果: 57 → 55 文件（2 个生成产物被忽略）

**决策**: 备份完整，可作为后续所有 A1-A7 任务回滚点。


## Task 4 完成方式决策

**完成时间**: 2026-09-01

**完成方式**: 两阶段协作
- **阶段1**（前序代理）: guide_engine.py 写入守卫实现 + test_write_guard.py/test_guide_engine.py 扩展
- **阶段2**（收尾代理）: 存量测试迁移 + 证据路径修复 + 证据记录 + 提交

**关键决策**:
1. **存量测试迁移**: test_handle_message_overwrite_emits_diff 从旧契约（直接覆盖+file_diff）迁移到 G1 契约（拦截+提案+next_question=None）
   - 理由: G1 写入守卫改变了非空字段覆盖行为，测试需反映新契约
   - 影响: Task 6 chat 路由集成依赖此契约（拦截时响应结构）

2. **证据路径修复**: test_concept_edge_vocab.py 中 Path(".sisyphus/evidence") 改为 Path(__file__).resolve().parents[4]/".sisyphus"/"evidence"
   - 理由: 相对路径从 backend 运行时错误落到 backend/.sisyphus/，需绝对路径定位仓库根

3. **清理误生成物**: 删除 backend/.sisyphus/（内含误生成的 untracked 证据文件）
   - 理由: 正确证据位置在仓库根 .sisyphus/evidence/，backend 下的产物是路径错误导致

**测试覆盖**: 759 passed (758 基线 + 1 修复后)
