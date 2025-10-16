# GitHub Issue: Provider-Specific Configuration Settings Enhancement

## Title
Enhancement: Add Provider-Specific Configuration Settings for OpenAI and Claude

## Labels
- enhancement
- configuration
- multi-provider support
- documentation

## Description

### Summary
Currently, the Image Description Toolkit uses Ollama-optimized settings for all AI providers. While this works (unsupported parameters are silently ignored), we should consider adding provider-specific configuration sections to properly support OpenAI and Claude with their native parameters.

### Current State

The toolkit currently uses a single `model_settings` configuration that is optimized for Ollama:

```json
{
  "model_settings": {
    "temperature": 0.1,
    "num_predict": 600,
    "top_k": 40,
    "top_p": 0.9,
    "repeat_penalty": 1.3
  }
}
```

**These settings are passed to ALL providers**, including OpenAI and Claude.

### The Problem

Different providers support different parameters:

#### **Ollama** (Current - Fully Supported)
- ✅ temperature (0.0-2.0)
- ✅ num_predict
- ✅ top_k
- ✅ top_p
- ✅ repeat_penalty

#### **OpenAI** (GPT-4o, GPT-5, etc.)
- ✅ temperature (0.0-2.0)
- ✅ max_tokens (similar to num_predict)
  - **Note:** GPT-5+ uses `max_completion_tokens` instead
- ✅ top_p
- ❌ top_k (NOT supported - silently ignored)
- ❌ repeat_penalty (NOT supported - uses `frequency_penalty` and `presence_penalty` instead)

#### **Claude** (Anthropic)
- ✅ temperature (**0.0-1.0 ONLY** - not 2.0! Will error if >1.0)
- ✅ max_tokens (REQUIRED parameter)
- ✅ top_p
- ✅ top_k
- ❌ repeat_penalty (NOT supported - silently ignored)

### Impact

**Current Behavior:**
1. Ollama settings work perfectly
2. OpenAI silently ignores `top_k` and `repeat_penalty` (no harm)
3. Claude ignores `repeat_penalty` (no harm)
4. **Potential issue:** If temperature is set > 1.0, Claude may error

**What We're Missing:**
- OpenAI's `frequency_penalty` and `presence_penalty` for controlling repetition
- Proper temperature range validation per provider
- Provider-specific optimizations

### Proposed Solution

Add provider-specific configuration sections to `image_describer_config.json`:

```json
{
  "provider_settings": {
    "ollama": {
      "temperature": 0.1,
      "num_predict": 600,
      "top_k": 40,
      "top_p": 0.9,
      "repeat_penalty": 1.3
    },
    "openai": {
      "temperature": 0.7,
      "max_tokens": 1000,
      "top_p": 0.9,
      "frequency_penalty": 0.0,
      "presence_penalty": 0.0
    },
    "claude": {
      "temperature": 0.7,
      "max_tokens": 1024,
      "top_p": 0.9,
      "top_k": 40
    }
  },
  
  // Legacy support - use if provider_settings not found
  "model_settings": {
    "temperature": 0.1,
    "num_predict": 600,
    "top_k": 40,
    "top_p": 0.9,
    "repeat_penalty": 1.3
  }
}
```

### Additional Universal Settings to Consider

Settings that would benefit ALL providers:

1. **timeout** (int) - Maximum seconds to wait for response
2. **retry_attempts** (int) - Number of retries on failure
3. **rate_limit_delay** (float) - Delay between requests (important for cloud APIs)
4. **image_detail** (OpenAI-specific) - "low", "high", or "auto" (affects cost and accuracy)

### Implementation Notes

**Code Changes Required:**
1. Update `scripts/image_describer.py` to read provider-specific settings
2. Update `imagedescriber/ai_providers.py` to use appropriate parameters per provider
3. Add validation for provider-specific ranges (e.g., Claude temperature ≤ 1.0)
4. Maintain backward compatibility with existing `model_settings`

**IDTConfigure Integration:**
- IDTConfigure GUI would show different settings based on selected provider
- Could add a provider selector to show provider-specific settings
- Alternative: Show all settings with notes about which providers support them

### Testing Requirements

1. Verify Ollama still works with new structure (backward compatible)
2. Test OpenAI with native parameters (frequency_penalty, presence_penalty)
3. Test Claude with temperature validation (≤ 1.0)
4. Confirm ignored parameters don't cause errors
5. Test fallback to legacy `model_settings` if `provider_settings` missing

### Related Work

**Preliminary work completed on `development` branch:**
- ✅ IDTConfigure GUI application created
- ✅ Manages all current configuration files
- ✅ 30+ settings across 6 categories
- ✅ Full keyboard accessibility
- ✅ Integrated with `idt configure` command

The IDTConfigure app could be enhanced to support provider-specific settings once implemented.

### Documentation Updates Needed

1. Update README with provider-specific parameter tables
2. Document OpenAI-specific parameters (frequency_penalty, presence_penalty)
3. Document Claude temperature limitation (≤ 1.0)
4. Add examples for each provider's optimal settings
5. Update IDTConfigure help text with provider notes

### Priority

**Recommended Priority: Medium**

**Rationale:**
- Current system works (parameters are silently ignored)
- No critical bugs or failures
- Enhancement would improve provider-specific tuning
- Good architectural improvement for multi-provider support

**Alternative Approach:**
- Document current behavior (Option 1: Keep it simple)
- Implement provider-specific sections later if users request it (Option 2: Wait for demand)
- Implement now for cleaner architecture (Option 3: Do it right)

### User Quotes

> "The best thing is after I received the email announcing this model, all I had to do was use the model name and the system just worked!" - User feedback on qwen3-vl:235b-cloud

This demonstrates that the current approach (provider-agnostic with Ollama abstraction) works well in practice.

### Questions for Discussion

1. Should we implement provider-specific settings now or document current behavior?
2. Do users actually need provider-specific tuning, or is current approach sufficient?
3. Should IDTConfigure show all settings or filter by selected provider?
4. How important is backward compatibility vs. clean architecture?

### References

- OpenAI API Documentation: https://platform.openai.com/docs/api-reference/chat/create
- Claude API Documentation: https://docs.anthropic.com/claude/reference/messages_post
- Ollama API Documentation: https://github.com/ollama/ollama/blob/main/docs/api.md

---

## Implementation Checklist

If this enhancement is approved:

- [ ] Design provider-specific config structure
- [ ] Update `image_describer_config.json` schema
- [ ] Modify `scripts/image_describer.py` to read provider settings
- [ ] Update `imagedescriber/ai_providers.py` parameter handling
- [ ] Add provider-specific validation
- [ ] Implement backward compatibility with legacy settings
- [ ] Update IDTConfigure to support provider-specific settings
- [ ] Add comprehensive tests for all three providers
- [ ] Update documentation
- [ ] Create migration guide for existing users

## Branch Information

- **Preliminary work:** `development` branch
- **IDTConfigure implementation:** Complete (commit a3b9bc2)
- **Testing branch:** `ImageDescriber` (v2.0.0-likely tag)
