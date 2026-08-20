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

from typing import Protocol, runtime_checkable
from pydantic import BaseModel, Field


class FieldWrite(BaseModel):
    """写入字段指令"""
    field: str
    value: str


class Suggestion(BaseModel):
    """分类建议"""
    field: str
    category: str = "其他"  # "其他"仅存不一致内容


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
    writes: list[FieldWrite] = Field(default_factory=list)
    classification_proposal: ClassificationProposal | None = None


@runtime_checkable
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
        - 接受 rules 参数（字典：关键词 → FieldWrite列表）
        - 文本包含关键词 → 返回对应的 writes
        - 文本不包含任何规则 → 返回 classification_proposal
        - 大小写不敏感匹配
    
    注意：
        这是骨架实现，仅用于契约验证和测试。
        真实的词典匹配和LLM调用在断点A任务（T-A）中实现。
    """
    
    def __init__(self, rules: dict[str, list[FieldWrite]] | None = None) -> None:
        """初始化假编译器
        
        Args:
            rules: 关键词到写入列表的映射
        """
        self._rules: dict[str, list[FieldWrite]] = rules or {}
    
    def compile(self, session_id: str, text: str) -> CompileResult:
        """编译自然语言为结构化指令（假实现）"""
        
        # 收集所有匹配的规则
        matched_writes: list[FieldWrite] = []
        text_lower = text.lower()
        
        for keyword, writes in self._rules.items():
            if keyword.lower() in text_lower:
                matched_writes.extend(writes)
        
        # 如果有匹配规则，返回 writes
        if matched_writes:
            return CompileResult(writes=matched_writes)
        
        # 无匹配规则，返回分类提案
        return CompileResult(
            classification_proposal=ClassificationProposal(
                suggestions=[
                    Suggestion(field="content", category="其他")
                ]
            )
        )
