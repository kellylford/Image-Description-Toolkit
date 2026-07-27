"""Causal test: is the large flat sky region what breaks gemma4?

Four conditions, one vision-capable model (gemma4:31b-cloud):

  A  failing frame, unmodified          -> expect hallucination (baseline)
  B  failing frame, sky cropped off     -> if correct, sky is the trigger
  C  clean frame, unmodified            -> expect correct (baseline)
  D  clean frame, grey sky band added   -> if hallucinates, sky is sufficient

B and D together establish direction, not just correlation.
"""
import base64, io, json, re, sys, time, urllib.request
from pathlib import Path
from PIL import Image

OLLAMA = "http://localhost:11434/api/generate"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "gemma4:cloud"
PROMPT = ("Describe this image for a screen reader user. Start with the main subject "
          "and overall scene. Then describe objects and people from left to right, "
          "including their colors, sizes, and positions relative to each other. "
          "Mention foreground, middle ground, and background elements. Use concrete, "
          "specific language without metaphor or visual-only references.")

SIG = re.compile(r"\b(abstract|digitally (manipulated|generated|distorted)|kaleidoscop\w*|"
                 r"mirrored|fragmented|glitch|corrupted)\b", re.I)

FR = Path.home() / "Documents/idt/try3.idtw/derived/frames"
FAILING = "od_video-26206_singular_display"     # 21/21 hallucinated
CLEAN = "video-27106_singular_display"          # 0/37 hallucinated


def send(img: Image.Image, tries=3):
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=90)
    b64 = base64.b64encode(buf.getvalue()).decode()
    body = json.dumps({"model": MODEL, "prompt": PROMPT,
                       "images": [b64], "stream": False}).encode()
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(OLLAMA, data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=900) as r:
                d = json.loads(r.read())
            return d.get("response", "").strip(), d.get("prompt_eval_count")
        except Exception as exc:
            last = exc
            time.sleep(5 * (attempt + 1))
    return f"ERROR {last}", None


def crop_sky(img):
    """Keep the bottom 45% — removes the flat overcast region."""
    w, h = img.size
    return img.crop((0, int(h * 0.55), w, h))


def add_sky(img):
    """Prepend a flat grey band equal to 55% of the final height."""
    w, h = img.size
    band = int(h * 55 / 45)
    out = Image.new("RGB", (w, h + band), (196, 199, 203))
    out.paste(img, (0, band))
    return out


def run(label, img, expect):
    t0 = time.time()
    txt, ptok = send(img)
    head = txt.split("\n")[0]
    if txt.startswith("ERROR"):
        print(f"{label:<34} ERROR (excluded)\n    {head[:120]}\n", flush=True)
        return None
    bad = bool(SIG.search(head))
    verdict = "HALLUCINATED" if bad else "ok"
    mark = "  <-- FLIPPED" if (bad and expect == "ok") or (not bad and expect == "bad") else ""
    print(f"{label:<34} {verdict:<13} {img.size[0]}x{img.size[1]}  "
          f"ptok={ptok}  ({time.time()-t0:.0f}s){mark}", flush=True)
    print(f"    {head[:165]}\n", flush=True)
    return bad


fail_frames = sorted((FR / FAILING).glob("*.jpg"))[:3]
clean_frames = sorted((FR / CLEAN).glob("*.jpg"))[:3]

print(f"model: {MODEL}\n")
tally = {}
for i, fp in enumerate(fail_frames, 1):
    im = Image.open(fp)
    tally[f"A{i}"] = run(f"A{i} failing frame, unmodified", im, "bad")
    tally[f"B{i}"] = run(f"B{i} failing frame, SKY CROPPED", crop_sky(im), "bad")

for i, fp in enumerate(clean_frames, 1):
    im = Image.open(fp)
    tally[f"C{i}"] = run(f"C{i} clean frame, unmodified", im, "ok")
    tally[f"D{i}"] = run(f"D{i} clean frame, SKY ADDED", add_sky(im), "ok")

print("=" * 66)
for k in ("A", "B", "C", "D"):
    vals = [v for n, v in tally.items() if n.startswith(k) and v is not None]
    print(f"  {k}: {sum(vals)}/{len(vals)} hallucinated")
print("\nA high + B low  -> the flat sky region causes it")
print("C low  + D high -> adding sky is sufficient to cause it")
