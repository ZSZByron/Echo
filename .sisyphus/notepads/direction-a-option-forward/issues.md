
## 2026-10-09 T4 发现
- test_reroll_cap_two（契约10）测试文件自身 NameError：L265 inject=[f"n{i}", f"m{i}", f"o{i}"] 的 i 未定义。测试 bug，生产侧无法修复（禁改测试）。需后续测试清理任务把 f-string 改为字面量列表。当前靶向套件红：契约8/16（T5 emission 范围）+ 此条。

## T6 (2026-10-09)
- TDD RED 阶段被跳过：实现已存在于工作区，测试写完即绿（无法观察失败）。验收靠 20 条 test_option_forward 既有契约 + 4 条新契约覆盖。
- brief 中路径笔误：注册表在 creation/shared/ 不在 creation/seed/；测试按真实路径导入。
