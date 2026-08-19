"""语义编译契约 - 三级匹配架构

契约说明：
    本模块定义语义编译的Protocol契约及三级匹配骨架。
    
    三级匹配级联逻辑（按优先级）：
        Level1 种子库级：预定义种子模式匹配（零LLM成本）
        Level2 词典规则级：词典+规则引擎匹配（零LLM成本）
        Level3 LLM级：前两级无法处理时，调用LLM理解（有LLM成本）
    
    当前实现：
        本任务仅交付契约+骨架结构。真实的词典匹配和LLM调用逻辑
        在断点A任务（T-A）完成后替换注入。
    
    架构目标：
        - 常规语句（设定/描述）：直接生成writes落盘
        - 创新语句（分类/提案）：返回classification_proposal等待用户确认
"""

from typing import Protocol, Optional
from pydantic import BaseModel, field_validator, model_validator


class Write(BaseModel):
    """写入字段指令"""
    field: str
    value: str


class Suggestion(BaseModel):
    """分类建议"""
    field: str
    category: str = "其他"


class ClassificationProposal(BaseModel):
    """分类提案（用户确认前不落盘）"""
    suggestions: list[Suggestion]


class CompileResult(BaseModel):
    """编译结果（二选一不变式）
    
    约束：
        - 常规语句 → writes（有值），classification_proposal=None
        - 创新语句 → classification_proposal（有值），writes=[]
        - 两者互斥，不能同时有值
    """
    writes: list[Write] = []
    classification_proposal: Optional[ClassificationProposal] = None
    source: str = ""  # seed|rule|llm|unresolved

    @model_validator(mode='after')
    def validate_exclusive_result(self):
        """验证二选一不变式：writes和proposal互斥"""
        has_writes = len(self.writes) > 0
        has_proposal = self.classification_proposal is not None

        if has_writes and has_proposal:
            raise ValueError(
                "CompileResult违反二选一不变式："
                "writes和classification_proposal不能同时有值"
            )

        return self


class SemanticCompiler(Protocol):
    """语义编译器契约
    
    实现要求：
        - 必须实现三级匹配级联逻辑
        - Level1/Level2优先使用（零LLM成本）
        - Level3作为兜底（有LLM成本）
    """
    def compile(self, session_id: str, text: str) -> CompileResult:
        """编译自然语言为结构化指令
        
        Args:
            session_id: 会话ID
            text: 用户输入文本
            
        Returns:
            CompileResult: 常规语句返回writes，创新语句返回classification_proposal
        """
        ...


class FakeCompiler:
    """确定性假实现 - 用于测试
    
    规则：
        - 包含"设定"的文本 → 常规write（模拟Level1种子库匹配）
        - 包含"分类"的文本 → 分类提案（模拟创新语句）
        - 其他文本 → 默认write（兜底处理）
    
    注意：
        这是骨架实现，仅用于契约验证和测试。
        真实的词典匹配和LLM调用在断点A任务（T-A）中实现。
    """
    
    def compile(self, session_id: str, text: str) -> CompileResult:
        """编译自然语言为结构化指令（假实现）"""
        
        if "设定" in text:
            # 模拟常规语句：提取字段设定
            # 示例: "设定标题为xxx" → Write(field="标题", value="xxx")
            parts = text.replace("设定", "").replace("为", "｜").split("｜")
            if len(parts) >= 2:
                field = parts[0].strip()
                value = parts[1].strip()
                return CompileResult(
                    writes=[Write(field=field, value=value)],
                    classification_proposal=None,
                    source="seed"
                )
        
        elif "分类" in text:
            # 模拟创新语句：返回分类提案
            # 示例: "这是一个分类语句" → ClassificationProposal
            return CompileResult(
                writes=[],
                classification_proposal=ClassificationProposal(
                    suggestions=[
                        Suggestion(field="content", category="创新")
                    ]
                ),
                source="rule"
            )
        
        # 兜底：默认为常规write
        return CompileResult(
            writes=[Write(field="content", value=text)],
            classification_proposal=None,
            source="unresolved"
        )
