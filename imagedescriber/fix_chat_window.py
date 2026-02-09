
from pathlib import Path

path = Path(r"c:\Users\kelly\GitHub\Image-Description-Toolkit\imagedescriber\chat_window_wx.py")
content = path.read_text(encoding='utf-8')

# The corrupted string pattern
corruption_start = 'API key string or None if not found/not needed'
if corruption_start in content:
    # Find the corruption (it seems to be followed by literals)
    # Be careful, the read_file output showed literal \n chars which means the file content has \n characters
    # We want to replace the escaped version with real code.
    
    # We can use a simpler approach: Re-write the function _get_api_key_for_provider entirely
    # The clean code:
    clean_code = '''    def _get_api_key_for_provider(self, provider: str) -> Optional[str]:
        """Load API key for the specified provider from config
        
        Args:
            provider: Provider name (ollama, openai, claude, huggingface)
            
        Returns:
            API key string or None if not found/not needed
        """
        # Ollama doesn't need API key (runs locally)
        if provider.lower() == 'ollama':
            return None
        
        try:
            # Load config to get API keys
            from config_loader import load_json_config
            
            config, _, _ = load_json_config('image_describer_config.json')
            if not config:
                return None
            
            # Get API keys dict
            api_keys = config.get('api_keys', {})
            
            # Match provider name (case-insensitive)
            for key_provider, api_key in api_keys.items():
                if key_provider.lower() == provider.lower():
                    return api_key
            
            # Check for standard capitalization
            provider_map = {
                'openai': 'OpenAI',
                'claude': 'Claude',
                'huggingface': 'HuggingFace'
            }
            
            standard_name = provider_map.get(provider.lower())
            if standard_name and standard_name in api_keys:
                return api_keys[standard_name]
            
            return None
            
        except Exception as e:
            print(f"Error loading API key for {provider}: {e}")
            return None
'''
    
    # We need to find what to replace.
    # The file has:
    #     def _get_api_key_for_provider(self, provider: str) -> Optional[str]:
    # ... down to ...
    #         Returns:
    #             API key string or None if not found/not needed
    # (Then the corruption)
    
    # Let's find the function definition start
    func_def = 'def _get_api_key_for_provider(self, provider: str)'
    start_idx = content.find(func_def)
    
    if start_idx != -1:
        # Find the start of the next function
        next_func = 'def on_chat_update(self, event):'
        end_idx = content.find(next_func, start_idx)
        
        if end_idx != -1:
            # Check indentation of next func to capture preceding newlines/indentation
            # But simpler: replace everything from start_idx to end_idx with clean_code + sufficient newlines
            
            # Preserve indentation of clean_code (it's already indented)
            
            new_content = content[:start_idx] + clean_code + "\n    " + content[end_idx:]
            path.write_text(new_content, encoding='utf-8')
            print("Successfully fixed chat_window_wx.py")
        else:
            print("Could not find end of function")
    else:
        print("Could not find start of function")
else:
    print("Could not find start marker")
