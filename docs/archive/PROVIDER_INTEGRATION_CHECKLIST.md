# AI Provider Integration Checklist

**Use this checklist when adding a new AI provider to prevent missing integration points.**

This is the practical, step-by-step guide. For architecture analysis and future improvements, see [PROVIDER_INTEGRATION_ANALYSIS.md](PROVIDER_INTEGRATION_ANALYSIS.md).

---

## Overview

Adding a new provider requires changes in **6 files**. Follow this checklist in order, checking off each item as you complete it.

**Estimated Time:** 1-2 hours (including testing)  
**Last Updated:** October 5, 2025 (based on Claude integration)

---

## Pre-Flight Checklist

Before starting, gather this information:

- [ ] Provider name (internal key, e.g., `google`, `anthropic`, `mistral`)
- [ ] Provider display name (UI label, e.g., `Google AI`, `Anthropic`, `Mistral`)
- [ ] API endpoint/SDK information
- [ ] API key environment variable name (e.g., `GOOGLE_API_KEY`)
- [ ] List of models to support (especially vision-capable models)
- [ ] API key file location (e.g., `~/google.txt`)
- [ ] Does it support chat? (most do)
- [ ] Does it support custom prompts? (most do)
- [ ] Message format (OpenAI-compatible, Claude-style, or custom?)

---

## Step 1: Core Provider Implementation

**File:** `imagedescriber/ai_providers.py` (~3,700 lines)

### 1.1 Define Model List

**Location:** Near top of file (around lines 50-100, with other model lists)

```python
# Add your model list
DEV_GOOGLE_MODELS = [
    'gemini-2.0-flash',
    'gemini-1.5-pro',
    'gemini-1.5-flash',
    # ... add all vision-capable models
]
```

**Search for:** `DEV_CLAUDE_MODELS` or `DEV_OPENAI_MODELS` to find the right location

- [ ] Model list added with descriptive variable name
- [ ] Only vision-capable models included (if vision is needed)
- [ ] Models in priority order (best/recommended first)

---

### 1.2 Create Provider Class

**Location:** After existing provider classes (search for `class ClaudeProvider`)

**Template:**

```python
class GoogleProvider(AIProvider):
    """Google AI (Gemini) provider for image description"""
    
    def __init__(self):
        super().__init__("google")
        self.api_key = None
        self.models = DEV_GOOGLE_MODELS
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"  # Adjust as needed
    
    def _load_api_key_from_file(self, key_file: str) -> str:
        """Load API key from file, checking multiple locations"""
        # COPY THIS PATTERN from ClaudeProvider or OpenAIProvider
        # It checks multiple paths: absolute, relative, ~/onedrive, etc.
        logger.info(f"Loading API key from: {key_file}")
        
        # Try paths in order
        paths_to_try = [
            key_file,  # Exact path provided
            os.path.expanduser(key_file),  # Expand ~
            os.path.join(os.path.expanduser("~"), "onedrive", os.path.basename(key_file)),
            os.path.join(os.getcwd(), key_file),  # Relative to CWD
        ]
        
        for path in paths_to_try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    api_key = f.read().strip()
                    if api_key:
                        logger.info(f"Successfully loaded API key from: {path}")
                        return api_key
        
        raise FileNotFoundError(f"Could not find API key file: {key_file} (tried {len(paths_to_try)} locations)")
    
    def is_available(self) -> bool:
        """Check if Google AI is available"""
        # Check for SDK installation
        try:
            import google.generativeai  # Or whatever the SDK is
            return True
        except ImportError:
            logger.debug("Google AI SDK not installed")
            return False
    
    def get_models(self) -> List[str]:
        """Get available models"""
        return self.models
    
    def describe_image(
        self,
        image_path: str,
        prompt: str = None,
        model: str = None,
        custom_prompt: bool = False,
        api_key: str = None,
        api_key_file: str = None,
        **kwargs
    ) -> str:
        """Generate description using Google AI"""
        
        # 1. Handle API key
        if api_key:
            self.api_key = api_key
        elif api_key_file:
            self.api_key = self._load_api_key_from_file(api_key_file)
        elif not self.api_key:
            # Try environment variable
            self.api_key = os.getenv('GOOGLE_API_KEY')  # Adjust env var name
        
        if not self.api_key:
            raise ValueError("Google AI requires an API key")
        
        # 2. Set model
        if not model:
            model = self.models[0]  # Use first model as default
        
        # 3. Load and encode image
        # COPY THIS PATTERN from ClaudeProvider
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Determine image format
        image_ext = os.path.splitext(image_path)[1].lower()
        media_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        media_type = media_type_map.get(image_ext, 'image/jpeg')
        
        # 4. Build prompt
        if not prompt:
            prompt = "Describe this image in detail."
        
        # 5. Make API call
        try:
            import google.generativeai as genai  # Adjust import
            
            genai.configure(api_key=self.api_key)
            model_instance = genai.GenerativeModel(model)
            
            # Adjust API call based on SDK
            response = model_instance.generate_content([prompt, image_data])
            
            return response.text
            
        except Exception as e:
            logger.error(f"Google AI API error: {str(e)}")
            raise
```

**Checklist:**

