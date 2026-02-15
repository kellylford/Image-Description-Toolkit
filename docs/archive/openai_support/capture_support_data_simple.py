#!/usr/bin/env python3
"""
Simpler OpenAI Support Data Assembler

Uses existing failed example + captures what's missing:
- 1 more failed example (if we can get one in reasonable time)
- 1 successful example  
- Test with temperature=0

Case 05757486
"""

import sys
import os
import json
import base64
from pathlib import Path
from datetime import datetime, timezone
import time

# Add scripts to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / 'scripts'))

from config_loader import load_json_config


def load_api_key():
    """Load OpenAI API key from config"""
    config, config_path, source = load_json_config('image_describer_config.json')
    if not config:
        return None
    return config.get('api_keys', {}).get('OpenAI')


def encode_image_base64(image_path: Path) -> str:
    """Encode image to base64"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def capture_with_details(client, model: str, image_path: Path, temperature=None):
    """Capture single request with all diagnostic details"""
    
    base64_img = encode_image_base64(image_path)
    
    request_params = {
        "model": model,
        "max_completion_tokens": 1000,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image in detail."},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
                }
            ]
        }]
    }
    
    if temperature is not None:
        request_params["temperature"] = temperature
    
    # Timestamps
    request_time = datetime.now(timezone.utc)
    
    # Make request
    raw_response = client.chat.completions.with_raw_response.create(**request_params)
    
    response_time = datetime.now(timezone.utc)
    response = raw_response.parse()
    headers = dict(raw_response.headers)
    response_body = json.loads(raw_response.text)
    
    choice = response.choices[0]
    content = choice.message.content or ""
    is_empty = len(content.strip()) == 0
    
    # Build the exact raw HTTP request JSON (what was sent over the wire)
    # Note: The actual wire format doesn't include the full base64, but OpenAI wants to see the structure
    raw_request_json = {
        "model": model,
        "max_completion_tokens": 1000,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image in detail."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,<BASE64_IMAGE_DATA_{len(base64_img)}_CHARS>"}}
            ]
        }]
    }
    
    if temperature is not None:
        raw_request_json["temperature"] = temperature
    
    return {
        "test_image": image_path.name,
        "capture_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        
        # Timing with timezone
        "timing": {
            "request_sent_utc": request_time.isoformat(),
            "response_received_utc": response_time.isoformat(),
            "request_sent_formatted": request_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " UTC",
            "response_received_formatted": response_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " UTC"
        },
        
        # RAW HTTP REQUEST JSON (as sent over wire)
        "raw_http_request_json": raw_request_json,
        
        # Response headers (focus on what OpenAI requested)
        "response_headers": {
            "x-request-id": headers.get('x-request-id'),
            "date": headers.get('date'),
            "openai-processing-ms": headers.get('openai-processing-ms'),
            "openai-organization": headers.get('openai-organization'),
            "openai-version": headers.get('openai-version'),
            # Include all headers for completeness
            "_all_headers": dict(headers)
        },
        
        # RAW HTTP RESPONSE BODY
        "raw_http_response_body": response_body,
        
        # Parsed summary
        "summary": {
            "response_id": response.id,
            "model": response.model,
            "is_empty": is_empty,
            "content_length": len(content),
            "finish_reason": choice.finish_reason,
            "completion_tokens": response.usage.completion_tokens,
            "reasoning_tokens": getattr(response.usage.completion_tokens_details, 'reasoning_tokens', None) if hasattr(response.usage, 'completion_tokens_details') else None,
            "temperature_used": temperature if temperature is not None else "NOT SET (model default)"
        }
    }


def main():
    print("=" * 70)
    print("OpenAI Support Data Collection (Case 05757486)")
    print("=" * 70)
    
    api_key = load_api_key()
    if not api_key:
        print("❌ No API key")
        return 1
    
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    
    test_dir = SCRIPT_DIR / 'testimages'
    images = sorted([f for f in test_dir.iterdir() if f.suffix.lower() in ['.jpg', '.jpeg', '.png']])
    
    if len(images) < 2:
        print("❌ Need test images")
        return 1
    
    model = "gpt-5-nano-2025-08-07"
    captures = []
    
    print(f"\nModel: {model}")
    print(f"Images available: {len(images)}\n")
    
    # =========================================================================
    # STEP 1: Load existing failed example
    # =========================================================================
    print("=" * 70)
    print("STEP 1: Loading existing failed example")
    print("=" * 70)
    
    existing_file = SCRIPT_DIR / "empty_response_detailed_capture.json"
    if existing_file.exists():
        with open(existing_file) as f:
            existing_data = json.load(f)
        print(f"✓ Loaded existing failed example")
        print(f"  Response ID: {existing_data.get('raw_response_body', {}).get('id')}")
        print(f"  x-request-id: {existing_data.get('x_request_id')}")
        
        # Reformat to match our new structure
        captures.append({
            "example_type": "FAILED (existing capture)",
            "data": existing_data
        })
    else:
        print("⚠️  No existing failed example found")
    
    # =========================================================================
    # STEP 2: Try to get one more failed example (limited attempts)
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 2: Attempting to capture 1 additional failed example")
    print("=" * 70)
    print("(Will try up to 20 attempts, then continue regardless)\n")
    
    failed_count = 0
    for attempt in range(1, 21):
        img = images[attempt % len(images)]
        try:
            data = capture_with_details(client, model, img)
            
            status = "EMPTY" if data["summary"]["is_empty"] else "SUCCESS"
            print(f"[{attempt:2d}] {status:7s} | {img.name:20s} | finish={data['summary']['finish_reason']:6s} | tokens={data['summary']['completion_tokens']:4d}")
            
            if data["summary"]["is_empty"]:
                print(f"  ✓ Captured failed example!")
                captures.append({
                    "example_type": "FAILED (additional)",
                    "data": data
                })
                failed_count += 1
                break
            
            time.sleep(0.5)
        except Exception as e:
            print(f"[{attempt:2d}] ERROR: {e}")
    
    if failed_count == 0:
        print(f"\n⚠️  Could not capture additional failed example in 20 attempts")
        print("   (Model may be working more reliably now - that's actually good!)")
    
    # =========================================================================
    # STEP 3: Get successful example
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 3: Capturing 1 successful example")
    print("=" * 70)
    
    for attempt in range(1, 11):
        img = images[attempt % len(images)]
        try:
            data = capture_with_details(client, model, img)
            
            if not data["summary"]["is_empty"]:
                print(f"✓ Captured successful example")
                print(f"  Response ID: {data['summary']['response_id']}")
                print(f"  x-request-id: {data['response_headers']['x-request-id']}")
                captures.append({
                    "example_type": "SUCCESSFUL",
                    "data": data
                })
                break
            
            time.sleep(0.5)
        except Exception as e:
            print(f"ERROR: {e}")
    
    # =========================================================================
    # STEP 4: Test with temperature=0
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 4: Testing with temperature=0 (consistency check)")
    print("=" * 70)
    
    temp0_results = {"empty": 0, "success": 0}
    temp0_examples = []
    
    for attempt in range(1, 16):
        img = images[attempt % len(images)]
        try:
            data = capture_with_details(client, model, img, temperature=0)
            
            if data["summary"]["is_empty"]:
                temp0_results["empty"] += 1
                status = "EMPTY"
                if len(temp0_examples) == 0 or not temp0_examples[0]["data"]["summary"]["is_empty"]:
                    temp0_examples.append({"example_type": "TEMPERATURE=0 (empty)", "data": data})
            else:
                temp0_results["success"] += 1
                status = "SUCCESS"
                if len([e for e in temp0_examples if not e["data"]["summary"]["is_empty"]]) == 0:
                    temp0_examples.append({"example_type": "TEMPERATURE=0 (success)", "data": data})
            
            print(f"[{attempt:2d}] {status:7s} | tokens={data['summary']['completion_tokens']:4d}")
            
            # Stop once we have at least one of each type, or after 15 attempts
            if len(temp0_examples) >= 2:
                break
            
            time.sleep(0.5)
        except Exception as e:
            print(f"[{attempt:2d}] ERROR: {e}")
    
    captures.extend(temp0_examples)
    
    total_temp0 = temp0_results["empty"] + temp0_results["success"]
    empty_rate = (temp0_results["empty"] / total_temp0 * 100) if total_temp0 > 0 else 0
    
    print(f"\nTemperature=0 results: {temp0_results['empty']} empty, {temp0_results['success']} success ({empty_rate:.1f}% empty rate)")
    
    if temp0_results["empty"] > 0:
        print("⚠️  IMPORTANT: Empty responses STILL OCCUR with temperature=0")
    
    # =========================================================================
    # SAVE RESULTS
    # =========================================================================
    output = {
        "case_number": "05757486",
        "created": datetime.now(timezone.utc).isoformat(),
        "sdk_version": "2.16.0",
        "model_tested": model,
        
        "summary": {
            "total_examples_captured": len(captures),
            "failed_examples": sum(1 for c in captures if "FAILED" in c["example_type"]),
            "successful_examples": sum(1 for c in captures if "SUCCESSFUL" in c["example_type"]),
            "temperature_0_test": {
                "attempts": total_temp0,
                "empty_count": temp0_results["empty"],
                "success_count": temp0_results["success"],
                "empty_rate_percent": empty_rate
            }
        },
        
        "examples": captures
    }
    
    output_file = SCRIPT_DIR / "openai_support_case_05757486_complete.json"
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)
    print(f"\n✓ Saved to: {output_file.name}")
    print(f"  Total examples: {len(captures)}")
    print("\nReady to send to OpenAI Support!")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
