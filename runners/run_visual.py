"""Start the browser visualisation (src/visualization/app.py).

Usage (from the repository root)::

    uv run runners/run_visual.py            # http://localhost:8521
    uv run runners/run_visual.py --port 8600
"""

import argparse
import subprocess
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "src" / "visualization" / "app.py"
DEFAULT_PORT = 8521


def main(default_port: int = DEFAULT_PORT) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=default_port)
    args = parser.parse_args()
    command = [sys.executable, "-m", "solara", "run", str(APP), "--port", str(args.port)]
    # subprocess instead of os.execv: on Windows execv starts a detached
    # process and Ctrl+C no longer stops the server.
    try:
        sys.exit(subprocess.call(command))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
