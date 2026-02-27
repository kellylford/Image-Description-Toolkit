"""Quick compatibility test for candidate MLX models.
Each model is tested in a fresh subprocess to avoid Metal memory collisions.
"""
import sys, os, time, subprocess, json

CANDIDATES = [
    'mlx-community/gemma-3-4b-it-qat-4bit',
    'mlx-community/Molmo-7B-D-0924-4bit',
    'mlx-community/SmolVLM-Instruct-4bit',
    'mlx-community/Qwen3-VL-4B-Instruct-3bit',
    'mlx-community/Llama-3.2-11B-Vision-Instruct-4bit',
]

if '--single' in sys.argv:
    # Subprocess mode: test exactly one model and emit JSON
    model = sys.argv[sys.argv.index('--single') + 1]
    sys.path.insert(0, 'imagedescriber')
    sys.path.insert(0, 'scripts')
    sys.path.insert(0, 'models')
    from imagedescriber.ai_providers import MLXProvider
    p = MLXProvider()
    t = time.time()
    result = p.describe_image('testimages/coffee_desk.jpg', 'Describe this image in detail.', model)
    elapsed = time.time() - t
    tps = p.last_usage.get('tokens_per_s', 0) if p.last_usage else 0
    ok = not result.startswith('Error')
    print(json.dumps({'ok': ok, 'elapsed': elapsed, 'tps': tps, 'text': result[:120]}))
    sys.exit(0)

# Orchestrator mode: spawn a subprocess per model
PYTHON = sys.executable
results = []

for model in CANDIDATES:
    print(f'\nTesting {model} ...', flush=True)
    t0 = time.time()
    try:
        proc = subprocess.run(
            [PYTHON, __file__, '--single', model],
            capture_output=True, text=True, timeout=600
        )
        elapsed = time.time() - t0
    except subprocess.TimeoutExpired:
        results.append((model, 'TIMEOUT', 600, 0, 'exceeded 600s timeout'))
        print(f'  TIMEOUT')
        continue

    if proc.returncode != 0:
        err = (proc.stderr or '').strip().splitlines()
        detail = next((l for l in reversed(err) if l.strip()), 'no output')[:150]
        results.append((model, 'FAIL', elapsed, 0, detail))
        print(f'  FAIL ({elapsed:.1f}s): {detail}')
        continue

    stdout = proc.stdout.strip().splitlines()
    json_line = next((l for l in reversed(stdout) if l.startswith('{')), None)
    if not json_line:
        results.append((model, 'FAIL', elapsed, 0, 'no JSON output'))
        print(f'  FAIL: no JSON output')
        continue

    data = json.loads(json_line)
    status = 'PASS' if data['ok'] else 'FAIL'
    tps = data['tps']
    detail = data['text']
    results.append((model, status, elapsed, tps, detail))
    print(f'  {status} ({data["elapsed"]:.1f}s, {tps:.1f} tok/s): {detail[:80]}')

print('\n\n=== SUMMARY ===')
for model, status, elapsed, tps, detail in results:
    short = model.split('/')[-1]
    print(f'  {status:9s} {short:<45s} {elapsed:6.1f}s  {tps:5.1f} tok/s')
