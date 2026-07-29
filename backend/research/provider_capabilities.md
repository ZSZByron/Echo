# LLM Provider JSON Mode Capabilities Research

**Date**: 2026-07-25  
**Purpose**: Evaluate JSON output capabilities for Echo Demo AI service layer  
**Context**: T6 (AI service layer) will reference this document for implementation strategy

---

## Executive Summary

| Provider | Native JSON Mode | Schema Enforcement | Recommended Strategy |
|----------|------------------|-------------------|---------------------|
| **OpenAI** | ✅ Yes (Structured Outputs) | ✅ Yes (100% guarantee) | **Use JSON Schema** |
| **Anthropic** | ✅ Yes (Structured Outputs) | ✅ Yes (constrained decoding) | **Use JSON Schema** |
| **DeepSeek** | ✅ Yes (JSON Object mode) | ❌ No (prompt-based) | JSON mode + Pydantic fallback |
| **Qwen** | ✅ Yes (OpenAI-compatible) | ⚠️ Partial (JSON object only) | JSON mode + Pydantic fallback |
| **Kimi** | ✅ Yes (OpenAI-compatible) | ⚠️ Partial (JSON object only) | JSON mode + Pydantic fallback |
| **GLM** | ✅ Yes (OpenAI-compatible) | ⚠️ Partial (JSON object only) | JSON mode + Pydantic fallback |

---

## Detailed Analysis

### 1. OpenAI (gpt-4o-mini)

#### JSON Mode Capabilities
- **Feature**: Structured Outputs (JSON Schema with `strict: true`)
- **Method**: `response_format: {type: "json_schema", strict: true, schema: {...}}`
- **SDK Support**: Native Pydantic integration via `.beta.chat.completions.parse()`
- **Model Support**: gpt-4o-mini, gpt-4o-2024-08-06 and all GPT-5 series
- **Guarantee**: 100% schema adherence through constrained decoding

#### Key Features
- **Schema enforcement**: All required fields present, no extra properties, type-safe enums
- **Refusal handling**: Dedicated `refusal` field for safety rejections
- **Latency**: One-time compilation overhead (~100-500ms first call per schema)
- **Validation keywords**: Only enforces structure, not value constraints (patterns, ranges)

#### Implementation for Echo
```python
from pydantic import BaseModel
from openai import OpenAI

class ParsedIntent(BaseModel):
    action_type: str
    target: str | None
    intensity: str
    risk_acceptance: bool

client = OpenAI()
response = client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[...],
    response_format=ParsedIntent  # Auto-converts to JSON Schema
)
intent = response.choices[0].message.parsed  # Fully typed
```

**Recommendation**: **Primary choice** - Use Structured Outputs with strict mode for both parser and renderer.

---

### 2. Anthropic (claude-3-5-sonnet-20241022)

#### JSON Mode Capabilities
- **Feature**: Structured Outputs (JSON outputs + Strict tool use)
- **Method**: `output_config.format: {type: "json_schema", schema: {...}}`
- **SDK Support**: Native SDK helpers with auto-validation
- **Model Support**: Claude Sonnet 4.5, Opus 4.5, Haiku 4.5 and all Claude 4.5+ series
- **Guarantee**: Schema-compliant responses through constrained decoding

#### Key Features
- **Two modes**: 
  1. JSON outputs (final message as JSON)
  2. Strict tool use (tool arguments validated)
- **Schema transformation**: SDK auto-converts unsupported constraints (minLength, pattern) to descriptions
- **Refusal handling**: Built-in error handling for validation failures
- **Agent SDK support**: Multi-turn workflows with structured final output

#### Implementation for Echo
```python
from anthropic import Anthropic
from pydantic import BaseModel

class ParsedIntent(BaseModel):
    action_type: str
    target: str | None
    intensity: str
    risk_acceptance: bool

client = Anthropic()
response = client.messages.parse(
    model="claude-3-5-sonnet-20241022",
    messages=[...],
    output_format=ParsedIntent  # Auto-converts to JSON Schema
)
intent = response.parsed_output  # Fully typed
```

**Recommendation**: **Primary choice** - Use structured outputs for parser and renderer. Excellent for complex schemas.

---

### 3. DeepSeek (deepseek-chat / deepseek-v4-flash)

