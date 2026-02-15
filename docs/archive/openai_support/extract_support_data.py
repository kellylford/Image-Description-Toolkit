#!/usr/bin/env python3
"""Extract diagnostic data for OpenAI support case 05757486"""

import json
from pathlib import Path

# Load Phase 2 results (baseline test)
with open('test_results/phase2_nano_baseline_20260215_092037.json') as f:
    phase2 = json.load(f)

# Get 2 failed requests
empty_requests = [r for r in phase2 if r['status'] == 'empty']
success_requests = [r for r in phase2 if r['status'] == 'success']

print("=" * 80)
print("DATA FOR OPENAI SUPPORT CASE 05757486")
print("=" * 80)
print()

# General info
print("GENERAL INFORMATION:")
print("- Case Number: 05757486")
print("- Org ID: [Need to get from platform.openai.com/organization]")
print("- Endpoint: Chat Completions API (not Responses API)")
print("- Streaming: No")
print("- Model: gpt-5-nano-2025-08-07")
print("- Test Date: February 15, 2026")
print("- UTC Time Range: ~14:20-15:20 UTC (Phase 2 testing)")
print()

print("=" * 80)
print("FAILED REQUEST #1")
print("=" * 80)
if len(empty_requests) > 0:
    r = empty_requests[0]
    print(f"Image: {r['image_path'].split('/')[-1]}")
    print(f"Response ID: {r['response']['response_id']}")
    print(f"Model Returned: {r['response']['model_returned']}")
    print(f"Finish Reason: {r['response']['finish_reason']}")
    print(f"Processing Time: {r['processing_time']:.2f}s")
    print()
    print("Usage:")
    print(f"  - prompt_tokens: {r['response']['prompt_tokens']}")
    print(f"  - completion_tokens: {r['response']['completion_tokens']}")
    print(f"  - total_tokens: {r['response']['total_tokens']}")
    print()
    print("Full Response JSON:")
    print(json.dumps({
        'id': r['response']['response_id'],
        'model': r['response']['model_returned'],
        'choices': [{
            'message': {
                'role': 'assistant',
                'content': r['response']['text']  # This will be empty string
            },
            'finish_reason': r['response']['finish_reason']
        }],
        'usage': {
            'prompt_tokens': r['response']['prompt_tokens'],
            'completion_tokens': r['response']['completion_tokens'],
            'total_tokens': r['response']['total_tokens']
        }
    }, indent=2))
    print()
    print(f"CRITICAL: finish_reason='{r['response']['finish_reason']}' "
          f"with completion_tokens={r['response']['completion_tokens']} "
          f"but message.content is EMPTY (length={r['response']['text_length']})")
    print()

print("=" * 80)
print("FAILED REQUEST #2")
print("=" * 80)
if len(empty_requests) > 1:
    r = empty_requests[1]
    print(f"Image: {r['image_path'].split('/')[-1]}")
    print(f"Response ID: {r['response']['response_id']}")
    print(f"Model Returned: {r['response']['model_returned']}")
    print(f"Finish Reason: {r['response']['finish_reason']}")
    print(f"Processing Time: {r['processing_time']:.2f}s")
    print()
    print("Usage:")
    print(f"  - prompt_tokens: {r['response']['prompt_tokens']}")
    print(f"  - completion_tokens: {r['response']['completion_tokens']}")
    print(f"  - total_tokens: {r['response']['total_tokens']}")
    print()
    print("Full Response JSON:")
    print(json.dumps({
        'id': r['response']['response_id'],
        'model': r['response']['model_returned'],
        'choices': [{
            'message': {
                'role': 'assistant',
                'content': r['response']['text']
            },
            'finish_reason': r['response']['finish_reason']
        }],
        'usage': {
            'prompt_tokens': r['response']['prompt_tokens'],
            'completion_tokens': r['response']['completion_tokens'],
            'total_tokens': r['response']['total_tokens']
        }
    }, indent=2))
    print()
    print(f"CRITICAL: finish_reason='{r['response']['finish_reason']}' "
          f"with completion_tokens={r['response']['completion_tokens']} "
          f"but message.content is EMPTY (length={r['response']['text_length']})")
    print()

print("=" * 80)
print("SUCCESSFUL REQUEST (for comparison)")
print("=" * 80)
if len(success_requests) > 0:
    r = success_requests[0]
    print(f"Image: {r['image_path'].split('/')[-1]}")
    print(f"Response ID: {r['response']['response_id']}")
    print(f"Model Returned: {r['response']['model_returned']}")
    print(f"Finish Reason: {r['response']['finish_reason']}")
    print(f"Processing Time: {r['processing_time']:.2f}s")
    print()
    print("Usage:")
    print(f"  - prompt_tokens: {r['response']['prompt_tokens']}")
    print(f"  - completion_tokens: {r['response']['completion_tokens']}")
    print(f"  - total_tokens: {r['response']['total_tokens']}")
    print()
    print("Full Response JSON:")
    print(json.dumps({
        'id': r['response']['response_id'],
        'model': r['response']['model_returned'],
        'choices': [{
            'message': {
                'role': 'assistant',
                'content': r['response']['text'][:100] + '...'  # Truncated for display
            },
            'finish_reason': r['response']['finish_reason']
        }],
        'usage': {
            'prompt_tokens': r['response']['prompt_tokens'],
            'completion_tokens': r['response']['completion_tokens'],
            'total_tokens': r['response']['total_tokens']
        }
    }, indent=2))
    print()
    print(f"SUCCESS: finish_reason='{r['response']['finish_reason']}' "
          f"with completion_tokens={r['response']['completion_tokens']} "
          f"and message.content length={r['response']['text_length']}")
else:
    print("NO SUCCESSFUL REQUESTS in Phase 2 (only 2/100 succeeded)")
print()

print("=" * 80)
print("MISSING DATA (not captured during testing):")
print("=" * 80)
print("- Response header: x-request-id (we didn't capture HTTP headers)")
print("- Response header: X-Client-Request-Id (we didn't set this)")
print("- Organization ID (need to get from platform.openai.com/organization)")
print()
print("NOTE: We have 39 failed requests total in Phase 2 with identical pattern:")
print("      ALL show finish_reason='length' + completion_tokens=1000 but empty content")
print()
