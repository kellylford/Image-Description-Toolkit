#!/usr/bin/env python3
"""
Loop until we get an empty response, then capture full diagnostics  
For OpenAI support case 05757486
"""

import json
import base64
import httpx
from pathlib import Path
from openai import OpenAI
import time

# Load API key
config_path = Path('scripts/image_describer_config.json')
with open(config_path) as f:
    config = json.load(f)
api_key = config['api_keys']['OpenAI']

# Create client
http_client = httpx.Client(timeout=30.0)
client = OpenAI(api_key=api_key, http_client=http_client)

# Load test images from testimages directory
testimages_dir = Path('testimages')
if not testimages_dir.exists():
    print("ERROR: testimages directory not found")
    exit(1)

# Get all images
image_files = []
for ext in ['*.jpg', '*.JPG', '*.png', '*.PNG', '*.jpeg', '*.JPEG']:
    image_files.extend(list(testimages_dir.glob(ext)))

if not image_files:
    print("ERROR: No images found in testimages/")
    exit(1)

print(f"Found {len(image_files)} test images")
print()

import openai
print(f"OpenAI SDK version: {openai.__version__}")
print(f"Model: gpt-5-nano-2025-08-07")
print()

prompt = "Provide a detailed description of this image."

attempt = 0
empty_count = 0
success_count = 0

print("Running requests until we get an empty response...")
print("=" * 80)

try:
    while attempt < 50:  # Try up to 50 images
        attempt += 1
        
        # Cycle through images
        test_image_path = image_files[(attempt - 1) % len(image_files)]
        
        # Load and encode image
        with open(test_image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        request_payload = {
            "model": "gpt-5-nano-2025-08-07",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            }],
            "max_completion_tokens": 1000
        }
        
        # Make request with raw response capture
        response_with_raw = client.chat.completions.with_raw_response.create(**request_payload)
        parsed_response = response_with_raw.parse()
        raw_http_response = response_with_raw.http_response
        
        # Parse raw body
        raw_body = raw_http_response.text
        raw_json = json.loads(raw_body)
        
        # Check response
        content = raw_json['choices'][0]['message'].get('content', '')
        finish_reason = raw_json['choices'][0]['finish_reason']
        usage = raw_json['usage']
        x_request_id = raw_http_response.headers.get('x-request-id', 'NONE')
        
        is_empty = (content == '')
        
        if is_empty:
            empty_count += 1
            status = "⚠️  EMPTY"
        else:
            success_count += 1
            status = "✓  OK"
        
        print(f"[{attempt}] {status} | {test_image_path.name[:30]:30} | "
              f"finish={finish_reason:8} | tokens={usage['completion_tokens']:4} | "
              f"content_len={len(content):4} | x-req-id={x_request_id[:12]}...")
        
        # If we got an empty response, save full details
        if is_empty and finish_reason == 'length':
            print()
            print("=" * 80)
            print("🎯 EMPTY RESPONSE CAPTURED! Saving full details...")
            print("=" * 80)
            print()
            
            # Save to file
            output = {
                "case_number": "05757486",
                "capture_date": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "attempt_number": attempt,
                "test_image": str(test_image_path),
                "sdk_version": openai.__version__,
                
                "request_payload": {
                    "model": request_payload["model"],
                    "max_completion_tokens": request_payload["max_completion_tokens"],
                    "temperature": "NOT SET (model default)",
                    "top_p": "NOT SET",
                    "tools": "NOT SET",
                    "functions": "NOT SET",
                    "response_format": "NOT SET",
                    "images_included": "YES (base64 encoded)",
                    "prompt": prompt,
                    "image_data_length": len(image_data)
                },
                
                "response_headers": dict(raw_http_response.headers),
                "x_request_id": x_request_id,
                
                "raw_response_body": raw_json,
                
                "parsed_fields": {
                    "response_id": raw_json['id'],
                    "model": raw_json['model'],
                    "finish_reason": finish_reason,
                    "usage": usage,
                    "content_length": len(content),
                    "content_is_empty": is_empty,
                    "message_fields": list(raw_json['choices'][0]['message'].keys()),
                    "has_tool_calls": 'tool_calls' in raw_json['choices'][0]['message'],
                    "has_function_call": 'function_call' in raw_json['choices'][0]['message']
                }
            }
            
            with open('empty_response_detailed_capture.json', 'w') as f:
                json.dump(output, f, indent=2)
            
            print("Saved to: empty_response_detailed_capture.json")
            print()
            print("SUMMARY:")
            print(f"  Response ID: {raw_json['id']}")
            print(f"  x-request-id: {x_request_id}")
            print(f"  finish_reason: {finish_reason}")
            print(f"  completion_tokens: {usage['completion_tokens']}")
            print(f"  content length: {len(content)} (EMPTY)")
            print(f"  tool_calls present: {'tool_calls' in raw_json['choices'][0]['message']}")
            print(f"  function_call present: {'function_call' in raw_json['choices'][0]['message']}")
            print()
            print("Raw response body saved in JSON file.")
            print()
            break
        
        # Small delay between requests
        time.sleep(1)

except KeyboardInterrupt:
    print("\n\nInterrupted by user")
except Exception as e:
    print(f"\n\nERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    http_client.close()

print()
print("=" * 80)
print(f"FINAL STATS: {attempt} attempts, {success_count} success, {empty_count} empty")
print("=" * 80)