#### JSON Mode Capabilities
- **Feature**: JSON Object mode (legacy JSON mode)
- **Method**: `response_format: {type: "json_object"}`
- **SDK Support**: OpenAI-compatible SDK via `base_url` override
- **Model Support**: deepseek-v4-flash, deepseek-v4-pro (legacy IDs: deepseek-chat, deepseek-reasoner)
- **Guarantee**: Valid JSON syntax only, no schema enforcement

#### Key Features
- **Prompt requirements**: 
  - Must include literal word "json" in prompt (API rejects otherwise)
  - Must provide example JSON shape in prompt
  - Set sufficient `max_tokens` to prevent truncation
- **Failure modes**: Empty content, truncation (`finish_reason="length"`), schema drift
- **Alternative**: Strict tool calling (beta) with JSON Schema validation for tool arguments

#### Implementation for Echo
```python
from openai import OpenAI  # Using OpenAI SDK
from pydantic import BaseModel, ValidationError

class ParsedIntent(BaseModel):
    action_type: str
    target: str | None
    intensity: str
    risk_acceptance: bool

client = OpenAI(base_url="https://api.deepseek.com/v1")
response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {
            "role": "system",
            "content": "Return only valid JSON. Use this shape: {\"action_type\":\"string\",\"target\":\"string|null\",\"intensity\":\"string\",\"risk_acceptance\":boolean}"
        },
        {"role": "user", "content": user_input}
    ],
    response_format={"type": "json_object"},
    max_tokens=500
)

# Parse with fallback
try:
    intent = ParsedIntent.model_validate_json(response.choices[0].message.content)
except ValidationError:
    # Fallback to unknown intent
    intent = ParsedIntent(action_type="unknown", target=None, intensity="low", risk_acceptance=False)
```

**Recommendation**: **Secondary choice** - Use JSON mode + Pydantic validation with fallback. Prompt engineering is critical.

---

### 4. Qwen / DashScope (qwen-plus)

#### JSON Mode Capabilities
- **Feature**: OpenAI-compatible JSON mode
- **Method**: `response_format: {type: "json_object"}` (via compatible-mode endpoint)
- **SDK Support**: OpenAI SDK with `base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"`
- **Model Support**: qwen-plus, qwen-turbo, qwen-max (all support JSON mode)
- **Guarantee**: Valid JSON syntax only, no schema enforcement

#### Key Features
- **Compatibility**: Full OpenAI API compatibility for chat completions
- **Prompt requirements**: Should include JSON instruction and example (best practice)
- **Stability**: Stable JSON output for well-structured prompts
- **Fallback**: Pydantic validation required

#### Implementation for Echo
```python
from openai import OpenAI
from pydantic import BaseModel

class ParsedIntent(BaseModel):
    action_type: str
    target: str | None
    intensity: str
    risk_acceptance: bool

client = OpenAI(
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key="..."
)

response = client.chat.completions.create(
    model="qwen-plus",
    messages=[
        {
            "role": "system",
            "content": "Respond in JSON format only. Extract action type and target from user input."
        },
        {"role": "user", "content": user_input}
    ],
    response_format={"type": "json_object"}
)

try:
    intent = ParsedIntent.model_validate_json(response.choices[0].message.content)
except ValidationError:
    intent = ParsedIntent(action_type="unknown", target=None, intensity="low", risk_acceptance=False)
```

**Recommendation**: **Secondary choice** - Use OpenAI-compatible JSON mode + Pydantic fallback.

---

### 5. Kimi / Moonshot (moonshot-v1-8k)

#### JSON Mode Capabilities
- **Feature**: OpenAI-compatible JSON mode
- **Method**: `response_format: {type: "json_object"}` 
- **SDK Support**: OpenAI SDK with `base_url="https://api.moonshot.cn/v1"`
- **Model Support**: moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k
- **Guarantee**: Valid JSON syntax only, no schema enforcement

#### Key Features
- **Compatibility**: Full OpenAI API compatibility
- **Prompt requirements**: Include JSON instruction in system prompt
- **Stability**: Reliable JSON output for structured tasks
- **Fallback**: Pydantic validation required

