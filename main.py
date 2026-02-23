"""
Zero Ichi - WhatsApp Bot launcher.

Thin wrapper that adds src/ to Python path and delegates to the entry point.
You can also run: uv run zero-ichi
"""

import sys
from pathlib import Path

src_dir = str(Path(__file__).parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

if __name__ == "__main__":
    from main import main

    main()
