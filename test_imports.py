#!/usr/bin/env python3
"""Quick test of core imports and provider availability"""
import sys
sys.path.insert(0, 'imagedescriber')
sys.path.insert(0, 'scripts')
sys.path.insert(0, 'shared')
sys.path.insert(0, 'models')
sys.path.insert(0, '.')

print('Testing imports...')
try:
    from imagedescriber.ai_providers import get_available_providers, get_all_providers, DEV_CLAUDE_MODELS, CLAUDE_MODEL_METADATA
    print(f'  ai_providers: OK - {len(DEV_CLAUDE_MODELS)} Claude models, {len(CLAUDE_MODEL_METADATA)} metadata entries')
    print(f'  Claude models: {DEV_CLAUDE_MODELS[:3]}...')
except Exception as e:
    print(f'  ai_providers: FAILED - {e}')

try:
    from imagedescriber.workers_wx import BatchProcessingWorker, ProcessingWorker
    print(f'  workers_wx: OK')
except Exception as e:
    print(f'  workers_wx: FAILED - {e}')

try:
    from imagedescriber.data_models import ImageItem, ImageDescription, ImageWorkspace
    print(f'  data_models: OK')
except Exception as e:
    print(f'  data_models: FAILED - {e}')

try:
    from imagedescriber.dialogs_wx import ProcessingOptionsDialog
    print(f'  dialogs_wx: OK')
except Exception as e:
    print(f'  dialogs_wx: FAILED - {e}')

# Test providers (no wx needed)
try:
    from imagedescriber.ai_providers import get_all_providers
    providers = get_all_providers()
    for name, p in providers.items():
        try:
            avail = p.is_available()
        except Exception as ex:
            avail = f'ERROR: {ex}'
        print(f'  Provider {name}: available={avail}')
except Exception as e:
    print(f'  Provider check: FAILED - {e}')

print('Done.')
