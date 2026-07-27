"""Same frames, same prompt, different model.

gemma4:31b-cloud called every frame of mcp_video-26116 an abstract, kaleidoscopic
image. The frames are ordinary concert photos. Re-describe them with
minicpm-v4.6 to establish whether that is the model or the pipeline.
"""
import base64, json, re, sys, time, urllib.request
from pathlib import Path

OLLAMA = "http://localhost:11434/api/generate"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "minicpm-v4.6:latest"
VIDEO = sys.argv[2] if len(sys.argv) > 2 else "mcp_video-26116_singular_display"

# Verbatim from scripts/image_describer_config.json, prompt_variations.accessibility
PROMPT = ("Describe this image for a screen reader user. Start with the main subject "
          "and overall scene. Then describe objects and people from left to right, "
          "including their colors, sizes, and positions relative to each other. "
          "Mention foreground, middle ground, and background elements. Use concrete, "
          "specific language without metaphor or visual-only references.")

BUNDLE = Path.home() / "Documents/idt/try3.idtw"
FRAMES = BUNDLE / "derived/frames" / VIDEO
DESCS = BUNDLE / "descriptions"

SIG = re.compile(r"\b(abstract|digitally (manipulated|generated|distorted)|"
                 r"kaleidoscop\w*|mirrored|fragmented)\b", re.I)


def old_description(frame_name):
    p = DESCS / f"{frame_name}.json"
    if not p.exists():
        return ""
    d = json.loads(p.read_text())
    ds = d.get("descriptions") or []
    return (ds[0].get("text") or "").strip() if ds else ""


def describe(img_path):
    payload = json.dumps({
        "model": MODEL,
        "prompt": PROMPT,
        "images": [base64.b64encode(img_path.read_bytes()).decode()],
        "stream": False,
    }).encode()
    req = urllib.request.Request(OLLAMA, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read()).get("response", "").strip()


frames = sorted(FRAMES.glob("*.jpg"))
print(f"model:  {MODEL}")
print(f"video:  {VIDEO}")
print(f"frames: {len(frames)}\n")

old_bad = new_bad = 0
for i, fp in enumerate(frames, 1):
    old = old_description(fp.name)
    t0 = time.time()
    try:
        new = describe(fp)
    except Exception as exc:
        print(f"[{i}/{len(frames)}] {fp.name}: ERROR {exc}")
        continue
    dt = time.time() - t0

    o_hit = bool(SIG.search(old.split("\n")[0])) if old else False
    n_hit = bool(SIG.search(new.split("\n")[0]))
    old_bad += o_hit
    new_bad += n_hit

    print(f"[{i}/{len(frames)}] {fp.name}  ({dt:.1f}s)")
    print(f"   gemma4 {'HALLUCINATED' if o_hit else 'ok':<13}: {old.splitlines()[0][:150] if old else '(none)'}")
    print(f"   minicpm{'HALLUCINATED' if n_hit else 'ok':>13}: {new.splitlines()[0][:150]}")
    print()

n = len(frames)
print("=" * 68)
print(f"gemma4:31b-cloud   hallucinated first line: {old_bad}/{n}")
print(f"{MODEL:<18} hallucinated first line: {new_bad}/{n}")
