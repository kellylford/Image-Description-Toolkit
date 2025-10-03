#!/usr/bin/env python3
"""
Backward compatibility wrapper for check_models.py

The actual implementation has been moved to models/check_models.py
This wrapper maintains compatibility with existing documentation and scripts.

For new usage, prefer:
    python -m models.check_models
"""

import sys
from pathlib import Path

# Add models directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the actual implementation
from models.check_models import main

if __name__ == "__main__":
    print("Note: check_models.py has moved to models/check_models.py")
    print("      You can also run: python -m models.check_models\n")
    main()