- [ ] Class created inheriting from `AIProvider`
- [ ] `__init__()` sets name, models, any base URLs
- [ ] `_load_api_key_from_file()` checks multiple paths (copy from Claude/OpenAI)
- [ ] `is_available()` checks for SDK installation
- [ ] `get_models()` returns model list
- [ ] `describe_image()` implements full API integration
- [ ] Error handling included (try/except blocks)
- [ ] Logging statements added for debugging
- [ ] Image encoding handled correctly
- [ ] API key loading from file/env/parameter works

---

### 1.3 Create Global Instance

**Location:** Search for `_claude_provider = ClaudeProvider()` (around line 3637)

```python
# Add after other provider instances
_google_provider = GoogleProvider()
```

- [ ] Global instance created with underscore prefix
- [ ] Named consistently: `_{provider}_provider`

---

### 1.4 Register in Provider Discovery

**Location:** In `get_available_providers()` function (around lines 3656-3686)

```python
def get_available_providers() -> Dict[str, AIProvider]:
    """Get all available AI providers"""
    providers = {}
    
    # ... existing providers ...
    
    if _claude_provider.is_available():
        providers['claude'] = _claude_provider
    
    # ADD YOUR PROVIDER HERE (in alphabetical order is nice)
    if _google_provider.is_available():
        providers['google'] = _google_provider
    
    if _huggingface_provider.is_available():
        providers['huggingface'] = _huggingface_provider
    
    # ... rest of providers ...
```

- [ ] Provider added to `get_available_providers()` function
- [ ] Checks `is_available()` before adding
- [ ] Key matches provider name (e.g., `'google'`)

---

## Step 2: Configuration

**File:** `models/provider_configs.py` (~100 lines)

### 2.1 Add Provider Capabilities

**Location:** In `PROVIDER_CONFIGS` dictionary (around lines 34-43)

```python
PROVIDER_CONFIGS = {
    # ... existing providers ...
    
    'claude': ProviderConfig(
        supports_prompts=True,
        supported_prompt_styles=DEFAULT_PROMPT_STYLES,
        default_prompt_style='standard',
        requires_api_key=True
    ),
    
    # ADD YOUR PROVIDER HERE
    'google': ProviderConfig(
        supports_prompts=True,  # Does it support custom prompts?
        supported_prompt_styles=DEFAULT_PROMPT_STYLES,  # All styles or subset?
        default_prompt_style='standard',  # Which style is default?
        requires_api_key=True  # Does it need an API key?
    ),
}
```

- [ ] Entry added to `PROVIDER_CONFIGS` dictionary
- [ ] `supports_prompts` set correctly (usually True)
- [ ] `supported_prompt_styles` set (usually DEFAULT_PROMPT_STYLES)
- [ ] `default_prompt_style` set (usually 'standard')
- [ ] `requires_api_key` set correctly (True for cloud providers)

---

## Step 3: GUI Integration

**File:** `imagedescriber/imagedescriber.py` (~9,600 lines) ⚠️ **LARGEST FILE**

### 3.1 Import Provider

**Location:** Near top of file (around lines 65-68)

```python
from imagedescriber.ai_providers import (
    OllamaProvider,
    OpenAIProvider,
    ClaudeProvider,
    GoogleProvider,  # ADD THIS
    HuggingFaceProvider,
    # ... other imports ...
)
```

- [ ] Provider class imported (even if not used directly, needed for type hints)

---

### 3.2 Add to Display Names Dictionary ⚠️ **IMPORTANT**

**Location:** Search for `provider_display_names = {` (around line 2038)

```python
provider_display_names = {
    "ollama": "Ollama",
    "ollama_cloud": "Ollama Cloud",
    "openai": "OpenAI",
    "claude": "Claude",
    "google": "Google AI",  # ADD THIS - use friendly display name
    "onnx": "Enhanced Ollama (CPU + YOLO)",
    "huggingface": "HuggingFace",
    "copilot": "Copilot+ PC",
    "object_detection": "Object Detection",
    "grounding_dino": "Grounding DINO",
    "grounding_dino_hybrid": "Grounding DINO"
}
```

- [ ] Display name added (this is what users see in GUI)

---

### 3.3 Add to Image Tab Provider Dictionary ⚠️ **CRITICAL** (Bug Source #1)

**Location:** Search for `def populate_models(self):` in `ImageTab` class (around line 2173)

```python
def populate_models(self):
    """Populate the models combo box based on selected provider"""
    # ... code ...
    
    providers = {
        'ollama': _ollama_provider,
        'ollama_cloud': _ollama_cloud_provider,
        'openai': _openai_provider,
        'claude': _claude_provider,
        'google': _google_provider,  # ADD THIS
        'huggingface': _huggingface_provider,
        'onnx': _onnx_provider,
        'copilot': _copilot_provider,
        'object_detection': _object_detection_provider,
        'grounding_dino': _grounding_dino_provider,
        'grounding_dino_hybrid': _grounding_dino_hybrid_provider
    }
```

⚠️ **WARNING:** Forgetting this causes "No models available" in Image tab!

- [ ] Provider added to `populate_models()` dictionary in **ImageTab** class

---

### 3.4 Add to Chat Tab Provider Dictionary ⚠️ **CRITICAL** (Bug Source #2)

