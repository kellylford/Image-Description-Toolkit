"""Runtime validation for MLXProvider — safe to delete after testing."""
import sys, time, os

sys.path.insert(0, os.path.dirname(__file__))

print("=== MLX Provider runtime validation ===")

# Test 1: import
from imagedescriber.ai_providers import (
    MLXProvider, get_available_providers, get_all_providers
)
print("PASS  import MLXProvider")

# Test 2: instantiation
p = MLXProvider()
print("PASS  MLXProvider()")

# Test 3: availability
avail = p.is_available()
print(f"PASS  is_available() = {avail}")

# Test 4: get_all_providers includes 'mlx'
all_p = get_all_providers()
assert 'mlx' in all_p, "mlx key missing from get_all_providers()"
print("PASS  get_all_providers() contains 'mlx'")

# Test 5: get_available_providers
avail_p = get_available_providers()
if avail:
    assert 'mlx' in avail_p, "mlx key missing from get_available_providers()"
    print("PASS  get_available_providers() contains 'mlx'")
else:
    print("SKIP  MLX not available on this platform")

# Test 6: model list
models = p.get_available_models()
print(f"PASS  get_available_models() → {models}")

# Test 7: reload_api_key no-op (must not raise)
p.reload_api_key()
p.reload_api_key(explicit_key="ignored")
print("PASS  reload_api_key() is a no-op")

if not avail:
    print("\nMLX not available — skipping inference tests")
    sys.exit(0)

# Test 8: actual inference
MODEL = "mlx-community/Qwen2-VL-2B-Instruct-4bit"
IMG   = "testimages/coffee_desk.jpg"
assert os.path.exists(IMG), f"Test image not found: {IMG}"

print(f"\nRunning inference: {MODEL} on {IMG}")
t0 = time.time()
desc = p.describe_image(image_path=IMG, prompt="Describe this image in one sentence.", model=MODEL)
elapsed = time.time() - t0

assert desc and not desc.startswith("Error"), f"Inference failed: {desc!r}"
print(f"PASS  describe_image() completed in {elapsed:.1f}s")
print(f"      → {desc[:150]}...")

# Test 9: last_usage populated
usage = p.get_last_token_usage()
assert usage is not None, "get_last_token_usage() returned None"
assert usage.get('completion_tokens', 0) > 0, f"completion_tokens zero: {usage}"
print(f"PASS  last_usage = {usage}")

# Test 10: second call re-uses loaded model (should be fast)
t0 = time.time()
desc2 = p.describe_image(image_path=IMG, prompt="What objects are visible?", model=MODEL)
elapsed2 = time.time() - t0
assert desc2 and not desc2.startswith("Error"), f"Second inference failed: {desc2!r}"
print(f"PASS  second describe_image() in {elapsed2:.1f}s (model reuse)")

print("\n=== ALL TESTS PASSED ===")
