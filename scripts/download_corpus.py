#!/usr/bin/env python3
"""
Download Livy's texts from The Latin Library.

Usage:
    python scripts/download_corpus.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.downloader import download_all


def main():
    print("=" * 60)
    print("Livy Corpus Downloader")
    print("=" * 60)
    print()

    # Use project-relative paths
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "data" / "raw"

    results = download_all(output_dir=str(output_dir), delay=1.5)

    if results["failed"]:
        print(f"\nWarning: {len(results['failed'])} downloads failed.")
        print("You can re-run this script to retry failed downloads.")
        sys.exit(1)
    else:
        print("\nAll downloads completed successfully!")
        print(f"HTML files saved to: {output_dir}")


if __name__ == "__main__":
    main()
