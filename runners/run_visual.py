import os
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "src" / "visualization" / "server.py"
PORT = "8521"


def main():
    os.execv(
        sys.executable,
        [
            sys.executable,
            "-m",
            "solara",
            "run",
            str(APP),
            "--port",
            PORT,
        ],
    )


if __name__ == "__main__":
    main()
