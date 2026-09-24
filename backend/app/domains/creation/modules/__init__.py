# -*- coding: utf-8 -*-
"""甲 M3：产出模块域（A2 资产回收，family="output"）。

三件入池（plan TODO 3；D15 裁决已定）：
- ``main_module``：主模组文字版（finalize 八步 S1:397-410 / 九节树 S2:385-403 /
  LLM module_compile 单点 + 确定性降级）
- ``dice_projector``：骰子投影（封闭三枚举 S1:292-308 / 四步法 S2:449-466 /
  signal_sources 五链溯源）
- ``character_projector``：角色投影（4 相位 + 常量/变量/锚点 + 缺骰子
  409 missing_dice_template 契约 S1:247）
- ``output_modules``：产出模块池清单数据（family="output" 纯数据面，
  由 shared/module_registry 入池）

纪律（D-A2-4 普适化）：LLM 只产文案与建议，永不产结构与数值——骰子/角色
投影零 LLM 纯确定性；主模组 LLM 仅在 module_compile 单点产 prose，骨架/数值
由确定性代码装配，失败降级骨架 + ledger 披露。产出模块不进访谈配方
（不进问题流/recipes），仅经 a1_routes 端点在 finalize 后按需触发。
"""
from app.domains.creation.modules import output_modules
from app.domains.creation.modules.character_projector import (
    DiceRequiredError,
    TemplatePhase,
    project_character_template,
)
from app.domains.creation.modules.dice_projector import (
    DiceCoreType,
    DifficultySystem,
    GrowthSystem,
    project_dice_template,
)
from app.domains.creation.modules.main_module import (
    NINE_SECTION_HEADINGS,
    ModuleDocument,
    ScopeBoundary,
    compile_document,
    render_markdown,
)

__all__ = [
    "output_modules",
    "DiceRequiredError",
    "TemplatePhase",
    "project_character_template",
    "DiceCoreType",
    "DifficultySystem",
    "GrowthSystem",
    "project_dice_template",
    "NINE_SECTION_HEADINGS",
    "ModuleDocument",
    "ScopeBoundary",
    "compile_document",
    "render_markdown",
]
