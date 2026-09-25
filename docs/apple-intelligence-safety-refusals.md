# Apple Intelligence: when it refuses to describe an image

**Measured 9/24/2026 on macOS 27.2 (`26B5086k`), Apple Silicon, model `system`.**

Apple's on-device model sometimes declines an image. This note records what that looks
like, what actually causes it, and how to reproduce it yourself — because the first
instinct (retry, or assume something is broken) is wrong in both directions.

---

## What it looks like

```
Apple Intelligence declined to describe this image: its safety guardrails were
triggered. Retrying will not help, but a different prompt style often does --
try 'accessibility' or 'detailed'.
```

Underneath, the server returns this:

```
HTTP 500 {"error":{"message":"The model's safety guardrails were triggered.",
                   "code":"500","type":"server_error"}}
```

Two things about that raw form are misleading, which is why IDT rewrites it:

- **It is an HTTP 500**, the same status a genuine server fault uses. Every text-based
  error classifier in this codebase reads a 500 as transient and worth retrying. This is
  not transient.
- **`"type":"server_error"`** says nothing broke on the server. The model declined.

## What it costs

Nothing noticeable. A refusal comes back in **0.3 seconds**, against 4–6 seconds for a
real description, so it is an input-side check that fires before any generation. In a
520-image batch, one refusal cost less than a second of the 58-minute run.

---

## What actually triggers it

The example below is a photo of two taxidermy mounts — a moose and an elk on a wall,
with a window, a fire-extinguisher cabinet, and the antlers throwing shadows.

