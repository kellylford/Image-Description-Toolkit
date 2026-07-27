"""Isolate the variable: same model, same image, context line on vs off.

The stored run used the EXIF-injected prompt; model_compare.py used the bare
prompt. That confounded model-vs-prompt. This holds the model fixed.
"""
import base64, json, re, sys, time, urllib.request
from pathlib import Path

OLLAMA = "http://localhost:11434/api/generate"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "gemma4:31b-cloud"
VIDEO = sys.argv[2] if len(sys.argv) > 2 else "mcp_video-26116_singular_display"
N = int(sys.argv[3]) if len(sys.argv) > 3 else 4

PROMPT = ("Describe this image for a screen reader user. Start with the main subject "
          "and overall scene. Then describe objects and people from left to right, "
          "including their colors, sizes, and positions relative to each other. "
          "Mention foreground, middle ground, and background elements. Use concrete, "
          "specific language without metaphor or visual-only references.")

# Exactly what workers_wx.py:819 builds, using the context seen in the run log
CTX = "Jul 3, 2026  Meta AI Ray-Ban Meta Smart Glasses"
WITH_CTX = f"Context: {CTX}\n\n{PROMPT}"

SIG = re.compile(r"\b(abstract|digitally (manipulated|generated|distorted)|"
                 r"kaleidoscop\w*|mirrored|fragmented)\b", re.I)
GLASSES = re.compile(r"\b(ray-?ban|smart glasses|eyeglass|spectacles|"
                     r"pair of .{0,20}glasses)\b", re.I)

FRAMES = Path.home() / "Documents/idt/try3.idtw/derived/frames" / VIDEO


def describe(img, prompt):
    payload = json.dumps({
        "model": MODEL, "prompt": prompt,
        "images": [base64.b64encode(img.read_bytes()).decode()],
        "stream": False,
    }).encode()
    req = urllib.request.Request(OLLAMA, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.loads(r.read()).get("response", "").strip()


frames = sorted(FRAMES.glob("*.jpg"))[:N]
print(f"model: {MODEL}\nframes: {len(frames)}\n", flush=True)

tally = {"with": 0, "without": 0, "glasses": 0}
for i, fp in enumerate(frames, 1):
    for label, prompt in (("WITHOUT context", PROMPT), ("WITH context", WITH_CTX)):
        t0 = time.time()
        try:
            out = describe(fp, prompt)
        except Exception as exc:
            print(f"[{i}] {label}: ERROR {exc}", flush=True)
            continue
        head = out.split("\n")[0]
        bad = bool(SIG.search(head))
        gl = bool(GLASSES.search(out))
        if bad:
            tally["with" if "WITH " in label else "without"] += 1
        if gl:
            tally["glasses"] += 1
        flag = "HALLUCINATED" if bad else "ok"
        gtag = "  [DESCRIBES GLASSES]" if gl else ""
        print(f"[{i}/{len(frames)}] {label:<16} {flag:<13} ({time.time()-t0:.0f}s){gtag}",
              flush=True)
        print(f"      {head[:170]}\n", flush=True)

n = len(frames)
print("=" * 62)
print(f"{MODEL}")
print(f"  hallucinated WITHOUT context line: {tally['without']}/{n}")
print(f"  hallucinated WITH    context line: {tally['with']}/{n}")
print(f"  mentioned glasses (either):        {tally['glasses']}/{n*2}")
