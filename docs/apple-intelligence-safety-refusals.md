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

### It also depends on the prompt

The same image, same day, same machine:

| Prompt | Result |
|---|---|
| `narrative` alone | 6 described / 0 refused |
| `narrative` with any prefix — including IDT's own `"Capture metadata (not visible in the image): "` | 0 / 9 |
| `concise` | 0 / 6 |
| `accessibility` | described |
| `detailed` | described |

So the image sits *near* the threshold rather than over it. The animals supply the
signal; some prompt wordings push it across and others do not.

A practical consequence: **EXIF metadata being enabled made the difference** on this
image, because the pipeline prepends that `Capture metadata…` line to the prompt. Turning
metadata off would have described it — at the cost of losing date and camera context on
every other image, which is not a trade worth making for one photo in 520.

### Retrying does not help; a different prompt does

Refusal is deterministic for a given (image, prompt) pair: **0 successes in 11 retries**
with an unchanged prompt. That is why IDT classifies it as permanent and does not retry —
a retry would resend byte-for-byte the same request and cost another round trip.

### A refusal does not poison the session

Worth stating because one test run made it look that way. On a fresh server the order
makes no difference: a refusal, then an immediately successful request on the same
server. One trip cannot wreck a batch — consistent with the 519/520 run where the single
refusal was at image 372 and everything after it succeeded.

---

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
2. **Change the prompt style.** `accessibility` and `detailed` described this image every
   time. That is the whole fix in most cases.
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