#### Implementation for Echo
```python
from openai import OpenAI
from pydantic import BaseModel

class ParsedIntent(BaseModel):
    action_type: str
    target: str | None
    intensity: str
    risk_acceptance: bool

client = OpenAI(
    base_url="https://api.moonshot.cn/v1",
    api_key="..."
)

response = client.chat.completions.create(
    model="moonshot-v1-8k",
    messages=[
        {
            "role": "system",
            "content": "Extract structured information as JSON. Action types: brute_force, stealth, read_memory, negotiate, probe, god_provoke, investigate."
        },
        {"role": "user", "content": user_input}
    ],
    response_format={"type": "json_object"}
)

try:
    intent = ParsedIntent.model_validate_json(response.choices[0].message.content)
except ValidationError:
    intent = ParsedIntent(action_type="unknown", target=None, intensity="low", risk_acceptance=False)
```

**Recommendation**: **Secondary choice** - Use OpenAI-compatible JSON mode + Pydantic fallback.

---

### 6. GLM / Zhipu (glm-4)

#### JSON Mode Capabilities
- **Feature**: OpenAI-compatible JSON mode
- **Method**: `response_format: {type: "json_object"}`
- **SDK Support**: OpenAI SDK with `base_url="https://open.bigmodel.cn/api/paas/v4"`
- **Model Support**: glm-4, glm-4-air, glm-4-flash
- **Guarantee**: Valid JSON syntax only, no schema enforcement

#### Key Features
- **Compatibility**: Full OpenAI API compatibility
- **Prompt requirements**: Include JSON instruction and example
- **Stability**: Stable JSON output for clear prompts
- **Fallback**: Pydantic validation required

#### Implementation for Echo
```python
from openai import OpenAI
from pydantic import BaseModel

class ParsedIntent(BaseModel):
    action_type: str
    target: str | None
    intensity: str
    risk_acceptance: bool

client = OpenAI(
    base_url="https://open.bigmodel.cn/api/paas/v4",
    api_key="..."
)

response = client.chat.completions.create(
    model="glm-4",
    messages=[
        {
            "role": "system",
            "content": "Parse user input into structured JSON. Use these fields: action_type, target, intensity, risk_acceptance."
        },
        {"role": "user", "content": user_input}
    ],
    response_format={"type": "json_object"}
)

try:
    intent = ParsedIntent.model_validate_json(response.choices[0].message.content)
except ValidationError:
    intent = ParsedIntent(action_type="unknown", target=None, intensity="low", risk_acceptance=False)
```

**Recommendation**: **Secondary choice** - Use OpenAI-compatible JSON mode + Pydantic fallback.

---

## Recommended Strategy for Echo Demo

### Tier 1: Native Schema Enforcement (Preferred)
**Providers**: OpenAI, Anthropic

Use native Structured Outputs with JSON Schema:
```python
# Preferred implementation
response = client.parse(..., response_format=MySchema)
result = response.parsed  # Guaranteed schema match
```

**Benefits**:
- 100% schema adherence
- No validation code needed
- Type-safe from API to app
- Handles refusals gracefully

### Tier 2: JSON Mode + Fallback (Compatible)
**Providers**: DeepSeek, Qwen, Kimi, GLM

Use OpenAI-compatible JSON mode with Pydantic validation:
```python
# Fallback implementation
response = client.chat.completions.create(..., response_format={"type": "json_object"})
try:
    result = MySchema.model_validate_json(response.choices[0].message.content)
except ValidationError:
    result = MySchema(action_type="unknown", ...)  # Safe fallback
```

**Benefits**:
- Works with OpenAI SDK
- Consistent interface across 4 providers
- Simple fallback pattern
- No breaking changes when switching providers

### Unified Implementation Pattern

```python
# backend/app/ai/parser.py
from typing import Union
from openai import OpenAI
from anthropic import Anthropic
from pydantic import BaseModel, ValidationError

class IntentParser:
    def __init__(self, provider_type: str, config: ProviderConfig):
        if provider_type in ["openai", "deepseek", "qwen", "kimi", "glm"]:
            self.client = OpenAI(base_url=config.base_url, api_key=config.api_key)
            self.use_native_schema = provider_type == "openai"
        elif provider_type == "anthropic":
            self.client = Anthropic(api_key=config.api_key)
            self.use_native_schema = True
        else:
            raise ValueError(f"Unknown provider: {provider_type}")
    
    async def parse(self, user_input: str) -> ParsedIntent:
        try:
            if self.use_native_schema:
                # Use Structured Outputs
                response = self.client.beta.chat.completions.parse(
                    model=config.model,
                    messages=self._build_messages(user_input),
                    response_format=ParsedIntent
                )
                return response.choices[0].message.parsed
            else:
                # Use JSON mode + validation
                response = self.client.chat.completions.create(
                    model=config.model,
                    messages=self._build_messages(user_input),
                    response_format={"type": "json_object"}
                )
                return ParsedIntent.model_validate_json(
                    response.choices[0].message.content
                )
        except (ValidationError, Exception) as e:
            # Fallback for any parsing failure
            return ParsedIntent(
                action_type="unknown",
                target=None,
                intensity="low",
                risk_acceptance=False
            )
```

