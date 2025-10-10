#!/usr/bin/env python3

import sys
import os
from pathlib import Path

# Add the current directory to the path so imports work
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / 'scripts'))

# Now import the CLI
from idt_cli import main

if __name__ == "__main__":
    sys.exit(main())