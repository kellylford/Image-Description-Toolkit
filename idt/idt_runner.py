#!/usr/bin/env python3

import sys
import os
from pathlib import Path

# Add the project root to the path so imports work
# We're now in idt/ directory, so go up one level to project root
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'scripts'))

# Now import the CLI
from idt_cli import main

if __name__ == "__main__":
    sys.exit(main())