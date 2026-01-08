"""
Analyzer module for word frequency analysis and database creation.
"""

import re
import sqlite3
from collections import Counter
from pathlib import Path

from .downloader import get_book_metadata
from .text_extractor import load_text, tokenize


def calculate_frequencies(text: str) -> Counter:
    """Calculate word frequencies for a text."""
    words = tokenize(text)
    return Counter(words)


def calculate_relative_frequency(count: int, total_words: int) -> float:
    """
    Calculate relative frequency per 10,000 words.

    This normalization allows comparison across books of different lengths.
    """
    if total_words == 0:
        return 0.0
    return (count / total_words) * 10000


def extract_snippets(
    text: str,
    word: str,
    context_chars: int = 50,
    max_snippets: int = 5
) -> list[dict]:
    """
    Extract word-in-context snippets.

    Args:
        text: Full text to search
        word: Word to find (case-insensitive)
        context_chars: Characters of context on each side
        max_snippets: Maximum number of snippets to return

    Returns:
        List of dicts with 'context' and 'position' keys
    """
    snippets = []
    pattern = re.compile(rf'\b{re.escape(word)}\b', re.IGNORECASE)

    for match in pattern.finditer(text):
        start = max(0, match.start() - context_chars)
        end = min(len(text), match.end() + context_chars)
        context = text[start:end]

        # Add ellipsis if truncated
        if start > 0:
            context = "..." + context
        if end < len(text):
            context = context + "..."

        snippets.append({
            "context": context,
            "position": match.start()
        })

        if len(snippets) >= max_snippets:
            break

    return snippets


