#!/usr/bin/env python3
"""
Capture raw HTTP response data for OpenAI support case 05757486
Captures everything OpenAI support requested:
- Exact request payload
- Raw HTTP response body
- Response headers (x-request-id)
- Check for tool_calls/function_call fields
"""

import json
import base64
import httpx
from pathlib import Path
from openai import OpenAI

# Load API key
config_path = Path('scripts/image_describer_config.json')
with open(config_path) as f:
    config = json.load(f)
api_key = config['api_keys']['OpenAI']

# Create client with custom http_client to capture raw responses
http_client = httpx.Client()
client = OpenAI(api_key=api_key, http_client=http_client)

# Load a test image from testimages directory
testimages_dir = Path('testimages')
if not testimages_dir.exists():
    print("ERROR: testimages directory not found")
    exit(1)

# Find first JPG or PNG image
test_image_path = None
for ext in ['*.jpg', '*.JPG', '*.png', '*.PNG', '*.jpeg', '*.JPEG']:
    images = list(testimages_dir.glob(ext))
    if images:
        test_image_path = images[0]
        break

if not test_image_path:
    print("ERROR: No valid image found in testimages/")
    exit(1)

print("=" * 80)
print("OPENAI SUPPORT CASE 05757486 - RAW RESPONSE CAPTURE")
print("=" * 80)
print()

# Load and encode image
print(f"Test Image: {test_image_path}")
with open(test_image_path, 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

print(f"Image size (base64): {len(image_data)} characters")
print()

# Build exact request payload
prompt = "Provide a detailed description of this image, including key visual elements, context, and any notable features."

request_payload = {
    "model": "gpt-5-nano-2025-08-07",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
        ]
    }],
    "max_completion_tokens": 1000  # GPT-5 uses max_completion_tokens
}

print("=" * 80)
print("1. EXACT REQUEST PAYLOAD")
print("=" * 80)
print()
print("Request parameters (excluding base64 image data for readability):")
print(json.dumps({
    "model": request_payload["model"],
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,<{len(image_data)} chars>"}}
        ]
    }],
    "max_completion_tokens": request_payload["max_completion_tokens"]
}, indent=2))
print()
print("Additional parameters NOT set:")
print("  - temperature: NOT SET (model default)")
print("  - top_p: NOT SET")
print("  - tools: NOT SET")
print("  - functions: NOT SET")
print("  - response_format: NOT SET")
print("  - Images included: YES (via data:image/jpeg;base64,...)")
print()

print("=" * 80)
print("2. OPENAI PYTHON SDK VERSION")
print("=" * 80)
print()
import openai
print(f"openai package version: {openai.__version__}")
print()

print("=" * 80)
print("3. MAKING API REQUEST...")
print("=" * 80)
print()

# Make request and capture raw response
# The OpenAI SDK uses httpx under the hood, we need to access the raw response
try:
    # Use with_raw_response to get both parsed and raw data
    response_with_raw = client.chat.completions.with_raw_response.create(**request_payload)
    
    # Get parsed response
    parsed_response = response_with_raw.parse()
    
    # Get raw HTTP response
    raw_http_response = response_with_raw.http_response
    
    print("=" * 80)
    print("4. RAW HTTP RESPONSE HEADERS")
    print("=" * 80)
    print()
    for header, value in raw_http_response.headers.items():
        print(f"{header}: {value}")
    print()
    
    # Extract x-request-id
    x_request_id = raw_http_response.headers.get('x-request-id', 'NOT FOUND')
    print(f"CRITICAL: x-request-id = {x_request_id}")
    print()
    
    print("=" * 80)
    print("5. RAW HTTP RESPONSE BODY")
    print("=" * 80)
    print()
    raw_body = raw_http_response.text
    print("Raw response body (as received over the wire):")
    print(raw_body)
    print()
    
    # Parse to check structure
    raw_json = json.loads(raw_body)
    print()
    print("Parsed raw JSON (formatted):")
    print(json.dumps(raw_json, indent=2))
    print()
    
    print("=" * 80)
    print("6. CHECKING FOR NON-CONTENT FIELDS IN choices[0].message")
    print("=" * 80)
    print()
    
    message_obj = raw_json['choices'][0]['message']
    print("Fields present in choices[0].message:")
    for key in message_obj.keys():
        print(f"  - {key}: {type(message_obj[key]).__name__}")
    
    has_tool_calls = 'tool_calls' in message_obj
    has_function_call = 'function_call' in message_obj
    
    print()
    print(f"Has tool_calls field? {has_tool_calls}")
    if has_tool_calls:
        print(f"  tool_calls value: {message_obj['tool_calls']}")
    
    print(f"Has function_call field? {has_function_call}")
    if has_function_call:
        print(f"  function_call value: {message_obj['function_call']}")
    
    print()
    
    print("=" * 80)
    print("7. RESPONSE ANALYSIS")
    print("=" * 80)
    print()
    
    content = message_obj.get('content', '')
    finish_reason = raw_json['choices'][0]['finish_reason']
    usage = raw_json['usage']
    
    print(f"Response ID: {raw_json['id']}")
    print(f"Model: {raw_json['model']}")
    print(f"finish_reason: {finish_reason}")
    print(f"completion_tokens: {usage['completion_tokens']}")
    print(f"prompt_tokens: {usage['prompt_tokens']}")
    print(f"total_tokens: {usage['total_tokens']}")
    print()
    print(f"message.content length: {len(content)} characters")
    print(f"message.content is empty? {content == ''}")
    print()
    
    if content == '' and finish_reason == 'length':
        print("⚠️  ISSUE REPRODUCED!")
        print("    finish_reason='length' with completion_tokens > 0 but content is EMPTY")
    elif content == '':
        print("⚠️  EMPTY CONTENT (different pattern)")
        print(f"    finish_reason='{finish_reason}'")
    else:
        print("✓  Response contains content (successful request)")
        print(f"    First 100 chars: {content[:100]}...")
    print()
    
    print("=" * 80)
    print("8. SUMMARY FOR OPENAI SUPPORT")
    print("=" * 80)
    print()
    print(f"x-request-id: {x_request_id}")
    print(f"Response ID: {raw_json['id']}")
    print(f"SDK Version: {openai.__version__}")
    print(f"Empty content? {content == ''}")
    print(f"finish_reason: {finish_reason}")
    print(f"completion_tokens: {usage['completion_tokens']}")
    print()

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

finally:
    http_client.close()

print()
print("=" * 80)
print("DATA CAPTURE COMPLETE")
print("=" * 80)
print()
print("To send to OpenAI support:")
print("1. Copy sections 1, 4, 5, 6 from above")
print("2. Include x-request-id from section 4")
print("3. Include raw response body from section 5")
print("4. Note SDK version from section 2")
