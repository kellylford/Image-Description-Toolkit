import os, base64, time, openai
from pathlib import Path

api_key = os.environ.get("OPENAI_API_KEY", "").strip()
if not api_key:
    key_file = Path("/Users/kellyford/Library/CloudStorage/OneDrive-Personal/idt/openai.txt")
    api_key = key_file.read_text().strip()

print(f"Key: {api_key[:8]}...{api_key[-4:]}")

img = Path("/Users/kellyford/Documents/ImageDescriptionToolkit/WorkspaceFiles/"
           "Europe_09_20260223/extracted_frames/IMG_4087/IMG_4087_0.00s.jpg")
img_b64 = base64.b64encode(img.read_bytes()).decode()
print(f"Image: {img.name}  ({len(img_b64)//1024} KB base64)")

client = openai.OpenAI(api_key=api_key, timeout=60, max_retries=0)
t0 = time.time()
resp = client.chat.completions.create(
    model="gpt-4o-mini",
    max_tokens=300,
    messages=[{"role": "user", "content": [
        {"type": "text", "text": "Describe this image in 2-3 sentences for a visually impaired person."},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
    ]}]
)
elapsed = time.time() - t0
content = (resp.choices[0].message.content or "").strip()
print(f"\nStatus:  {'OK' if content else 'EMPTY'}")
print(f"Time:    {elapsed:.1f}s")
print(f"Tokens:  {resp.usage.prompt_tokens} in / {resp.usage.completion_tokens} out")
print(f"Result:  {content[:300]}")
