import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.visualization.server import server

if __name__ == "__main__":
    print(f"Launching server on {server.port}")
    server.launch()
