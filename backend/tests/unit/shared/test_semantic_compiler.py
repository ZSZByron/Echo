"""语义编译器测试 - 使用FakeCompiler确定性测试"""

import pytest
from app.domains.creation.shared.semantic_compiler import (
    Write,
    Suggestion,
    ClassificationProposal,
    CompileResult,
    FakeCompiler
)


class TestCompileResultContract:
    """测试CompileResult契约不变式"""
    
    def test_exclusive_invariant_both_valid(self):
        """测试二选一不变式：writes和proposal不能同时有值"""
        with pytest.raises(ValueError, match="违反二选一不变式"):
            CompileResult(
                writes=[Write(field="test", value="value")],
                classification_proposal=ClassificationProposal(
                    suggestions=[Suggestion(field="test")]
                ),
                source="test"
            )
    
    def test_exclusive_invariant_writes_only(self):
        """测试：仅writes是合法的"""
        result = CompileResult(
            writes=[Write(field="title", value="test")],
            classification_proposal=None,
            source="seed"
        )
        assert len(result.writes) == 1
        assert result.classification_proposal is None
        assert result.source == "seed"
    
    def test_exclusive_invariant_proposal_only(self):
        """测试：仅proposal是合法的"""
        result = CompileResult(
            writes=[],
            classification_proposal=ClassificationProposal(
                suggestions=[Suggestion(field="content", category="创新")]
            ),
            source="llm"
        )
        assert len(result.writes) == 0
        assert result.classification_proposal is not None
        assert len(result.classification_proposal.suggestions) == 1
        assert result.source == "llm"
    
    def test_exclusive_invariant_both_empty(self):
        """测试：两者都空是合法的（边界情况）"""
        result = CompileResult(
            writes=[],
            classification_proposal=None,
            source="unresolved"
        )
        assert len(result.writes) == 0
        assert result.classification_proposal is None


class TestFakeCompiler:
    """测试FakeCompiler确定性实现"""
    
    def setup_method(self):
        """每个测试前创建新的compiler实例"""
        self.compiler = FakeCompiler()
    
    def test_regular_statement_returns_writes(self):
        """测试：常规语句返回writes且无proposal"""
        # 包含"设定"的文本 → 常规write
        result = self.compiler.compile(
            session_id="test-session",
            text="设定标题为测试标题"
        )
        
        # 验证：有writes
        assert len(result.writes) == 1
        assert result.writes[0].field == "标题"
        assert result.writes[0].value == "测试标题"
        
        # 验证：无proposal
        assert result.classification_proposal is None
        
        # 验证：来源
        assert result.source == "seed"
    
    def test_innovative_statement_returns_proposal(self):
        """测试：创新语句返回proposal且无writes"""
        # 包含"分类"的文本 → 分类提案
        result = self.compiler.compile(
            session_id="test-session",
            text="这是一个分类语句"
        )
        
        # 验证：无writes
        assert len(result.writes) == 0
        
        # 验证：有proposal
        assert result.classification_proposal is not None
        assert len(result.classification_proposal.suggestions) == 1
        assert result.classification_proposal.suggestions[0].field == "content"
        assert result.classification_proposal.suggestions[0].category == "创新"
        
        # 验证：来源
        assert result.source == "rule"
    
    def test_fake_compiler_deterministic(self):
        """测试：FakeCompiler确定性（同输入同输出）"""
        text = "设定作者为张三"
        
        # 多次调用同一输入，应得到相同输出
        result1 = self.compiler.compile(session_id="session-1", text=text)
        result2 = self.compiler.compile(session_id="session-2", text=text)
        
        assert result1.writes == result2.writes
        assert result1.classification_proposal == result2.classification_proposal
        assert result1.source == result2.source
    
    def test_fake_compiler_fallback_default(self):
        """测试：其他文本的兜底处理"""
        result = self.compiler.compile(
            session_id="test-session",
            text="普通文本内容"
        )
        
        # 兜底：默认为常规write
        assert len(result.writes) == 1
        assert result.writes[0].field == "content"
        assert result.writes[0].value == "普通文本内容"
        assert result.classification_proposal is None
        assert result.source == "unresolved"
    
    def test_fake_compiler_complex_extraction(self):
        """测试：复杂字段提取逻辑"""
        result = self.compiler.compile(
            session_id="test-session",
            text="设定描述为这是一个很长的描述内容"
        )
        
        assert len(result.writes) == 1
        assert result.writes[0].field == "描述"
        assert result.writes[0].value == "这是一个很长的描述内容"


class TestSemanticCompilerIntegration:
    """集成测试：验证语义编译器契约完整性"""
    
    def test_full_compile_flow_regular(self):
        """测试：完整编译流程 - 常规语句"""
        compiler = FakeCompiler()
        
        result = compiler.compile(
            session_id="user-123",
            text="设定类型为文章"
        )
        
        # 验证：CompileResult二选一不变式
        assert (len(result.writes) > 0) != (result.classification_proposal is not None)
        
        # 验证：常规语句路径
        assert len(result.writes) == 1
        assert result.classification_proposal is None
    
    def test_full_compile_flow_innovative(self):
        """测试：完整编译流程 - 创新语句"""
        compiler = FakeCompiler()
        
        result = compiler.compile(
            session_id="user-456",
            text="需要进行分类处理"
        )
        
        # 验证：CompileResult二选一不变式
        assert (len(result.writes) > 0) != (result.classification_proposal is not None)
        
        # 验证：创新语句路径
        assert len(result.writes) == 0
        assert result.classification_proposal is not None
