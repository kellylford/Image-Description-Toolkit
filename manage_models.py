#!/usr/bin/env python3
"""
Backward compatibility wrapper for manage_models.py

The actual implementation has been moved to models/manage_models.py
This wrapper maintains compatibility with existing documentation and scripts.

For new usage, prefer:
    python -m models.manage_models
"""

import sys
from pathlib import Path

# Add models directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the actual implementation
from models.manage_models import main

if __name__ == "__main__":
    print("Note: manage_models.py has moved to models/manage_models.py")
    print("      You can also run: python -m models.manage_models\n")
    main()
