"""Retry the 5 models that returned empty with finish=length, using 1500 tokens."""
import base64, time, openai, io
from pathlib import Path
from PIL import Image

key = Path("/Users/kellyford/Library/CloudStorage/OneDrive-Personal/idt/openai.txt").read_text().strip()
client = openai.OpenAI(api_key=key, timeout=120, max_retries=0)

img_path = Path("/Users/kellyford/Documents/ImageDescriptionToolkit/WorkspaceFiles/"
                "Europe_09_20260223/extracted_frames/IMG_4087/IMG_4087_0.00s.jpg")
pil = Image.open(img_path).convert("RGB")
pil.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
buf = io.BytesIO()
pil.save(buf, format="JPEG", quality=85)
img_b64 = base64.b64encode(buf.getvalue()).decode()

prompt = "Describe this image in 2-3 sentences for a visually impaired person."

for model in ["gpt-5", "gpt-5-mini", "gpt-5-nano", "o4-mini", "o1"]:
    t0 = time.time()
    try:
        resp = client.chat.completions.create(
            model=model,
            max_completion_tokens=1500,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
            ]}]
        )
        elapsed = time.time() - t0
        content = (resp.choices[0].message.content or "").strip()
        finish = resp.choices[0].finish_reason
        tok_out = resp.usage.completion_tokens
        tok_reason = getattr(resp.usage, "completion_tokens_details", None)
        status = "OK" if content else "EMPTY"
        print(f"{model:<15} {status:<6} {elapsed:.1f}s  out={tok_out} finish={finish}  reasoning_details={tok_reason}")
        if content:
            print(f"  {content[:150]}")
    except Exception as e:
        print(f"{model:<15} FAIL   {time.time()-t0:.1f}s  {str(e)[:100]}")