**Location:** Search for `def populate_providers(self):` in `ChatTab` class (around line 2452)

```python
def populate_providers(self):
    """Populate provider dropdown with chat-capable providers"""
    # ... code ...
    
    providers_with_chat = {
        'ollama': _ollama_provider,
        'ollama_cloud': _ollama_cloud_provider,
        'openai': _openai_provider,
        'claude': _claude_provider,
        'google': _google_provider,  # ADD THIS (if chat supported)
        'huggingface': _huggingface_provider
    }
```

- [ ] Provider added to `populate_providers()` dictionary in **ChatTab** class
- [ ] Only add if provider supports chat (most do)

---

### 3.5 Add to Chat Tab Models Dictionary ⚠️ **CRITICAL** (Bug Source #3)

**Location:** Search for `def populate_models(self):` in `ChatTab` class (around line 2480)

```python
def populate_models(self):
    """Populate model dropdown based on selected provider"""
    # ... code ...
    
    providers = {
        'ollama': _ollama_provider,
        'ollama_cloud': _ollama_cloud_provider,
        'openai': _openai_provider,
        'claude': _claude_provider,
        'google': _google_provider,  # ADD THIS (if chat supported)
        'huggingface': _huggingface_provider
    }
```

- [ ] Provider added to `populate_models()` dictionary in **ChatTab** class

---

### 3.6 Add to Regenerate Dialog Dictionary ⚠️ **CRITICAL** (Bug Source #4)

**Location:** Search for `class RegenerateDescriptionDialog` and find `providers = {` (around line 7461)

```python
class RegenerateDescriptionDialog(QDialog):
    def __init__(self, ...):
        # ... lots of code ...
        
        providers = {
            'ollama': _ollama_provider,
            'ollama_cloud': _ollama_cloud_provider,
            'openai': _openai_provider,
            'claude': _claude_provider,
            'google': _google_provider,  # ADD THIS
            'huggingface': _huggingface_provider,
            'onnx': _onnx_provider,
            'copilot': _copilot_provider,
            'object_detection': _object_detection_provider,
            'grounding_dino': _grounding_dino_provider,
            'grounding_dino_hybrid': _grounding_dino_hybrid_provider
        }
```

⚠️ **WARNING:** Forgetting this breaks the "Regenerate Description" dialog!

- [ ] Provider added to dictionary in **RegenerateDescriptionDialog** class

---

### 3.7 Add Chat Processing (If Provider Has Custom Format)

**Location:** In `ChatTab` class, search for `async def process_chat_message` (around line 1036)