def create_database(db_path: str = "data/analysis/word_index.sqlite"):
    """Create the SQLite database with required tables."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing database
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.executescript("""
        CREATE TABLE books (
            book_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            sequence_index INTEGER NOT NULL,
            total_words INTEGER NOT NULL,
            unique_words INTEGER NOT NULL
        );

        CREATE TABLE word_frequencies (
            word TEXT NOT NULL,
            book_id TEXT NOT NULL,
            count INTEGER NOT NULL,
            relative_frequency REAL NOT NULL,
            PRIMARY KEY (word, book_id),
            FOREIGN KEY (book_id) REFERENCES books(book_id)
        );

        CREATE TABLE word_stats (
            word TEXT PRIMARY KEY,
            total_count INTEGER NOT NULL,
            book_count INTEGER NOT NULL,
            mean_position REAL NOT NULL
        );

        CREATE TABLE snippets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            book_id TEXT NOT NULL,
            context TEXT NOT NULL,
            position_in_book INTEGER NOT NULL,
            FOREIGN KEY (book_id) REFERENCES books(book_id)
        );

        CREATE INDEX idx_word_freq_word ON word_frequencies(word);
        CREATE INDEX idx_snippets_word ON snippets(word);
        CREATE INDEX idx_word_stats_position ON word_stats(mean_position);
        CREATE INDEX idx_word_stats_count ON word_stats(total_count);
    """)

    conn.commit()
    return conn


def run_analysis(
    texts_dir: str = "data/texts",
    db_path: str = "data/analysis/word_index.sqlite",
    min_word_freq: int = 2,
    max_snippets_per_book: int = 5
):
    """
    Run full analysis pipeline and populate database.

    Args:
        texts_dir: Directory containing extracted text files
        db_path: Path to SQLite database
        min_word_freq: Minimum total frequency for a word to be included in snippets
        max_snippets_per_book: Maximum snippets to store per word per book
    """
    print("Creating database...")
    conn = create_database(db_path)
    cursor = conn.cursor()

    # Get book metadata
    book_metadata = get_book_metadata()
    book_id_to_metadata = {b["book_id"]: b for b in book_metadata}

    # Process each book
    all_frequencies = {}  # word -> {book_id: count}
    book_totals = {}  # book_id -> total_words
    book_texts = {}  # book_id -> raw text

    print("Calculating word frequencies...")
    for meta in book_metadata:
        book_id = meta["book_id"]
        try:
            text = load_text(book_id, texts_dir)
            book_texts[book_id] = text
        except FileNotFoundError:
            print(f"  Skipping {book_id}: text file not found")
            continue

        frequencies = calculate_frequencies(text)
        total_words = sum(frequencies.values())
        unique_words = len(frequencies)
        book_totals[book_id] = total_words

        # Store in books table
        cursor.execute(
            "INSERT INTO books VALUES (?, ?, ?, ?, ?)",
            (book_id, meta["title"], meta["sequence_index"], total_words, unique_words)
        )

        # Aggregate frequencies
        for word, count in frequencies.items():
            if word not in all_frequencies:
                all_frequencies[word] = {}
            all_frequencies[word][book_id] = count

        print(f"  {meta['title']}: {total_words} words, {unique_words} unique")

    # Store word frequencies and calculate stats
    print("Storing word frequencies and calculating statistics...")
    word_stats = []

    for word, book_counts in all_frequencies.items():
        total_count = sum(book_counts.values())
        book_count = len(book_counts)

        # Calculate mean position (weighted by frequency)
        weighted_sum = 0
        for book_id, count in book_counts.items():
            if book_id in book_id_to_metadata:
                seq_idx = book_id_to_metadata[book_id]["sequence_index"]
                weighted_sum += seq_idx * count
        mean_position = weighted_sum / total_count if total_count > 0 else 0

        word_stats.append((word, total_count, book_count, mean_position))

        # Store per-book frequencies
        for book_id, count in book_counts.items():
            if book_id in book_totals:
                rel_freq = calculate_relative_frequency(count, book_totals[book_id])
                cursor.execute(
                    "INSERT INTO word_frequencies VALUES (?, ?, ?, ?)",
                    (word, book_id, count, rel_freq)
                )

    # Batch insert word stats
    cursor.executemany(
        "INSERT INTO word_stats VALUES (?, ?, ?, ?)",
        word_stats
    )

    # Extract and store snippets for common words
    print("Extracting snippets for common words...")
    common_words = [w for w, total, _, _ in word_stats if total >= min_word_freq]
    print(f"  Processing {len(common_words)} words with frequency >= {min_word_freq}")

    snippet_count = 0
    for word in common_words:
        for book_id, text in book_texts.items():
            snippets = extract_snippets(text, word, max_snippets=max_snippets_per_book)
            for snippet in snippets:
                cursor.execute(
                    "INSERT INTO snippets (word, book_id, context, position_in_book) VALUES (?, ?, ?, ?)",
                    (word, book_id, snippet["context"], snippet["position"])
                )
                snippet_count += 1

    print(f"  Stored {snippet_count} snippets")

    conn.commit()

    # Print summary
    cursor.execute("SELECT COUNT(*) FROM books")
    num_books = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT word) FROM word_frequencies")
    num_words = cursor.fetchone()[0]

    print(f"\nAnalysis complete!")
    print(f"  Books processed: {num_books}")
    print(f"  Unique words: {num_words}")
    print(f"  Database saved to: {db_path}")

    conn.close()


def get_word_frequencies(word: str, db_path: str = "data/analysis/word_index.sqlite") -> list[dict]:
    """
    Get frequency data for a word across all books.

    Returns list of dicts with book_id, title, sequence_index, count, relative_frequency
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT b.book_id, b.title, b.sequence_index,
               COALESCE(wf.count, 0) as count,
               COALESCE(wf.relative_frequency, 0) as relative_frequency
        FROM books b
        LEFT JOIN word_frequencies wf ON b.book_id = wf.book_id AND wf.word = ?
        ORDER BY b.sequence_index
    """, (word.lower(),))

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_word_snippets(word: str, db_path: str = "data/analysis/word_index.sqlite") -> list[dict]:
    """
    Get snippets for a word across all books.

    Returns list of dicts with book_id, title, context, position
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT b.book_id, b.title, b.sequence_index, s.context, s.position_in_book
        FROM snippets s
        JOIN books b ON s.book_id = b.book_id
        WHERE s.word = ?
        ORDER BY b.sequence_index, s.position_in_book
    """, (word.lower(),))

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_words_by_position(
    ascending: bool = True,
    min_count: int = 10,
    limit: int = 100,
    db_path: str = "data/analysis/word_index.sqlite"
) -> list[dict]:
    """
    Get words sorted by their mean position.

    Args:
        ascending: If True, return words appearing earlier in corpus first
        min_count: Minimum total count to include a word
        limit: Maximum number of words to return

    Returns list of dicts with word, total_count, book_count, mean_position
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    order = "ASC" if ascending else "DESC"
    cursor.execute(f"""
        SELECT word, total_count, book_count, mean_position
        FROM word_stats
        WHERE total_count >= ?
        ORDER BY mean_position {order}
        LIMIT ?
    """, (min_count, limit))

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def search_words(
    prefix: str,
    limit: int = 20,
    db_path: str = "data/analysis/word_index.sqlite"
) -> list[str]:
    """Search for words starting with a prefix."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT word FROM word_stats
        WHERE word LIKE ?
        ORDER BY total_count DESC
        LIMIT ?
    """, (prefix.lower() + "%", limit))

    results = [row[0] for row in cursor.fetchall()]
    conn.close()
    return results


if __name__ == "__main__":
    run_analysis()
