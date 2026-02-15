# Model Parameter Constraints - Architecture Proposal

**Created**: February 15, 2026  
**Trigger**: gpt-5-nano temperature=0.2 → 400 error (model doesn't support custom temperature)  
**Status**: Proposal - Awaiting prioritization decision

---

## Problem Statement

We currently handle model-specific parameter requirements through **hardcoded logic** in `ai_providers.py`:

```python
# CURRENT APPROACH (BRITTLE):
# Line 640 - Comment-only documentation
# NOTE: gpt-5-nano does NOT support custom temperature (only default=1)

# Lines 659-666 - String matching
if model.startswith('gpt-5') or model.startswith('o1') or model.startswith('o3'):
    request_params["max_completion_tokens"] = 300
else:
    request_params["max_tokens"] = 300
```

**Failure Mode**: ChatGPT recommended `temperature=0.2` for gpt-5-nano, but the model rejects this with a 400 error. We had no way to know this constraint existed until runtime failure.

---

## Current Architecture Gaps

### What We Have
1. **Provider capabilities** (`models/provider_configs.py`):
   - ✅ `supports_prompts`, `supports_custom_prompts`
   - ❌ No API parameter constraints

2. **Model metadata** (`models/model_registry.py`):
   - ✅ Provider, description, size, cost
   - ❌ No parameter specifications

3. **Runtime logic** (`imagedescriber/ai_providers.py`):
   - ❌ Hardcoded parameter selection
   - ❌ String matching for model families
   - ❌ Comment-based documentation (not queryable)

### What Breaks
- ✅ New model names don't match string patterns (e.g., `gpt-5-nano` vs `gpt-5`)
- ✅ Provider-specific constraints undocumented (temperature=1 for gpt-5-nano)
- ✅ ChatGPT/docs give bad advice (recommended temperature=0.2)
- ✅ Runtime failures instead of validation

---

## Proposed Solution

### 1. Add Parameter Constraints to Model Metadata

**File**: `models/manage_models.py` - Extend `MODEL_METADATA`

```python
MODEL_METADATA = {
    "gpt-5-nano": {
        "provider": "openai",
        "description": "GPT-5 Nano - Ultra-low-cost OpenAI model",
        "cost": "$",
        "recommended": False,
        
        # NEW: API Parameter Constraints
        "api_parameters": {
            "max_tokens": {
                "param_name": "max_completion_tokens",  # GPT-5 uses new param name
                "default": 300,
                "min": 1,
                "max": 4096,
                "recommended": 300  # Based on Issue #91 testing
            },
            "temperature": {
                "supported": False,  # Model rejects custom temperature
                "fixed_value": 1,    # Always uses default=1
                "reason": "Nano-tier models have fixed temperature"
            },
            "top_p": {"supported": False},
            "frequency_penalty": {"supported": False},
            "presence_penalty": {"supported": False}
        }
    },
    
    "gpt-4o": {
        "provider": "openai",
        "description": "GPT-4o - Latest multimodal model",
        "cost": "$$$",
        
        "api_parameters": {
            "max_tokens": {
                "param_name": "max_tokens",  # GPT-4 uses old param name
                "default": 1000,
                "min": 1,
                "max": 16384
            },
            "temperature": {
                "supported": True,
                "default": 1.0,
                "min": 0.0,
                "max": 2.0,
                "recommended": 0.7
            },
            "top_p": {"supported": True, "default": 1.0},
            "frequency_penalty": {"supported": True, "default": 0.0},
            "presence_penalty": {"supported": True, "default": 0.0}
        }
    },
    
    "claude-sonnet-4": {
        "provider": "claude",
        "description": "Claude 4 Sonnet",
        "cost": "$$$",
        
        "api_parameters": {
            "max_tokens": {
                "param_name": "max_tokens",  # Anthropic uses max_tokens
                "default": 1024,
                "min": 1,
                "max": 4096
            },
            "temperature": {
                "supported": True,
                "default": 1.0,
                "min": 0.0,
                "max": 1.0  # Anthropic range is 0-1, not 0-2!
            }
        }
    }
}
```

### 2. Add Helper Functions to Model Registry

**File**: `models/model_registry.py` - New methods

```python
class ModelRegistry:
    
    def get_supported_parameters(self, model_name: str) -> Dict[str, Any]:
        """
        Get API parameters supported by a model.
        
        Returns:
            Dictionary of parameter specifications, or {} if none defined
        """
        metadata = self.get_model_info(model_name)
        if not metadata:
            return {}
        return metadata.get('api_parameters', {})
    
    def build_request_params(self, model_name: str, 
                           desired_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build valid API request parameters for a model.
        
        Filters out unsupported parameters and applies constraints.
        
        Args:
            model_name: Model to use
            desired_params: Requested parameters (may include unsupported ones)
            
        Returns:
            Validated parameters safe to pass to API
        """
        constraints = self.get_supported_parameters(model_name)
        if not constraints:
            # No constraints defined - pass through (backward compatible)
            return desired_params
        
        validated = {}
        
        for param_name, desired_value in desired_params.items():
            if param_name not in constraints:
                continue  # Skip undocumented parameters
            
            constraint = constraints[param_name]
            
            # Check if parameter is supported
            if not constraint.get('supported', True):
                # Log warning but don't fail
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Parameter '{param_name}' not supported by {model_name}, "
                    f"using fixed value: {constraint.get('fixed_value')}"
                )
                continue
            
            # Use correct parameter name (e.g., max_tokens vs max_completion_tokens)
            api_param_name = constraint.get('param_name', param_name)
            
            # Apply min/max constraints
            value = desired_value
            if 'min' in constraint and value < constraint['min']:
                value = constraint['min']
            if 'max' in constraint and value > constraint['max']:
                value = constraint['max']
            
            validated[api_param_name] = value
        
        return validated
    
    def get_default_parameters(self, model_name: str) -> Dict[str, Any]:
        """
        Get default/recommended parameters for a model.
        
        Returns:
            Dictionary of parameter values
        """
        constraints = self.get_supported_parameters(model_name)
        defaults = {}
        
        for param_name, spec in constraints.items():
            if not spec.get('supported', True):
                continue
            
            # Prefer 'recommended' over 'default'
            value = spec.get('recommended', spec.get('default'))
            if value is not None:
                api_name = spec.get('param_name', param_name)
                defaults[api_name] = value
        
        return defaults
```

### 3. Update Provider Code to Use Registry

**File**: `imagedescriber/ai_providers.py` - Replace hardcoded logic

```python
# BEFORE (HARDCODED):
request_params = {
    "model": model,
    "messages": messages
}
if model.startswith('gpt-5') or model.startswith('o1'):
    request_params["max_completion_tokens"] = 300
else:
    request_params["max_tokens"] = 300

# AFTER (DATA-DRIVEN):
from models.model_registry import get_registry

registry = get_registry()

# Start with desired parameters
desired_params = {
    "model": model,
    "messages": messages,
    "max_tokens": 300,  # Will be renamed to max_completion_tokens if needed
    "temperature": 0.7
}

# Let registry validate and transform
request_params = registry.build_request_params(model, desired_params)
```

---

## Benefits

### Immediate
1. ✅ **Prevent 400 errors** - Validate parameters before API call
2. ✅ **Document constraints** - Centralized source of truth
3. ✅ **Support new models** - Add metadata entry, code auto-adapts

### Long-term
4. ✅ **UI improvements** - Disable unsupported options in configure dialog
5. ✅ **Better defaults** - Use recommended values per model
6. ✅ **Testing** - Validate parameters in unit tests
7. ✅ **Documentation** - Auto-generate parameter docs from metadata

---

## Implementation Priority

### Option A: Fix Now (Before Testing)
- **Pros**: Prevents future parameter errors, cleaner architecture
- **Cons**: Delays current testing, requires careful migration
- **Effort**: 4-6 hours (metadata + registry + providers + testing)

### Option B: Fix Later (After Issue #91 Testing)
- **Pros**: Faster to current test, validates approach first
- **Cons**: Still have hardcoded logic for now
- **Effort**: Same 4-6 hours, but deferred

### Option C: Minimal Fix (Just gpt-5-nano)
- **Pros**: Solves immediate problem, 30 minutes
- **Cons**: Doesn't address root cause, still hardcoded
- **Effort**: 30 min - just remove temperature parameter for gpt-5-nano

---

## Recommendation

**Option B: Fix Later** ✅

**Reasoning**:
1. Current 400 error is already fixed (temperature removed)
2. Testing with max_tokens=300 is more important right now
3. Full architecture fix deserves dedicated time + testing
4. Include this in Issue #91 findings ("discovered model has undocumented constraints")

**Next Steps**:
1. ✅ Test current changes (max_tokens=300, PNG conversion, logging)
2. ✅ Submit OpenAI support ticket with temperature discovery
3. 🔲 After results, schedule architecture refactor as separate work
4. 🔲 Add to backlog: "Model Parameter Constraint System"

---

## Related Issues

- **Issue #91** - gpt-5-nano empty responses (exposed this need)
- **Temperature failure** - Discovered gpt-5-nano has fixed temperature=1
- **ChatGPT bad advice** - Support assistant recommended unsupported parameter

---

## Future Enhancements

Once base system exists, we can add:
1. **Parameter validation UI** - Gray out unsupported options
2. **Auto-optimization** - Use recommended values per model
3. **Cost estimation** - Calculate expected tokens × pricing
4. **Provider comparison** - Show which models support which features
5. **Migration assistant** - Warn when switching models with different constraints
