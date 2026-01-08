#!/usr/bin/env python3
"""
Run the full analysis pipeline: extract text and build database.

Usage:
    python scripts/run_analysis.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.text_extractor import extract_and_save
from src.analyzer import run_analysis


def main():
    print("=" * 60)
    print("Livy Text Analysis Pipeline")
    print("=" * 60)
    print()

    # Use project-relative paths
    project_root = Path(__file__).parent.parent
    raw_dir = project_root / "data" / "raw"
    texts_dir = project_root / "data" / "texts"
    db_path = project_root / "data" / "analysis" / "word_index.sqlite"

    # Check for raw HTML files
    html_files = list(raw_dir.glob("liv.*.html"))
    if not html_files:
        print(f"Error: No HTML files found in {raw_dir}")
        print("Please run download_corpus.py first.")
        sys.exit(1)

    print(f"Found {len(html_files)} HTML files in {raw_dir}")
    print()

    # Step 1: Extract text
    print("Step 1: Extracting text from HTML...")
    print("-" * 40)
    word_counts = extract_and_save(
        input_dir=str(raw_dir),
        output_dir=str(texts_dir)
    )
    print()

    # Step 2: Run analysis
    print("Step 2: Analyzing word frequencies...")
    print("-" * 40)
    run_analysis(
        texts_dir=str(texts_dir),
        db_path=str(db_path),
        min_word_freq=2,
        max_snippets_per_book=5
    )
    print()

    print("=" * 60)
    print("Pipeline complete!")
    print()
    print("To launch the dashboard, run:")
    print(f"  streamlit run {project_root / 'app' / 'dashboard.py'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
