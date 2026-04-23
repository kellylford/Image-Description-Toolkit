#!/usr/bin/env python3
"""
OpenAI A/B Testing Script - Case 05757486

Tests requested by OpenAI Support:
1. Same request with max_completion_tokens=200 and 300 (instead of 1000)
2. Same request with ALL params explicitly set (including defaults)

Each test captures:
- Timestamp with timezone
- x-request-id
- Full request JSON
- Full response with headers
"""

import sys
import json
import base64
from pathlib import Path
from datetime import datetime, timezone
import time

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
from config_loader import load_json_config


def load_api_key():
    """Load OpenAI API key from config"""
    config, _, _ = load_json_config('image_describer_config.json')
    return config.get('api_keys', {}).get('OpenAI') if config else None


def encode_image(image_path: Path) -> str:
    """Encode image to base64"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def run_test(client, model: str, image_path: Path, test_config: dict):
    """
    Run a single test with specified configuration
    
    test_config includes:
    - name: Test name
    - max_completion_tokens: Token limit
    - explicit_params: Whether to set all params explicitly
    """
    print(f"\n{'='*70}")
    print(f"TEST: {test_config['name']}")
    print(f"{'='*70}")
    
    base64_img = encode_image(image_path)
    
    # Build request parameters
    request_params = {
        "model": model,
        "max_completion_tokens": test_config['max_completion_tokens'],
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
    
    # If explicit_params, add ALL parameters (even defaults)
    if test_config.get('explicit_params'):
        request_params.update({
            "temperature": 1,  # Model default (only value supported)
            "top_p": 1,        # SDK default
            "n": 1,            # SDK default
            "stream": False,   # SDK default
            "presence_penalty": 0,  # SDK default
            "frequency_penalty": 0  # SDK default
        })
        print("Setting ALL parameters explicitly (including defaults)")
    
    print(f"Configuration:")
    print(f"  max_completion_tokens: {test_config['max_completion_tokens']}")
    print(f"  explicit_params: {test_config.get('explicit_params', False)}")
    print(f"  image: {image_path.name}")
    
    # Capture timestamps
    request_time = datetime.now(timezone.utc)
    print(f"\nSending request at: {request_time.isoformat()}")
    
    # Make request with raw response
    try:
        raw_response = client.chat.completions.with_raw_response.create(**request_params)
        response_time = datetime.now(timezone.utc)
        
        response = raw_response.parse()
        headers = dict(raw_response.headers)
        response_body = json.loads(raw_response.text)
        
        # Extract key data
        choice = response.choices[0]
        content = choice.message.content or ""
        is_empty = len(content.strip()) == 0
        
        # Print results
        print(f"Response received at: {response_time.isoformat()}")
        print(f"\nRESULTS:")
        print(f"  Status: {'EMPTY ❌' if is_empty else 'SUCCESS ✓'}")
        print(f"  Response ID: {response.id}")
        print(f"  x-request-id: {headers.get('x-request-id')}")
        print(f"  openai-processing-ms: {headers.get('openai-processing-ms')}")
        print(f"  finish_reason: {choice.finish_reason}")
        print(f"  completion_tokens: {response.usage.completion_tokens}")
        if hasattr(response.usage, 'completion_tokens_details'):
            print(f"  reasoning_tokens: {response.usage.completion_tokens_details.reasoning_tokens}")
        print(f"  content_length: {len(content)}")
        
        if is_empty:
            print(f"\n⚠️  EMPTY RESPONSE CAPTURED")
        
        # Build detailed capture
        # Create the raw request JSON exactly as sent
        raw_request_json = {
            "model": model,
            "max_completion_tokens": test_config['max_completion_tokens'],
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image in detail."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,<BASE64_DATA_{len(base64_img)}_CHARS>"}}
                ]
            }]
        }
        
        if test_config.get('explicit_params'):
            raw_request_json.update({
                "temperature": 1,
                "top_p": 1,
                "n": 1,
                "stream": False,
                "presence_penalty": 0,
                "frequency_penalty": 0
            })
        
        return {
            "test_name": test_config['name'],
            "test_config": test_config,
            "timestamp_utc": request_time.isoformat(),
            "timestamp_formatted": request_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " UTC",
            
            "request": {
                "raw_json": raw_request_json,
                "actual_params_sent": {k: v for k, v in request_params.items() if k != 'messages'}
            },
            
            "response": {
                "timestamp_utc": response_time.isoformat(),
                "x_request_id": headers.get('x-request-id'),
                "response_id": response.id,
                "openai_processing_ms": headers.get('openai-processing-ms'),
                "headers": {
                    "x-request-id": headers.get('x-request-id'),
                    "date": headers.get('date'),
                    "openai-processing-ms": headers.get('openai-processing-ms'),
                    "openai-organization": headers.get('openai-organization'),
                    "openai-version": headers.get('openai-version')
                },
                "raw_body": response_body
            },
            
            "result": {
                "is_empty": is_empty,
                "content_length": len(content),
                "finish_reason": choice.finish_reason,
                "completion_tokens": response.usage.completion_tokens,
                "reasoning_tokens": response.usage.completion_tokens_details.reasoning_tokens if hasattr(response.usage, 'completion_tokens_details') else None
            }
        }
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return {
            "test_name": test_config['name'],
            "test_config": test_config,
            "timestamp_utc": request_time.isoformat(),
            "error": str(e)
        }


def main():
    print("=" * 70)
    print("OpenAI A/B Testing - Case 05757486")
    print("=" * 70)
    print("\nTests requested:")
    print("  1. max_completion_tokens=200")
    print("  2. max_completion_tokens=300")
    print("  3. All parameters explicitly set")
    print()
    
    # Load API key
    api_key = load_api_key()
    if not api_key:
        print("❌ No API key found")
        return 1
    
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    print("✓ OpenAI client initialized")
    
    # Load test images
    test_dir = Path(__file__).parent / 'testimages'
    images = sorted([f for f in test_dir.iterdir() if f.suffix.lower() in ['.jpg', '.jpeg', '.png']])
    
    if len(images) < 2:
        print("❌ Need test images")
        return 1
    
    print(f"✓ Found {len(images)} test images\n")
    
    model = "gpt-5-nano-2025-08-07"
    
    # Define test configurations
    test_configs = [
        {
            "name": "Test 1: max_completion_tokens=200",
            "max_completion_tokens": 200,
            "attempts": 10
        },
        {
            "name": "Test 2: max_completion_tokens=300",
            "max_completion_tokens": 300,
            "attempts": 10
        },
        {
            "name": "Test 3: All params explicit (max=1000)",
            "max_completion_tokens": 1000,
            "explicit_params": True,
            "attempts": 10
        }
    ]
    
    all_results = []
    
    for test_config in test_configs:
        print(f"\n{'#'*70}")
        print(f"# {test_config['name']}")
        print(f"# Running {test_config['attempts']} attempts")
        print(f"{'#'*70}")
        
        test_results = []
        empty_count = 0
        success_count = 0
        
        for attempt in range(1, test_config['attempts'] + 1):
            img = images[attempt % len(images)]
            
            # Create test config for this attempt
            attempt_config = {
                **test_config,
                "name": f"{test_config['name']} - Attempt {attempt}"
            }
            
            result = run_test(client, model, img, attempt_config)
            
            if "error" not in result:
                if result["result"]["is_empty"]:
                    empty_count += 1
                else:
                    success_count += 1
            
            test_results.append(result)
            
            # Brief delay
            if attempt < test_config['attempts']:
                time.sleep(0.5)
        
        # Summary for this test
        print(f"\n{'-'*70}")
        print(f"SUMMARY: {test_config['name']}")
        print(f"  Total attempts: {test_config['attempts']}")
        print(f"  Successful: {success_count}")
        print(f"  Empty: {empty_count}")
        print(f"  Empty rate: {empty_count/test_config['attempts']*100:.1f}%")
        print(f"{'-'*70}")
        
        all_results.extend(test_results)
    
    # Save all results
    output_file = Path(__file__).parent / "openai_ab_test_results.json"
    
    output = {
        "case_number": "05757486",
        "created": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "sdk_version": "2.16.0",
        
        "summary": {
            "test_1_max_200": {
                "empty": sum(1 for r in all_results[:10] if r.get("result", {}).get("is_empty")),
                "success": sum(1 for r in all_results[:10] if not r.get("result", {}).get("is_empty", True))
            },
            "test_2_max_300": {
                "empty": sum(1 for r in all_results[10:20] if r.get("result", {}).get("is_empty")),
                "success": sum(1 for r in all_results[10:20] if not r.get("result", {}).get("is_empty", True))
            },
            "test_3_explicit_params": {
                "empty": sum(1 for r in all_results[20:30] if r.get("result", {}).get("is_empty")),
                "success": sum(1 for r in all_results[20:30] if not r.get("result", {}).get("is_empty", True))
            }
        },
        
        "all_results": all_results
    }
    
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n{'='*70}")
    print("COMPLETE")
    print(f"{'='*70}")
    print(f"\n✓ All tests saved to: {output_file.name}")
    print("\nReady to send to OpenAI Support!")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
