# Issue #225 — reproduction harnesses

Ad-hoc scripts used to isolate why `gemma4:*` models describe ordinary photos as
"abstract / kaleidoscopic". Kept because the conclusion is counter-intuitive and
someone will want to re-verify it. **Not** part of the test suite — they need a
running Ollama and take a long time.

## Requirements

```bash
pip install pillow          # only external dependency
ollama serve                # must be reachable at localhost:11434
```

Each script takes a model name as argv[1]. All read frames from a workspace bundle;
edit the `FR` / `BUNDLE` constants at the top if your paths differ.

## Scripts

| Script | Answers |
|---|---|
| `model_compare.py <model> <video>` | Does another model describe the same frames correctly? |
| `context_test.py <model> <video> <n>` | Does the EXIF `Context:` line cause it? (No.) |
| `crop_test.py <model>` | A/B/C/D — does removing/adding a sky region flip the result? (Yes, both ways.) |
| `aspect_test.py <model>` | E/F/G — is it aspect ratio, flat area, or resolution alone? (None of them.) |
| `token_probe.py <model>` | Does the image reach the model? Compares `prompt_eval_count` with and without. |

## Conclusion

The trigger is **real content confined to a small fraction of a vertically tall
frame, with the rest uniform** — e.g. an overcast sky filling the top ~55% of a
portrait video frame. No single factor reproduces it; see the issue for the full
matrix.

## Logs

`*.log` are the raw outputs behind the tables in the issue. `crop.log` is
`gemma4:31b-cloud`, `crop_cloud.log` is `gemma4:cloud`.

## Known harness caveats

- `model_compare.py` prints the literal label `minicpm` for the *new* model's output
  regardless of which model was passed. Read it as "the model in argv[1]".
- `crop_test.py` originally scored an `ERROR …` response string as "ok"; fixed to
  return `None` and be excluded from the tally. `aspect_test.py` has the fix.
- Ollama `*-cloud` endpoints failed roughly a quarter of calls (timeouts, HTTP 500,
  HTTP 503). Latency ranged 16s–828s on identical requests. Expect to re-run.
