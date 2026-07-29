# Echo Demo - Issues

## Problems Encountered

### CRITICAL: action.py Duplicate JudgmentResult
- In `backend/app/models/action.py`, `JudgmentResult` is defined TWICE:
  1. Line 21: `class JudgmentResult(str, Enum)` with values success/fail/forced_fail/partial/god_intervention
  2. Line 135: `class JudgmentResult(BaseModel)` with result/damage/state_changes fields
- The BaseModel definition shadows the Enum, making `result: JudgmentResult` on line 151 reference the model itself (circular)
- **FIX**: Rename Enum to `JudgmentOutcome` (or similar), keep BaseModel as `JudgmentResult`

### ActionType Values Mismatch
- Plan specifies: brute_force/stealth/read_memory/negotiate/probe/god_provoke/investigate
- Current code has: move/interact/attack/examine/speak/wait/use_item/flee
- **FIX**: Must align ActionType enum with plan values (T6 parser depends on this whitelist)

### .env.example Provider Names Mismatch
- Plan specifies 6 providers: OpenAI/Anthropic/DeepSeek/Qwen/Kimi/GLM
- Current has: OpenAI/Anthropic/Azure/Mistral/Groq/OpenRouter
- **FIX**: Replace with plan-specified providers

### Frontend Missing Tailwind
- Vite default template only, no Tailwind CSS configured
- Missing: tailwind.config.js, index.css CRT effects, vite proxy /api

## Blockers

## Workarounds

## Pending Resolution
