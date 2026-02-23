"""
Test all Claude models listed in models/claude_models.py against the live Anthropic API.
Usage: python _test_claude_models.py
"""
import os, sys, json, time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load API key the same way ai_providers.py does
api_key = os.getenv('ANTHROPIC_API_KEY')

if not api_key:
    config_paths = [
        Path('scripts/image_describer_config.json'),
        Path.home() / 'Library/Application Support/IDT/image_describer_config.json',
    ]
    for p in config_paths:
        if p.exists():
            try:
                d = json.loads(p.read_text())
                keys = d.get('api_keys', {})
                api_key = keys.get('Claude') or keys.get('claude') or keys.get('CLAUDE')
                if api_key and api_key.strip():
                    api_key = api_key.strip()
                    print(f"Key loaded from: {p}")
                    break
            except Exception:
                continue

if not api_key:
    # Try claude.txt in common locations
    for p in [Path('claude.txt'), Path.home() / 'claude.txt']:
        if p.exists():
            api_key = p.read_text().strip()
            print(f"Key loaded from: {p}")
            break

if not api_key:
    print("ERROR: No Anthropic API key found.")
    print("Set ANTHROPIC_API_KEY environment variable, or put key in scripts/image_describer_config.json")
    sys.exit(1)

print(f"API key: sk-ant-...{api_key[-6:]}")

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic SDK not installed. Run: pip install anthropic")
    sys.exit(1)

client = anthropic.Anthropic(api_key=api_key)

# Load model list from canonical source
from models.claude_models import CLAUDE_MODELS
print(f"\nLoaded {len(CLAUDE_MODELS)} models from models/claude_models.py\n")

# Small test image (1x1 white JPEG, base64)
TEST_IMAGE_B64 = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/xAAUAQEAAAAAAAAAAAAAAAAAAAAA/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEQMRAD8AJQAB/9k="

TEST_PROMPT = "Say only: 'ok'"

print(f"{'Model':<45} {'Result':<10} {'Time':>6}  Notes")
print("-" * 75)

results = {"ok": [], "error": [], "not_found": []}

for model in CLAUDE_MODELS:
    t0 = time.time()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=20,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": TEST_IMAGE_B64
                    }},
                    {"type": "text", "text": TEST_PROMPT}
                ]
            }]
        )
        elapsed = time.time() - t0
        text = response.content[0].text.strip()[:40] if response.content else "(empty)"
        print(f"{model:<45} {'OK':<10} {elapsed:>5.1f}s  \"{text}\"")
        results["ok"].append(model)
    except anthropic.NotFoundError:
        elapsed = time.time() - t0
        print(f"{model:<45} {'404':<10} {elapsed:>5.1f}s  Model not found")
        results["not_found"].append(model)
    except anthropic.BadRequestError as e:
        elapsed = time.time() - t0
        msg = str(e)[:60]
        print(f"{model:<45} {'BAD REQ':<10} {elapsed:>5.1f}s  {msg}")
        results["error"].append(model)
    except anthropic.AuthenticationError:
        print(f"{model:<45} {'AUTH ERR':<10}  Invalid API key")
        sys.exit(1)
    except Exception as e:
        elapsed = time.time() - t0
        print(f"{model:<45} {'ERROR':<10} {elapsed:>5.1f}s  {str(e)[:50]}")
        results["error"].append(model)
    
    time.sleep(0.5)  # Rate limit buffer

print("\n" + "=" * 75)
print(f"WORKING ({len(results['ok'])}): {results['ok']}")
print(f"NOT FOUND ({len(results['not_found'])}): {results['not_found']}")
print(f"OTHER ERROR ({len(results['error'])}): {results['error']}")
