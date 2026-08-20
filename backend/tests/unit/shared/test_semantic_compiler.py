"""语义编译器测试 - 使用FakeCompiler确定性测试"""

import pytest
from app.domains.creation.shared.semantic_compiler import (
    FieldWrite,
    Suggestion,
    ClassificationProposal,
    CompileResult,
    FakeCompiler,
    SemanticCompiler,
)


class TestCompileResultContract:
    """测试CompileResult契约不变式"""
    
    def test_exclusive_invariant_writes_only(self):
        """测试：仅writes是合法的"""
        result = CompileResult(
            writes=[FieldWrite(field="title", value="test")]
        )
        assert len(result.writes) == 1
        assert result.classification_proposal is None
    
    def test_exclusive_invariant_proposal_only(self):
        """测试：仅proposal是合法的"""
        result = CompileResult(
            classification_proposal=ClassificationProposal(
                suggestions=[Suggestion(field="content", category="创新")]
            )
        )
        assert len(result.writes) == 0
        assert result.classification_proposal is not None
        assert len(result.classification_proposal.suggestions) == 1
    
    def test_exclusive_invariant_both_empty(self):
        """测试：两者都空是合法的（边界情况）"""
        result = CompileResult()
        assert len(result.writes) == 0
        assert result.classification_proposal is None
    
    def test_protocol_isinstance_check(self):
        """测试：runtime_checkable Protocol支持isinstance"""
        compiler = FakeCompiler()
        assert isinstance(compiler, SemanticCompiler)


class TestFakeCompiler:
    """测试FakeCompiler确定性实现"""
    
    def test_fake_compiler_init_empty_rules(self):
        """测试：空规则初始化"""
        compiler = FakeCompiler()
        assert compiler._rules == {}
    
    def test_fake_compiler_init_with_rules(self):
        """测试：带规则初始化"""
        rules = {
            "sword": [FieldWrite(field="type", value="武器")],
            "fire": [FieldWrite(field="element", value="火")],
        }
        compiler = FakeCompiler(rules=rules)
        assert compiler._rules == rules
    
    def test_compile_no_rule_match_returns_proposal(self):
        """测试：无匹配规则返回提案"""
        compiler = FakeCompiler()
        result = compiler.compile("session_1", "未知创新内容")
        
        # 无匹配规则，返回提案
        assert result.writes == []
        assert result.classification_proposal is not None
        assert len(result.classification_proposal.suggestions) == 1
    
    def test_compile_with_rule_match_returns_writes(self):
        """测试：匹配规则返回writes"""
        rules = {
            "dragon": [FieldWrite(field="creature_type", value="龙")],
        }
        compiler = FakeCompiler(rules=rules)
        result = compiler.compile("session_1", "Red dragon appears")
        
        # 匹配成功，返回writes
        assert len(result.writes) == 1
        assert result.writes[0].field == "creature_type"
        assert result.writes[0].value == "龙"
        assert result.classification_proposal is None
    
    def test_compile_case_insensitive(self):
        """测试：大小写不敏感匹配"""
        rules = {
            "CRYSTAL": [FieldWrite(field="material", value="水晶")],
        }
        compiler = FakeCompiler(rules=rules)
        
        result1 = compiler.compile("session_1", "crystal sword")
        result2 = compiler.compile("session_2", "CRYSTAL SHIELD")
        result3 = compiler.compile("session_3", "Crystal Wand")
        
        assert len(result1.writes) == 1
        assert len(result2.writes) == 1
        assert len(result3.writes) == 1
    
    def test_compile_multiple_rules_match(self):
        """测试：多个规则匹配合并writes"""
        rules = {
            "fire": [FieldWrite(field="element", value="火")],
            "sword": [FieldWrite(field="category", value="武器")],
        }
        compiler = FakeCompiler(rules=rules)
        result = compiler.compile("session_1", "Fire sword created")
        
        # 两个规则都匹配
        assert len(result.writes) == 2
        fields = {write.field for write in result.writes}
        assert "element" in fields
        assert "category" in fields
    
    def test_compile_deterministic(self):
        """测试：确定性（同输入同输出）"""
        rules = {
            "test": [FieldWrite(field="key", value="value")],
        }
        compiler = FakeCompiler(rules=rules)
        
        result1 = compiler.compile("session_1", "test input")
        result2 = compiler.compile("session_2", "test input")
        
        assert result1.writes == result2.writes
        assert result1.classification_proposal == result2.classification_proposal


class TestSemanticCompilerIntegration:
    """集成测试：验证语义编译器契约完整性"""
    
    def test_full_compile_flow_regular(self):
        """测试：完整编译流程 - 常规语句（有规则匹配）"""
        rules = {
            "article": [FieldWrite(field="type", value="文章")],
        }
        compiler = FakeCompiler(rules=rules)
        
        result = compiler.compile(
            session_id="user-123",
            text="Create article post"
        )
        
        # 验证：CompileResult二选一不变式
        assert (len(result.writes) > 0) != (result.classification_proposal is not None)
        
        # 验证：常规语句路径
        assert len(result.writes) == 1
        assert result.classification_proposal is None
    
    def test_full_compile_flow_innovative(self):
        """测试：完整编译流程 - 创新语句（无规则匹配）"""
        compiler = FakeCompiler()
        
        result = compiler.compile(
            session_id="user-456",
            text="未知创新内容需要分类"
        )
        
        # 验证：CompileResult二选一不变式
        assert (len(result.writes) > 0) != (result.classification_proposal is not None)
        
        # 验证：创新语句路径
        assert len(result.writes) == 0
        assert result.classification_proposal is not None
    
    def test_three_level_matching_skeleton(self):
        """测试：三级匹配骨架结构"""
        # Level 1 & 2: 规则匹配（零LLM成本）
        rules = {
            "crystal": [FieldWrite(field="material", value="水晶")],
            "create": [FieldWrite(field="action", value="create")],
        }
        compiler = FakeCompiler(rules=rules)
        
        # 规则命中 → 直接返回writes
        result = compiler.compile("session_1", "Create crystal item")
        assert len(result.writes) == 2
        assert result.classification_proposal is None
        
        # Level 3: 无规则匹配 → 返回提案（模拟LLM级）
        result2 = compiler.compile("session_2", "quantum innovation device")
        assert len(result2.writes) == 0
        assert result2.classification_proposal is not None