**The photo:** [`~/Documents/September/Alaska and More - 239 of 402.jpeg`](file:///Users/kellyford/Documents/September/Alaska%20and%20More%20-%20239%20of%20402.jpeg)
*(a personal photo on Kelly's machine, deliberately not committed to this repository)*

### It is the animals, established by cropping

Same prompt (`concise`) each time, three runs per crop:

| What was sent | Result |
|---|---|
| Whole image | refused ×3 |
| Top half — both mounted heads | refused ×3 |
| Bottom half — window, wall, extinguisher | **described ×3** |
| Left mount alone (moose) | refused ×3 |
| Right mount alone (elk) | refused ×3 |
| Centre of top half — the antlers' *shadows*, no animal | **described ×3** |

Either mount alone is enough. Neither the room nor the shadows of the very same antlers
trip anything — the shadow control is the useful one, because the shape is right there
on the wall and the model describes it happily.

The reading is a hunting-trophy / animal-death judgment. **This is inference:** Apple
returns no category and no score, only the sentence above. The crops establish *what* in
the frame is responsible; they cannot establish *why* Apple classes it that way.

### It also depends on the prompt — unpredictably

The same image, same day, same machine:

| Prompt sent | Result |
|---|---|
| `narrative` (327 chars) | described 4/4 |
| `narrative` truncated to 200 chars or less | refused |
| `narrative` truncated to 240 chars or more | described |
| `narrative` with a leading **space** | described |
| `narrative` with a leading **newline** | refused |
| `narrative` with trailing spaces or trailing text | described (trailing never mattered) |
| `narrative` with the metadata prefix `"…: Sep 7, 2026"` | refused |
| `narrative` with the metadata prefix `"…: Seattle, Washington  Sep 7, 2026"` | **described** |
| `concise` (107 chars) | refused |
| `"Describe this image."` / `"Write alt text for this image."` / `"Describe this image for a screen reader user."` | all refused |

**The decision does not track meaning.** A prompt that works stops working if you put a
newline in front of it, while a space is fine. Trailing text never changes anything, so
only the start of the prompt seems to matter — yet `"Describe this image."` is refused
while a 327-character prompt that *begins with those exact words* is described. One
metadata prefix flips it and a longer, more specific one does not.

What it is *not*: random. The same exact string gives the same answer every time — 10/10
and 4/4 in repeated runs, and identical across three freshly started servers.

**Different people hit different styles.** On this photo, one run refused `narrative` and
`detailed` while `accessibility` and `artistic` worked; another machine refused `concise`
while `narrative`, `detailed`, `accessibility` and `artistic` all worked. So do not trust
any list of "safe" styles, including the examples above — try a few.

### All twelve built-in prompts, one image

Run through the built CLI with `BuildAndRelease/MacBuilds/test_prompts_apple.command`,
which does exactly this sweep and prints the table:

| chars | prompt | result |
|---:|---|---|
| 66 | `simple` | **refused** |
| 107 | `concise` | **refused** |
| 115 | `aialttext` | **refused** |
| 271 | `mood` | **refused** |
| 305 | `comparison` | described |
| 319 | `functional` | described |
| 325 | `artistic` | described |
| 327 | `narrative` | described |
| 350 | `accessibility` | described |
| 389 | `colorful` | described |
| 449 | `detailed` | described |
| 638 | `technical` | described |

Eight described, four refused, and **the split is exactly by length**: everything at or
below 271 characters was refused, everything at or above 305 was described. Truncating a
working prompt reproduces it — `narrative` cut to 200 characters is refused, cut to 240 it
is described — so the effect is the prompt's size, not its wording.

That is not a complete theory: `mood` at 271 characters is refused while a 240-character
truncation of `narrative` is described, so content still matters at the margin. But length
is the one variable that separates this table cleanly.

**The accessibility-shaped prompts are the short ones.** `aialttext` is the prompt written
specifically for alt text, and `simple` is the one for a plain short description. Both are
refused on this image, while the verbose styles are not. Anyone using the Apple provider
for alt text is therefore more likely to meet a refusal than someone asking for a
paragraph of art criticism — which is the opposite of useful.

### Apple's own accessibility feature describes it fine

VoiceOver's image description produced a full, accurate description of this same photo —
both mounts, the window and blinds, the fire extinguisher cabinet, even the illegible
labels. Same vendor, same device, no refusal. Whatever guardrail configuration the
Foundation Models endpoint applies is evidently not the one behind VoiceOver.

A practical consequence: **EXIF metadata being enabled made the difference** on this
image, because the pipeline prepends that `Capture metadata…` line to the prompt. Turning
metadata off would have described it — at the cost of losing date and camera context on
every other image, which is not a trade worth making for one photo in 520.

### Retrying does not help; a different prompt does

Refusal is stable for an exact prompt string: **0 successes in 11 retries** with an
unchanged prompt, and the same answer across three freshly started servers. That is why
IDT classifies it as permanent and does not retry — a retry resends byte-for-byte the
same request.

Changing the prompt is what works. Which change works is not predictable, so try more
than one.

### A refusal does not poison the session

Worth stating because one test run made it look that way. On a fresh server the order
makes no difference: a refusal, then an immediately successful request on the same
server. One trip cannot wreck a batch — consistent with the 519/520 run where the single
refusal was at image 372 and everything after it succeeded.

---

## A different failure that looks the same

Not every HTTP 500 from this provider is a refusal. Seen in a 90-image run:

```
{"error":{"message":"The operation couldn't be completed.
          (ModelManagerServices.ModelManagerError error 1001.)",
          "code":"500","type":"server_error"}}
```

That is Apple's model manager failing to load the model for one request, and
unlike a refusal it is **transient**. Both images that hit it described fine when
tried again — one succeeded three times out of three, the other on the second
attempt. IDT now recognises it, marks it retryable, and the retry usually makes it
invisible.

The two are worth keeping straight because they call for opposite responses:

| | Safety refusal | Model manager error |
|---|---|---|
| Message | "safety guardrails were triggered" | "ModelManagerServices.ModelManagerError" |
| Stable for the same request? | yes, every time | no — usually succeeds on a retry |
| Time to fail | ~0.3s | varies |
| What helps | a different prompt style | trying again |

## Reproduce it yourself

From the repository root, with the Apple provider working (`idt models --provider apple`):

```bash
python3 - <<'PY'
import sys, io, json; sys.path.insert(0, '.')
from PIL import Image
from idt_core.providers.apple import AppleProvider, AppleFMError

PHOTO = '/Users/kellyford/Documents/September/Alaska and More - 239 of 402.jpeg'
concise = json.load(open('scripts/image_describer_config.json'))['prompt_variations']['concise']

img = Image.open(PHOTO).convert('RGB')
W, H = img.size
def jpg(im):
    b = io.BytesIO(); im.save(b, format='JPEG', quality=90); return b.getvalue()

crops = {
    'whole image':                 img,
    'top half (the mounts)':       img.crop((0, 0, W, H // 2)),
    'bottom half (no animals)':    img.crop((0, H // 2, W, H)),
    'centre top (shadows only)':   img.crop((W // 3, 0, 2 * W // 3, H // 2)),
}
p = AppleProvider()
for label, im in crops.items():
    out = []
    for _ in range(3):
        try:
            p.describe(jpg(im), 'image/jpeg', concise); out.append('ok')
        except AppleFMError:
            out.append('REFUSED')
    print(f'{label:28s} {out}')
PY
```

To try the prompt dimension instead, swap `concise` for `styles['narrative']`,
`styles['accessibility']` or `styles['detailed']` from the same config file, or prepend
any text at all to `narrative` and watch it flip.

---

## If you hit this on your own images

1. **Do not retry.** It is deterministic.
2. **Change the prompt style, and try more than one.** Which styles work varies by image
   and by exact prompt text — `detailed` described this photo on one machine and was
   refused on another. Longer, more elaborate prompts did better than short ones in every
   test here, which is the only pattern that held.
3. **Turn EXIF metadata off for that one image** if a prompt change is not enough — the
   metadata prefix is sometimes what tips it over.
4. **Use another provider** for images that refuse under every prompt. Claude, OpenAI and
   Ollama have their own filters, drawn in different places.

Expect scattered refusals in libraries with hunting, taxidermy or game photography.
Nothing is wrong with the installation when this happens.

---

## Where this is implemented

`idt_core/providers/apple.py` — `_GUARDRAIL_MARKER` and `GUARDRAIL_HINT`, recognised in
`FmServer.open_chat` alongside the context-window case. Test:
`test_a_safety_refusal_reads_as_a_refusal_not_a_server_fault` in
`pytest_tests/unit/test_apple_provider.py`.
