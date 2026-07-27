"""Does the image reach the model? Compare prompt_eval_count with and without it."""
import base64, json, sys, urllib.request
from pathlib import Path
OLLAMA="http://localhost:11434/api/generate"
MODEL=sys.argv[1]
IMG=Path.home()/"Documents/idt/try3.idtw/derived/frames/mcp_video-26116_singular_display/mcp_video-26116_singular_display_0.00s.jpg"
P="Describe this image for a screen reader user. Start with the main subject and overall scene."

def call(with_image):
    body={"model":MODEL,"prompt":P,"stream":False}
    if with_image:
        body["images"]=[base64.b64encode(IMG.read_bytes()).decode()]
    req=urllib.request.Request(OLLAMA,data=json.dumps(body).encode(),
                               headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=900) as r:
        d=json.loads(r.read())
    return d.get("prompt_eval_count"), (d.get("response") or "")[:110]

for flag in (False, True):
    try:
        n,txt=call(flag)
        print(f"{MODEL}  image={'YES' if flag else 'NO ':<3}  prompt_tokens={n}")
        print(f"    {txt}\n", flush=True)
    except Exception as e:
        print(f"{MODEL} image={flag}: ERROR {e}", flush=True)