**Only needed if:** Provider has unique message format (like Claude's different from OpenAI)

```python
async def process_chat_message(self, user_message, selected_image_path, provider, model):
    """Process chat message with appropriate provider"""
    # ... existing code ...
    
    if provider == 'ollama' or provider == 'ollama_cloud':
        await self.process_with_ollama_chat(...)
    elif provider == 'openai':
        await self.process_with_openai_chat(...)
    elif provider == 'claude':
        await self.process_with_claude_chat(...)
    elif provider == 'google':
        await self.process_with_google_chat(...)  # ADD IF NEEDED
    elif provider == 'huggingface':
        await self.process_with_huggingface_chat(...)
```

**If provider uses OpenAI-compatible format:** You might be able to reuse existing code!

- [ ] Chat processing branch added (if needed)
- [ ] Or verified that existing OpenAI code works (if compatible)

---

### 3.8 Create Chat Methods (If Custom Format Needed)

**Location:** In `ChatTab` class, after existing chat methods

**Template:**

```python
def build_google_messages(self):
    """Build message array for Google AI API"""
    # Build messages from self.chat_history
    # Format depends on provider's API requirements
    messages = []
    
    for role, content in self.chat_history:
        # Convert to provider's format
        messages.append({
            "role": "user" if role == "user" else "model",  # Google uses "model" not "assistant"
            "parts": [{"text": content}]  # Google's format
        })
    
    return messages

async def process_with_google_chat(self, user_message, selected_image_path, model):
    """Process chat with Google AI"""
    try:
        # 1. Build messages
        messages = self.build_google_messages()
        
        # 2. Add current message
        if selected_image_path:
            # Add image to message
            pass
        
        # 3. Make API call
        # 4. Stream response
        # 5. Update UI
        
    except Exception as e:
        logger.error(f"Google chat error: {str(e)}")
        self.append_message("assistant", f"Error: {str(e)}")
```

- [ ] `build_{provider}_messages()` created if custom format needed
- [ ] `process_with_{provider}_chat()` created if custom format needed
- [ ] Error handling included
- [ ] UI updates (status messages, streaming) working

---

### 3.9 Update Status Messages (Optional but Nice)

**Location:** Search for "Generating description with Claude" (around lines 2098, 2510)

```python
# In ImageTab - update_process_button_text() or similar
if provider == 'google':
    status_text = "Generating description with Google AI..."

# In ChatTab - status updates
if self.provider_combo.currentData() == 'google':
    self.status_label.setText("Processing with Google AI...")
```

- [ ] Status messages updated to mention provider name (optional)

---

## Step 4: CLI Workflow Integration

**File:** `scripts/workflow.py` (~1,200 lines)

### 4.1 Add to Provider Choices

**Location:** Search for `parser.add_argument('--provider'` (around line 1153)

```python
parser.add_argument(
    '--provider',
    choices=[
        'ollama',
        'openai',
        'claude',
        'google',  # ADD THIS
        'onnx',
        'huggingface',
        'copilot',
        'object_detection',
        'grounding_dino',
        'grounding_dino_hybrid'
    ],
    default='ollama',
    help='AI provider to use'
)
```

- [ ] Provider added to choices list (alphabetical order preferred)

---

### 4.2 Add Usage Examples

**Location:** In `parser.epilog` or near other examples (around lines 1099-1113)

```python
Examples:
    # ... existing examples ...
    
    # Claude (Anthropic)
    python workflow.py photos --provider claude --model claude-sonnet-4-5-20250929 --prompt-style narrative --api-key-file ~/claude.txt
    
    # Google AI (Gemini)
    python workflow.py photos --provider google --model gemini-2.0-flash --prompt-style narrative --api-key-file ~/google.txt
    
    # ... more examples ...
```

- [ ] Usage examples added to help text
- [ ] Shows provider name, recommended model, API key requirement

---

## Step 5: CLI Batch Processing Integration ⚠️ **CRITICAL**

**File:** `scripts/image_describer.py` (~1,400 lines)

**⚠️ WARNING:** This file was completely forgotten during Claude integration! Don't skip this!

### 5.1 Import Provider

**Location:** Near top of file (around line 46)

```python
from imagedescriber.ai_providers import (
    OllamaProvider,
    OpenAIProvider,
    ClaudeProvider,
    GoogleProvider,  # ADD THIS
    ONNXProvider,
    HuggingFaceProvider,
    CopilotProvider,
    ObjectDetectionProvider,
    GroundingDINOProvider,
    GroundingDINOHybridProvider,
    get_available_providers
)
```

- [ ] Provider class imported

---

### 5.2 Add to Provider Choices

**Location:** Search for `parser.add_argument("--provider"` (around line 1146)

```python
parser.add_argument(
    "--provider",
    choices=[
        "ollama",
        "openai",
        "claude",
        "google",  # ADD THIS
        "onnx",
        "huggingface",
        "copilot",
        "object_detection",
        "grounding_dino",
        "grounding_dino_hybrid"
    ],
    default="ollama",
    help="AI provider to use for image description"
)
```

- [ ] Provider added to choices list

---

### 5.3 Add Usage Examples

**Location:** In argument parser help text or epilog (around lines 1112-1114)

```python
Examples:
    # ... existing examples ...
    
    # Claude (Anthropic)
    python image_describer.py exportedphotos --provider claude --model claude-sonnet-4-5-20250929 --api-key-file ~/claude.txt
    
    # Google AI (Gemini)
    python image_describer.py exportedphotos --provider google --model gemini-2.0-flash --api-key-file ~/google.txt
    
    # ... more examples ...
```

- [ ] Usage examples added to help text

---

### 5.4 Add API Key Validation

**Location:** Search for "Provider 'openai' requires an API key" (around lines 1260-1270)

```python
# Load API key if needed
api_key = None
if args.api_key_file:
    # Load from file
    pass
elif args.api_key:
    api_key = args.api_key

# Check for required API keys
if not api_key and args.provider in ["openai", "huggingface", "claude", "google"]:  # ADD google
    # Check environment variables
    if args.provider == "openai":
        env_var = "OPENAI_API_KEY"
    elif args.provider == "huggingface":
        env_var = "HUGGINGFACE_TOKEN"
    elif args.provider == "claude":
        env_var = "ANTHROPIC_API_KEY"
    elif args.provider == "google":  # ADD THIS BLOCK
        env_var = "GOOGLE_API_KEY"
    
    api_key = os.getenv(env_var)
    
    if not api_key:
        logger.error(f"Provider '{args.provider}' requires an API key...")
        raise ValueError(f"Provider '{args.provider}' requires an API key")
```

- [ ] Provider added to API key requirement check
- [ ] Environment variable name set correctly
- [ ] Error message updated

---

### 5.5 Add Provider Initialization

**Location:** In `_initialize_provider()` method (around lines 175-185)

```python
def _initialize_provider(self):
    """Initialize the AI provider based on configuration"""
    # ... existing code ...
    
    if self.provider_name == "ollama":
        # ... ollama code ...
    elif self.provider_name == "openai":
        # ... openai code ...
    elif self.provider_name == "claude":
        # ... claude code ...
    elif self.provider_name == "google":  # ADD THIS BLOCK
        logger.info("Initializing Google AI provider...")
        if not self.api_key:
            raise ValueError("Google AI provider requires an API key. Use --api-key-file or set GOOGLE_API_KEY")
        provider = GoogleProvider()
        provider.api_key = self.api_key
        return provider
    elif self.provider_name == "huggingface":
        # ... huggingface code ...
```

- [ ] Provider initialization block added
- [ ] API key check included
- [ ] Provider instance created and API key set
- [ ] Descriptive error message if API key missing

---

### 5.6 Update Error Messages

**Location:** Search for error messages that list providers (around line 225)

```python
# Update any error messages that list supported providers
supported_providers = ["ollama", "openai", "claude", "google", "onnx", ...]  # ADD google
```

- [ ] Provider added to any error messages listing supported providers

---

## Step 6: Create Batch File (Optional)

**File:** `BatForScripts/run_google.bat` (NEW)

**Template:** Copy `BatForScripts/run_claude.bat` and modify

```batch
@echo off
REM Google AI (Gemini) Image Description Batch File
REM This script runs the workflow with Google AI provider

REM =============================================================================
REM CONFIGURATION
REM =============================================================================

REM Provider configuration
set PROVIDER=google
set MODEL=gemini-2.0-flash

REM ... rest of template ...
```

- [ ] Batch file created (optional but helpful)
- [ ] Default model set to recommended one
- [ ] All models listed in comments
- [ ] API key path updated

---

## Step 6.5: Update Model Management Scripts ⚠️ **IMPORTANT**

**⚠️ NOTE:** These scripts were forgotten during Claude integration! Don't skip them.

The toolkit includes two model management scripts in the `models/` directory that need to be updated:
- `models/check_models.py` - Check provider status and list models
- `models/manage_models.py` - Manage and install models

### 6.5.1 Update check_models.py

**File:** `models/check_models.py` (~465 lines)

#### Add Status Check Function

**Location:** After `check_openai_status()` function (around line 135)

**Template:**

```python
def check_google_status() -> Tuple[bool, List[str], str]:
    """Check Google AI provider status."""
    with SuppressOutput():
        from imagedescriber.ai_providers import GoogleProvider
    
    try:
        provider = GoogleProvider()
        if not provider.is_available():
            return False, [], "API key not configured (need google.txt or GOOGLE_API_KEY)"
        
        # Known Google vision models
        models = [
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash"
        ]
        return True, models, "API key configured"
    except Exception as e:
        return False, [], f"Error: {str(e)}"
```

- [ ] Status check function added
- [ ] Model list matches provider's models
- [ ] Environment variable name correct

#### Add to Providers Dictionary

**Location:** In `main()` function (around line 380)

```python
# Check all providers
providers = {
    'ollama': ('Ollama (Local Models)', check_ollama_status),
    'ollama-cloud': ('Ollama Cloud', check_ollama_cloud_status),
    'openai': ('OpenAI', check_openai_status),
    'claude': ('Claude (Anthropic)', check_claude_status),
    'google': ('Google AI (Gemini)', check_google_status),  # ADD THIS
    'huggingface': ('HuggingFace', check_huggingface_status),
    'onnx': ('ONNX / Enhanced YOLO', check_onnx_status),
    'copilot': ('Copilot+ PC (NPU)', check_copilot_status),
    'groundingdino': ('GroundingDINO (Object Detection)', check_groundingdino_status),
}
```

- [ ] Provider added to dictionary with display name

#### Add to Provider Choices

**Location:** In argument parser (around line 360)

```python
parser.add_argument(
    '--provider',
    choices=['ollama', 'ollama-cloud', 'openai', 'claude', 'google', 'huggingface', 'onnx', 'copilot', 'groundingdino'],
    help='Check only a specific provider'
)
```

- [ ] Provider added to choices list

#### Update Help Messages (Optional)

**Location:** API key error messages (around line 305)

```python
elif "api key" in message.lower():
    if "google" in message.lower() or "gemini" in provider_name.lower():
        print(f"  {Fore.YELLOW}->{Style.RESET_ALL} Add Google API key to 'google.txt' or GOOGLE_API_KEY env var")
    elif "anthropic" in message.lower() or "claude" in provider_name.lower():
        print(f"  {Fore.YELLOW}->{Style.RESET_ALL} Add Claude API key to 'claude.txt' or ANTHROPIC_API_KEY env var")
    else:
        print(f"  {Fore.YELLOW}->{Style.RESET_ALL} Add OpenAI API key to 'openai.txt' or OPENAI_API_KEY env var")
```

- [ ] Help message updated for provider's API key

**Testing check_models.py:**

```bash
# Test specific provider
python -m models.check_models --provider google

# Should show:
# Google AI (Gemini)
#   [OK] Status: API key configured
#   Models: 3 available
#     • gemini-2.0-flash
#     • gemini-1.5-pro
#     • gemini-1.5-flash
```

---

### 6.5.2 Update manage_models.py

**File:** `models/manage_models.py` (~860 lines)

#### Add Models to MODEL_METADATA

**Location:** After OpenAI models section (around line 165)

**Template:**

```python
# Google AI (Gemini) Models
"gemini-2.0-flash": {
    "provider": "google",
    "description": "Gemini 2.0 Flash - Latest, fastest",
    "size": "Cloud-based",
    "install_command": "Requires API key in google.txt or GOOGLE_API_KEY",
    "recommended": True,
    "cost": "$$",
    "tags": ["vision", "cloud", "fast", "recommended"]
},
"gemini-1.5-pro": {
    "provider": "google",
    "description": "Gemini 1.5 Pro - Highest quality",
    "size": "Cloud-based",
    "install_command": "Requires API key in google.txt or GOOGLE_API_KEY",
    "recommended": True,
    "cost": "$$$",
    "tags": ["vision", "cloud", "accurate", "recommended"]
},
"gemini-1.5-flash": {
    "provider": "google",
    "description": "Gemini 1.5 Flash - Good balance",
    "size": "Cloud-based",
    "install_command": "Requires API key in google.txt or GOOGLE_API_KEY",
    "recommended": False,
    "cost": "$$",
    "tags": ["vision", "cloud"]
},
```

**Fields to include:**
- `provider`: Provider key (e.g., "google")
- `description`: Clear model description
- `size`: "Cloud-based" for API models
- `install_command`: API key setup instructions
- `recommended`: True for best models
- `cost`: $ (cheap), $$ (moderate), $$$ (expensive)
- `tags`: Categorization tags

- [ ] All models added to MODEL_METADATA
- [ ] Recommended flag set correctly
- [ ] Cost indicators appropriate

#### Update Supported Providers Documentation

**Location:** Top of file docstring (around line 8)

```python
Supported Providers:
    - Ollama (local vision models)
    - OpenAI (cloud API models)
    - Claude (Anthropic cloud API models)
    - Google (Gemini cloud API models)  # ADD THIS
    - HuggingFace (transformers-based models)
    - YOLO (object detection)
    - GroundingDINO (text-prompted detection)
```

- [ ] Provider added to documentation

#### Add to Provider Choices

**Location:** In argument parser (around line 783)

```python
list_parser.add_argument(
    '--provider',
    choices=['ollama', 'openai', 'claude', 'google', 'huggingface', 'yolo', 'groundingdino'],
    help='Filter by provider'
)
```

- [ ] Provider added to choices list

#### Add Install Command Handling

**Location:** In install command section (around line 832)

```python
elif provider == 'openai':
    print(f"OpenAI models require an API key.")
    print(f"Add your API key to 'openai.txt' or set OPENAI_API_KEY environment variable")
elif provider == 'claude':
    print(f"Claude models require an API key.")
    print(f"Add your API key to 'claude.txt' or set ANTHROPIC_API_KEY environment variable")
elif provider == 'google':  # ADD THIS
    print(f"Google AI models require an API key.")
    print(f"Add your API key to 'google.txt' or set GOOGLE_API_KEY environment variable")
else:
    print(f"Installation for {provider} not supported via this tool")
```

- [ ] Install command handling added

**Testing manage_models.py:**

```bash
# List provider's models
python -m models.manage_models list --provider google

# Should show:
# GOOGLE
#   [AVAILABLE] gemini-2.0-flash [RECOMMENDED]
#     Gemini 2.0 Flash - Latest, fastest
#     Size: Cloud-based | Cost: $$
#     Install: Requires API key in google.txt or GOOGLE_API_KEY
```

---

### 6.5.3 Checklist Summary

**check_models.py changes:**
- [ ] Status check function created
- [ ] Added to providers dictionary
- [ ] Added to provider choices
- [ ] Help messages updated
- [ ] Tested with `--provider google`

**manage_models.py changes:**
- [ ] All models added to MODEL_METADATA
- [ ] Supported providers list updated
- [ ] Added to provider choices
- [ ] Install command handling added
- [ ] Tested with `list --provider google`

**Why This Matters:**
- Users can check if provider is configured: `checkmodels.bat google`
- Users can list available models: `python -m models.manage_models list --provider google`
- Provides installation instructions and model metadata
- Integrates with existing model management workflow

---

## Step 7: Testing ⚠️ **DO NOT SKIP**

### 7.1 GUI Testing

**Launch GUI:** `python imagedescriber/imagedescriber.py`

#### Image Tab
- [ ] Provider appears in provider dropdown
- [ ] Display name is correct (e.g., "Google AI")
- [ ] Selecting provider populates models dropdown ✅ **Critical Test**
- [ ] Models list is correct
- [ ] Can select an image
- [ ] Can select a prompt style
- [ ] Click "Generate Description" works
- [ ] Description appears in text field
- [ ] Status messages show provider name

#### Chat Tab
- [ ] Provider appears in provider dropdown
- [ ] Selecting provider populates models dropdown
- [ ] Can load an image
- [ ] Can send chat message
- [ ] Response appears in chat
- [ ] Follow-up messages work
- [ ] Chat history maintained

#### Regenerate Dialog (from Image Tab)
- [ ] Generate description for an image
- [ ] Click "Regenerate" button
- [ ] Dialog opens with providers list
- [ ] New provider appears in list ✅ **Critical Test**
- [ ] Can select provider and model
- [ ] Regenerate works

**If any of these fail:** Check the 4 provider dictionaries in imagedescriber.py!

---

### 7.2 CLI Workflow Testing

**Test Command:**
```bash
python workflow.py "test_images_folder" \
    --provider google \
    --model gemini-2.0-flash \
    --prompt-style narrative \
    --api-key-file ~/google.txt
```

- [ ] Command runs without "invalid choice" error
- [ ] API key loads from file
- [ ] Images processed
- [ ] Descriptions generated
- [ ] HTML report created
- [ ] Check descriptions for quality

---

### 7.3 CLI Batch Processing Testing

**Test Command:**
```bash
python scripts/image_describer.py test_images_folder \
    --provider google \
    --model gemini-2.0-flash \
    --api-key-file ~/google.txt \
    --output-dir test_output
```

- [ ] Command runs without "invalid choice" error ✅ **Critical Test**
- [ ] Provider initializes correctly
- [ ] API key loads from file
- [ ] Images processed
- [ ] Descriptions saved to output file
- [ ] No crashes or errors

**If this fails with "invalid choice: google":**
You forgot to add provider to `scripts/image_describer.py` (Step 5)!

---

### 7.4 Workflow Resume Testing

**Test Resume:**
```bash
# First, interrupt a workflow (Ctrl+C after a few images)
python workflow.py test_images --provider google --model gemini-2.0-flash --api-key-file ~/google.txt

# Then resume it
python workflow.py --resume <workflow_dir> --api-key-file ~/google.txt
```

- [ ] Resume finds the workflow
- [ ] API key required message shown (if you forget --api-key-file)
- [ ] Resume completes successfully with API key

---

## Step 8: Documentation

### 8.1 Create Setup Guide

**File:** `docs/GOOGLE_SETUP_GUIDE.md` (NEW)

**Template:** Copy `docs/CLAUDE_SETUP_GUIDE.md` and modify

Sections to include:
- Prerequisites
- API key setup
- Installation (SDK installation if needed)
- Configuration
- Available models
- Usage examples (GUI, CLI, workflow)
- Troubleshooting

- [ ] Setup guide created
- [ ] API key instructions clear
- [ ] All usage examples tested

---

### 8.2 Update Model Selection Guide

**File:** `docs/MODEL_SELECTION_GUIDE.md`

Add section for Google models:

```markdown
### Google AI (Gemini)

**Best For:** [Fast processing / Advanced reasoning / etc.]

**Models:**
- `gemini-2.0-flash` - Latest and fastest [recommended]
- `gemini-1.5-pro` - Highest quality
- `gemini-1.5-flash` - Good balance

**Pricing:** [link to Google pricing]

**Setup:** See [GOOGLE_SETUP_GUIDE.md](GOOGLE_SETUP_GUIDE.md)
```

- [ ] Provider section added to model selection guide
- [ ] Models documented
- [ ] Recommendations provided

---

### 8.3 Update Main README

**File:** `docs/README.md`

Add link to setup guide:

```markdown
### AI Provider Guides
- [OpenAI Setup Guide](OPENAI_SETUP_GUIDE.md)
- [Claude Setup Guide](CLAUDE_SETUP_GUIDE.md)
- [Google AI Setup Guide](GOOGLE_SETUP_GUIDE.md)
```

- [ ] Link added to main README
- [ ] Alphabetical order maintained

---

### 8.4 Create Resume Batch File (Optional)

**File:** `resume_google_workflow.bat` (root directory)

```batch
@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe workflow.py --resume "<workflow_dir>" --api-key-file "%USERPROFILE%\onedrive\google.txt"
pause
```

- [ ] Resume batch file created (optional)

---

## Step 9: Final Verification

### 9.1 Code Review Checklist

**Search for provider name in each file:**

```bash
# From repository root:
grep -n "claude" imagedescriber/ai_providers.py | wc -l
grep -n "claude" imagedescriber/imagedescriber.py | wc -l
grep -n "claude" models/provider_configs.py | wc -l
grep -n "claude" scripts/workflow.py | wc -l
grep -n "claude" scripts/image_describer.py | wc -l
grep -n "claude" models/check_models.py | wc -l
grep -n "claude" models/manage_models.py | wc -l
```

Now search for your provider and ensure similar number of matches.

- [ ] Provider name appears in all 7 core files
- [ ] No "TODO" or "FIXME" comments left
- [ ] No copy-paste errors (e.g., "Claude" in Google code)

---

### 9.2 Integration Points Count

Based on Claude integration, you should have touched these locations:

| File | Expected Changes | What to Check |
|------|-----------------|---------------|
| `ai_providers.py` | 4 locations | Model list, class, instance, registration |
| `provider_configs.py` | 1 location | Capabilities entry |
| `imagedescriber.py` | 6-10 locations | Import, display name, 4 dictionaries, chat (if needed) |
| `workflow.py` | 2 locations | Choices, examples |
| `image_describer.py` | 5 locations | Import, choices, examples, API key, initialization |
| `models/check_models.py` | 4 locations | Status function, provider dict, choices, help |
| `models/manage_models.py` | 4+ locations | Model metadata, docs, choices, install handling |

- [ ] All expected changes made
- [ ] No locations missed

---

### 9.3 Common Mistakes Check

**Did you remember all 4 GUI dictionaries?** ⚠️ **Most common mistake!**

1. Line ~2038: `provider_display_names`
2. Line ~2173: ImageTab `populate_models()` 
3. Line ~2452: ChatTab `populate_providers()`
4. Line ~2480: ChatTab `populate_models()`
5. Line ~7461: RegenerateDescriptionDialog

- [ ] All 5 locations updated (1 display names + 4 provider dictionaries)

**Did you remember image_describer.py?** ⚠️ **Second most common mistake!**

- [ ] `scripts/image_describer.py` fully integrated (5 changes)

**Did you test in GUI?** ⚠️ **Catches most bugs!**

- [ ] Tested in Image tab (models populate)
- [ ] Tested in Chat tab (provider works)
- [ ] Tested Regenerate dialog (provider appears)

---

## Step 10: Commit & Document

### 10.1 Git Commit

```bash
git add .
git commit -m "Add Google AI (Gemini) provider integration

- Implement GoogleProvider class with Gemini API
- Add 3 Gemini models (2.0-flash, 1.5-pro, 1.5-flash)
- Integrate into GUI (Image tab, Chat tab, Regenerate dialog)
- Add CLI support (workflow.py and image_describer.py)
- Create setup guide and update documentation
- Test all integration points (GUI, CLI, batch processing)"
```

- [ ] Changes committed with descriptive message

---

### 10.2 Update Integration Analysis

**File:** `docs/PROVIDER_INTEGRATION_ANALYSIS.md`

Add note that Google was integrated following this checklist.

- [ ] Analysis document updated (optional)

---

## Troubleshooting

### "No models available" in GUI Image tab
**Cause:** Forgot to add provider to dictionary at line ~2173  
**Fix:** Add provider to `populate_models()` in ImageTab class

### "No models available" in GUI Chat tab
**Cause:** Forgot to add provider to dictionary at line ~2480  
**Fix:** Add provider to `populate_models()` in ChatTab class

### Provider doesn't appear in Regenerate dialog
**Cause:** Forgot to add provider to dictionary at line ~7461  
**Fix:** Add provider to RegenerateDescriptionDialog dictionary

### "invalid choice: 'google'" in workflow.py
**Cause:** Forgot to add provider to choices list  
**Fix:** Add to `--provider` choices in workflow.py

### "invalid choice: 'google'" in image_describer.py
**Cause:** Forgot to add provider to choices list  
**Fix:** Add to `--provider` choices in image_describer.py

### "Provider 'google' requires an API key"
**Cause:** API key not provided or not loaded correctly  
**Fix:** Check `_load_api_key_from_file()` implementation, verify file paths

### "invalid choice: 'google'" in check_models.py or manage_models.py
**Cause:** Forgot to add provider to model management scripts  
**Fix:** Add to provider choices in both `models/check_models.py` and `models/manage_models.py`

### Provider doesn't show in checkmodels.bat output
**Cause:** Forgot to add provider to `models/check_models.py`  
**Fix:** Add status check function and provider dictionary entry

### ImportError or ModuleNotFoundError
**Cause:** Provider SDK not installed  
**Fix:** Install required package: `pip install google-generativeai` (or whatever)

### API returns errors
**Cause:** Incorrect API call format, wrong endpoint, bad API key  
**Fix:** Check provider documentation, verify API key is valid, check request format

---

## Time Estimate

| Phase | Time | Notes |
|-------|------|-------|
| Core Implementation (Step 1) | 30-45 min | Longest step, API integration |
| Configuration (Step 2) | 2 min | Quick |
| GUI Integration (Step 3) | 10-15 min | Tedious, easy to miss locations |
| Workflow CLI (Step 4) | 5 min | Simple |
| Batch CLI (Step 5) | 10 min | Often forgotten! |
| Batch File (Step 6) | 5 min | Optional |
| **Model Scripts (Step 6.5)** | 10-15 min | **Easy to forget!** |
| **Testing (Step 7)** | 15-20 min | **Don't skip!** |
| Documentation (Step 8) | 20-30 min | Important for users |
| Verification (Step 9) | 10 min | Final checks |

**Total:** ~105-135 minutes (with testing and documentation)  
**Without documentation:** ~75 minutes  
**Absolute minimum (no testing):** ~50 minutes (⚠️ not recommended)

---

## Summary

Adding a provider touches **8 files** with **28+ integration points**:

1. ✅ **ai_providers.py** - Core implementation (4 points)
2. ✅ **provider_configs.py** - Capabilities (1 point)
3. ✅ **imagedescriber.py** - GUI integration (6-10 points) ⚠️ **Most error-prone**
4. ✅ **workflow.py** - CLI workflow (2 points)
5. ✅ **image_describer.py** - CLI batch (5 points) ⚠️ **Often forgotten**
6. ✅ **models/check_models.py** - Model status checking (4 points) ⚠️ **Often forgotten**
7. ✅ **models/manage_models.py** - Model management (4+ points) ⚠️ **Often forgotten**
8. ✅ **Documentation** - Setup guides and examples (3+ files)

**Most Common Mistakes:**
1. ❌ Forgetting one of the 4 provider dictionaries in imagedescriber.py
2. ❌ Forgetting scripts/image_describer.py entirely
3. ❌ Forgetting model management scripts (check_models.py, manage_models.py)
4. ❌ Not testing thoroughly (especially GUI)

**Success Criteria:**
- ✅ Works in GUI (all 3 tabs)
- ✅ Works in workflow.py
- ✅ Works in image_describer.py
- ✅ Shows in check_models.py output
- ✅ Shows in manage_models.py list
- ✅ API key loading works
- ✅ All integration points updated

**Good luck adding Google! 🚀**

---

**Version:** 1.1  
**Last Updated:** October 5, 2025 (Updated to include model management scripts)  
**Based On:** Claude provider integration experience (including lessons learned)  
**Next Review:** After adding Google provider (to refine checklist)
