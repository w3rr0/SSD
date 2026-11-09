"""Start the browser visualisation on port 8522.

The Olist page is now part of the main visualisation
(``src/visualization/app.py``): orders come from the Olist generator by
default, and the sidebar switches placement, rack return policy, volume and
layout. This runner is kept for ``make run_visual_olist``.

    uv run runners/run_visual_olist.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_visual import main  # noqa: E402

if __name__ == "__main__":
    main(default_port=8522)