---

## Testing Recommendations

### Unit Tests (Mock)
- Mock provider responses for both success and failure cases
- Test fallback behavior on ValidationError
- Verify prompt construction includes JSON instructions

### Integration Tests (Real API)
```python
# Test each provider if API key available
@pytest.mark.parametrize("provider", ["openai", "anthropic", "deepseek", "qwen", "kimi", "glm"])
def test_provider_json_output(provider):
    if not os.getenv(f"{provider.upper()}_API_KEY"):
        pytest.skip(f"No API key for {provider}")
    
    parser = IntentParser(provider, load_config(provider))
    result = parser.parse("我强行砸开这个锁")
    
    assert result.action_type in ["brute_force", "unknown"]
    assert isinstance(result, ParsedIntent)
```

### Validation Tests
```python
# Test schema enforcement
def test_openai_strict_schema():
    # Should 100% match schema
    pass

def test_deepseek_fallback_on_invalid():
    # Should fallback to unknown intent
    pass
```

---

## Performance Considerations

### Latency
| Provider | Mode | Latency Notes |
|----------|------|---------------|
| OpenAI | Structured Outputs | +100-500ms first call (schema compilation) |
| Anthropic | Structured Outputs | Similar compilation overhead |
| DeepSeek | JSON mode | Standard latency, no compilation |
| Qwen/Kimi/GLM | JSON mode | Standard latency |

### Cost
- **Structured Outputs**: Same per-token rates as normal calls
- **JSON mode**: No surcharge
- **Recommendation**: Cost is identical, choose based on schema needs

### Reliability
| Provider | JSON Guarantee | Failure Handling |
|----------|---------------|------------------|
| OpenAI | 100% schema match | Check `refusal` field |
| Anthropic | 100% schema match | SDK auto-retries |
| DeepSeek | Valid JSON only | Check empty content + truncation |
| Qwen/Kimi/GLM | Valid JSON only | Check parse errors |

---

## Migration Path

### Phase 1: Foundation (T6 Implementation)
- Implement unified `IntentParser` with both modes
- Prioritize OpenAI/Anthropic for production use
- Test fallback path for other providers

### Phase 2: Validation
- Add provider-specific tests
- Measure parsing accuracy rates
- Tune prompts for each provider

### Phase 3: Optimization
- Add schema compilation caching (OpenAI/Anthropic)
- Implement retry logic for transient failures
- Monitor fallback rates per provider

---

## Key Learnings

1. **Schema enforcement varies**: Only OpenAI and Anthropic guarantee 100% schema adherence
2. **Prompt engineering matters**: For JSON mode providers, prompt quality affects output stability
3. **Fallback is essential**: All providers need graceful degradation
4. **SDK compatibility**: OpenAI SDK works for 5/6 providers via `base_url`
5. **Anthropic is special**: Requires separate SDK but offers excellent structured outputs
6. **Test before trusting**: Always validate schema even with "guaranteed" outputs

---

## References

- [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
- [Anthropic Structured Outputs](https://docs.anthropic.com/claude/docs/structured-outputs)
- [DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode/)
- [Qwen DashScope Compatibility](https://help.aliyun.com/zh/dashscope/developer-reference/compatibility-of-openai-with-dashscope)
- [Kimi (Moonshot) API](https://platform.moonshot.cn/docs/api/chat)
- [GLM (Zhipu) API](https://open.bigmodel.cn/dev/api/normal-model/glm-4)

---

**Next Steps**: T6 (AI service layer) implementation should use this document as the primary reference for provider-specific JSON mode handling.
