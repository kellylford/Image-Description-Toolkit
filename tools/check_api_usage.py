#!/usr/bin/env python3
"""
Query actual usage data from OpenAI and Claude APIs
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add scripts to path
scripts_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from config_loader import load_json_config

def check_openai_usage(api_key):
    """Query OpenAI usage endpoint"""
    print("\n" + "="*70)
    print("OPENAI USAGE DATA")
    print("="*70)
    
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        
        # Try to get usage data
        # Note: OpenAI's usage API is limited - may not have all details
        print("\n📊 Attempting to query OpenAI usage API...\n")
        
        # Get current date and 30 days ago
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        try:
            # Try the usage endpoint (may require specific permissions)
            # This might not work for all API keys
            response = client.with_raw_response.get(
                "/v1/usage",
                params={
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d")
                }
            )
            
            if response.status_code == 200:
                usage_data = response.json()
                print("✅ Usage data retrieved:")
                print(json.dumps(usage_data, indent=2))
            else:
                print(f"⚠️  Usage endpoint returned status {response.status_code}")
                print(f"Response: {response.text[:500]}")
        except Exception as usage_error:
            print(f"⚠️  Direct usage query not available: {usage_error}")
            print("\n💡 OpenAI usage data is available at:")
            print("   https://platform.openai.com/usage")
            print("\n   The API doesn't expose detailed billing/cost data directly.")
            print("   You can only see token counts from individual API responses.")
        
        # Try to list available models as verification
        print("\n🔑 API Key Status:")
        try:
            models = client.models.list()
            model_count = len(list(models))
            print(f"✅ API key valid - {model_count} models accessible")
            
            # Show GPT-5 models specifically
            gpt5_models = [m.id for m in client.models.list() if 'gpt-5' in m.id]
            if gpt5_models:
                print(f"\n📋 GPT-5 Models Available ({len(gpt5_models)}):")
                for model in sorted(gpt5_models)[:10]:  # Show first 10
                    print(f"   - {model}")
                if len(gpt5_models) > 10:
                    print(f"   ... and {len(gpt5_models) - 10} more")
        except Exception as model_error:
            print(f"❌ Could not list models: {model_error}")
            
    except ImportError:
        print("❌ openai package not installed")
        print("   Install with: pip install openai")
    except Exception as e:
        print(f"❌ Error querying OpenAI: {e}")


def check_claude_usage(api_key):
    """Query Claude/Anthropic usage endpoint"""
    print("\n" + "="*70)
    print("CLAUDE/ANTHROPIC USAGE DATA")
    print("="*70)
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        print("\n📊 Attempting to query Anthropic usage...\n")
        
        # Anthropic doesn't have a public usage API endpoint yet
        # But we can verify the key works
        print("🔑 API Key Status:")
        try:
            # Send a minimal test request to verify key
            message = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            
            print("✅ API key valid - Claude accessible")
            print(f"\n📋 Test response token usage:")
            print(f"   Input tokens: {message.usage.input_tokens}")
            print(f"   Output tokens: {message.usage.output_tokens}")
            
            print("\n💡 Anthropic usage/billing data available at:")
            print("   https://console.anthropic.com/settings/cost")
            print("\n   Like OpenAI, Anthropic doesn't expose detailed billing via API.")
            print("   Token counts are returned per-request only.")
            
        except anthropic.AuthenticationError:
            print("❌ API key authentication failed")
        except Exception as test_error:
            print(f"⚠️  API test failed: {test_error}")
            
    except ImportError:
        print("❌ anthropic package not installed")
        print("   Install with: pip install anthropic")
    except Exception as e:
        print(f"❌ Error querying Anthropic: {e}")


def main():
    """Main function"""
    print("\n" + "="*70)
    print("API USAGE VERIFICATION")
    print("="*70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load API keys from config
    try:
        config, _, _ = load_json_config('image_describer_config.json')
        api_keys = config.get('api_keys', {})
        
        openai_key = api_keys.get('OpenAI') or api_keys.get('openai')
        claude_key = api_keys.get('claude') or api_keys.get('Claude')
        
        if openai_key:
            check_openai_usage(openai_key)
        else:
            print("\n⚠️  No OpenAI API key found in config")
        
        if claude_key:
            check_claude_usage(claude_key)
        else:
            print("\n⚠️  No Claude API key found in config")
        
        # Summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print("\n📌 Key Findings:")
        print("   • APIs return token counts per-request (what we already track)")
        print("   • Total usage/cost must be viewed in web dashboards:")
        print("     - OpenAI: https://platform.openai.com/usage")
        print("     - Claude: https://console.anthropic.com/settings/cost")
        print("\n💡 For IDT cost calculation:")
        print("   • We can track cumulative tokens per session")
        print("   • We can multiply by known pricing → estimated cost")
        print("   • But we can't verify against actual billing via API")
        print("")
        
    except Exception as e:
        print(f"\n❌ Error loading config: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
