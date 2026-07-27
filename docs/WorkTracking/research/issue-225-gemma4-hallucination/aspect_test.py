"""Is it the flat region, or the aspect ratio?

D added a grey band AND made the image 1:3 tall. Those are confounded.

  E  clean frame stretched to 1:3, NO grey  -> tall aspect alone
  F  clean frame + grey band on LEFT/RIGHT  -> flat region without tall aspect
     (same flat-area fraction as D, landscape instead)
  G  clean frame downscaled so its subject  -> effective-resolution alone
     occupies as few pixels as a failing frame's subject
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
                 r"mirrored|fragmented|glitch|corrupted|distorted)\b", re.I)
FR = Path.home() / "Documents/idt/try3.idtw/derived/frames"
CLEAN = "video-27106_singular_display"
GREY = (196, 199, 203)


def send(img, tries=3):
    buf = io.BytesIO(); img.convert("RGB").save(buf, "JPEG", quality=90)
    body = json.dumps({"model": MODEL, "prompt": PROMPT,
                       "images": [base64.b64encode(buf.getvalue()).decode()],
                       "stream": False}).encode()
    last = None
    for a in range(tries):
        try:
            req = urllib.request.Request(OLLAMA, data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=900) as r:
                return json.loads(r.read()).get("response", "").strip()
        except Exception as e:
            last = e; time.sleep(5 * (a + 1))
    return f"ERROR {last}"


def run(label, img):
    t0 = time.time(); txt = send(img); head = txt.split("\n")[0]
    if txt.startswith("ERROR"):
        print(f"{label:<40} ERROR (excluded)", flush=True); return None
    bad = bool(SIG.search(head))
    print(f"{label:<40} {'HALLUCINATED' if bad else 'ok':<13} "
          f"{img.size[0]}x{img.size[1]}  ({time.time()-t0:.0f}s)", flush=True)
    print(f"    {head[:160]}\n", flush=True)
    return bad


frames = sorted((FR / CLEAN).glob("*.jpg"))[:3]
print(f"model: {MODEL}\n")
res = {"E": [], "F": [], "G": []}
for i, fp in enumerate(frames, 1):
    im = Image.open(fp).convert("RGB")
    w, h = im.size

    # E: tall aspect, no grey — stretch to the same 1:3 as condition D
    res["E"].append(run(f"E{i} stretched 1:3, NO grey", im.resize((w, int(w / 0.338)))))

    # F: same flat-area fraction as D, but added horizontally
    band = int(w * 55 / 45)
    f_img = Image.new("RGB", (w + band, h), GREY); f_img.paste(im, (band, 0))
    res["F"].append(run(f"F{i} grey band LEFT (landscape)", f_img))

    # G: effective resolution only — shrink subject to failing-frame scale
    res["G"].append(run(f"G{i} downscaled 45% (no pad, no stretch)",
                        im.resize((int(w * 0.45), int(h * 0.45)))))

print("=" * 66)
for k in ("E", "F", "G"):
    v = [x for x in res[k] if x is not None]
    print(f"  {k}: {sum(v)}/{len(v)} hallucinated")
print("""
E high -> tall aspect ratio alone is the trigger
F high -> a large flat region alone is the trigger (aspect irrelevant)
G high -> low effective resolution of the subject is the trigger""")
