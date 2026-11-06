"""Download the Olist dataset from Kaggle into data/raw/.

Usage (from the repository root):

    uv run data/download_olist.py

Only the files the simulation needs are extracted. If the automatic
download fails, download the zip by hand from DATASET_PAGE, put it in
data/raw/ under ZIP_NAME and run the script again: it will only unpack it.
"""

import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

DATASET_PAGE = "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"
DOWNLOAD_URL = (
    "https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce"
)
RAW_DIR = Path(__file__).resolve().parent / "raw"
ZIP_NAME = "brazilian-ecommerce.zip"
NEEDED_FILES = (
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
)
CHUNK_BYTES = 1024 * 1024


def download(url: str, target: Path) -> None:
    """Stream ``url`` to ``target``, printing progress in megabytes."""
    partial = target.with_suffix(".part")
    with urllib.request.urlopen(url) as response, partial.open("wb") as out:
        received = 0
        while chunk := response.read(CHUNK_BYTES):
            out.write(chunk)
            received += len(chunk)
            print(f"\r  {received / CHUNK_BYTES:.1f} MB", end="", flush=True)
    print()
    partial.replace(target)


def extract(zip_path: Path, names: tuple[str, ...], target_dir: Path) -> None:
    """Unpack only ``names`` from ``zip_path`` into ``target_dir``."""
    with zipfile.ZipFile(zip_path) as archive:
        available = set(archive.namelist())
        missing = [name for name in names if name not in available]
        if missing:
            raise SystemExit(f"Zip does not contain: {', '.join(missing)}")
        for name in names:
            archive.extract(name, target_dir)
            print(f"  extracted {name}")


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if all((RAW_DIR / name).exists() for name in NEEDED_FILES):
        print(f"Olist data already in {RAW_DIR}")
        return

    zip_path = RAW_DIR / ZIP_NAME
    if not zip_path.exists():
        print(f"Downloading Olist dataset to {zip_path}")
        try:
            download(DOWNLOAD_URL, zip_path)
        except urllib.error.URLError as error:
            print(f"Download failed: {error}", file=sys.stderr)
            print(
                f"Download the zip by hand from {DATASET_PAGE},\n"
                f"save it as {zip_path} and run this script again.",
                file=sys.stderr,
            )
            raise SystemExit(1) from error

    print(f"Extracting into {RAW_DIR}")
    extract(zip_path, NEEDED_FILES, RAW_DIR)
    zip_path.unlink()
    print("Done.")


if __name__ == "__main__":
    main()
