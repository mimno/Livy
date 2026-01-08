"""
Downloader module for fetching Livy's texts from The Latin Library.
"""

import os
import time
import requests
from pathlib import Path
from tqdm import tqdm

BASE_URL = "https://www.thelatinlibrary.com/"

# List of (book_id, url_path, sequence_index) tuples
# sequence_index creates a continuous sequence for position analysis
BOOKS = [
    ("praefatio", "livy/liv.pr.shtml", 0),
    ("1", "livy/liv.1.shtml", 1),
    ("2", "livy/liv.2.shtml", 2),
    ("3", "livy/liv.3.shtml", 3),
    ("4", "livy/liv.4.shtml", 4),
    ("5", "livy/liv.5.shtml", 5),
    ("6", "livy/liv.6.shtml", 6),
    ("7", "livy/liv.7.shtml", 7),
    ("8", "livy/liv.8.shtml", 8),
    ("9", "livy/liv.9.shtml", 9),
    ("10", "livy/liv.10.shtml", 10),
    # Books 11-20 are lost
    ("21", "livy/liv.21.shtml", 11),
    ("22", "livy/liv.22.shtml", 12),
    ("23", "livy/liv.23.shtml", 13),
    ("24", "livy/liv.24.shtml", 14),
    ("25", "livy/liv.25.shtml", 15),
    ("26", "livy/liv.26.shtml", 16),
    ("27", "livy/liv.27.shtml", 17),
    ("28", "livy/liv.28.shtml", 18),
    ("29", "livy/liv.29.shtml", 19),
    ("30", "livy/liv.30.shtml", 20),
    ("31", "livy/liv.31.shtml", 21),
    ("32", "livy/liv.32.shtml", 22),
    ("33", "livy/liv.33.shtml", 23),
    ("34", "livy/liv.34.shtml", 24),
    ("35", "livy/liv.35.shtml", 25),
    ("36", "livy/liv.36.shtml", 26),
    ("37", "livy/liv.37.shtml", 27),
    ("38", "livy/liv.38.shtml", 28),
    ("39", "livy/liv.39.shtml", 29),
    ("40", "livy/liv.40.shtml", 30),
    ("41", "livy/liv.41.shtml", 31),
    ("42", "livy/liv.42.shtml", 32),
    ("43", "livy/liv.43.shtml", 33),
    ("44", "livy/liv.44.shtml", 34),
    ("45", "livy/liv.45.shtml", 35),
]

HEADERS = {
    "User-Agent": "LivyTextAnalysis/1.0 (Educational Research Project)"
}


def get_book_title(book_id: str) -> str:
    """Return a human-readable title for a book."""
    if book_id == "praefatio":
        return "Praefatio"
    return f"Book {book_id}"


def download_book(book_id: str, url_path: str, output_dir: Path) -> bool:
    """
    Download a single book's HTML.

    Returns True if successful, False otherwise.
    """
    url = BASE_URL + url_path
    output_file = output_dir / f"liv.{book_id}.html"

    # Skip if already downloaded
    if output_file.exists():
        return True

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        # Save with UTF-8 encoding
        output_file.write_text(response.text, encoding="utf-8")
        return True

    except requests.RequestException as e:
        print(f"Error downloading {book_id}: {e}")
        return False


def download_all(output_dir: str = "data/raw", delay: float = 1.5) -> dict:
    """
    Download all books from The Latin Library.

    Args:
        output_dir: Directory to save HTML files
        delay: Seconds to wait between requests (rate limiting)

    Returns:
        Dict with 'success' and 'failed' lists of book_ids
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = {"success": [], "failed": []}

    print(f"Downloading {len(BOOKS)} books to {output_dir}...")

    for book_id, url_path, _ in tqdm(BOOKS, desc="Downloading"):
        success = download_book(book_id, url_path, output_path)

        if success:
            results["success"].append(book_id)
        else:
            results["failed"].append(book_id)

        # Rate limiting (skip delay for last item)
        if book_id != BOOKS[-1][0]:
            time.sleep(delay)

    print(f"\nDownload complete: {len(results['success'])} succeeded, {len(results['failed'])} failed")

    if results["failed"]:
        print(f"Failed books: {results['failed']}")

    return results


def get_book_metadata() -> list[dict]:
    """
    Return metadata for all books.

    Returns:
        List of dicts with book_id, title, url_path, sequence_index
    """
    return [
        {
            "book_id": book_id,
            "title": get_book_title(book_id),
            "url_path": url_path,
            "sequence_index": seq_idx
        }
        for book_id, url_path, seq_idx in BOOKS
    ]


if __name__ == "__main__":
    download_all()
