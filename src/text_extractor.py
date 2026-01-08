"""
Text extractor module for parsing HTML and extracting Latin text.
"""

import re
from pathlib import Path
from bs4 import BeautifulSoup

# Pattern to match section markers like [1], [2], etc.
SECTION_MARKER_PATTERN = re.compile(r'\[\d+\]')

# Pattern to match Latin words (including diacritics)
LATIN_WORD_PATTERN = re.compile(r'\b[a-zA-ZāēīōūĀĒĪŌŪàèìòùÀÈÌÒÙëïüËÏÜæœÆŒ]+\b')

# Diacritic normalization mapping
DIACRITIC_MAP = {
    'ā': 'a', 'ē': 'e', 'ī': 'i', 'ō': 'o', 'ū': 'u',
    'Ā': 'a', 'Ē': 'e', 'Ī': 'i', 'Ō': 'o', 'Ū': 'u',
    'à': 'a', 'è': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
    'À': 'a', 'È': 'e', 'Ì': 'i', 'Ò': 'o', 'Ù': 'u',
    'ë': 'e', 'ï': 'i', 'ü': 'u',
    'Ë': 'e', 'Ï': 'i', 'Ü': 'u',
    'æ': 'ae', 'œ': 'oe',
    'Æ': 'ae', 'Œ': 'oe',
}


def normalize_diacritics(text: str) -> str:
    """Normalize Latin diacritics to base ASCII letters."""
    for diacritic, replacement in DIACRITIC_MAP.items():
        text = text.replace(diacritic, replacement)
    return text


def extract_text_from_html(html_content: str) -> str:
    """
    Extract plain text from HTML, removing markup and navigation.

    Args:
        html_content: Raw HTML string

    Returns:
        Cleaned plain text
    """
    soup = BeautifulSoup(html_content, 'lxml')

    # Remove script and style elements
    for element in soup.find_all(['script', 'style']):
        element.decompose()

    # Get text content
    text = soup.get_text(separator=' ')

    # Remove section markers [1], [2], etc.
    text = SECTION_MARKER_PATTERN.sub('', text)

    # Normalize whitespace
    text = ' '.join(text.split())

    return text.strip()


def tokenize(text: str, normalize: bool = True) -> list[str]:
    """
    Tokenize Latin text into words.

    Args:
        text: Plain text string
        normalize: If True, normalize diacritics and lowercase

    Returns:
        List of word tokens
    """
    if normalize:
        text = normalize_diacritics(text)
        text = text.lower()

    words = LATIN_WORD_PATTERN.findall(text)

    if normalize:
        words = [w.lower() for w in words]

    return words


def extract_and_save(input_dir: str = "data/raw", output_dir: str = "data/texts") -> dict:
    """
    Extract text from all HTML files and save as plain text.

    Args:
        input_dir: Directory containing HTML files
        output_dir: Directory to save text files

    Returns:
        Dict mapping book_id to word count
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    word_counts = {}

    for html_file in sorted(input_path.glob("liv.*.html")):
        # Extract book_id from filename (liv.1.html -> 1, liv.praefatio.html -> praefatio)
        book_id = html_file.stem.replace("liv.", "")

        # Read and extract text
        html_content = html_file.read_text(encoding="utf-8")
        text = extract_text_from_html(html_content)

        # Save plain text
        output_file = output_path / f"{book_id}.txt"
        output_file.write_text(text, encoding="utf-8")

        # Count words
        words = tokenize(text)
        word_counts[book_id] = len(words)

        print(f"Extracted {book_id}: {len(words)} words")

    return word_counts


def load_text(book_id: str, texts_dir: str = "data/texts") -> str:
    """Load extracted text for a book."""
    text_file = Path(texts_dir) / f"{book_id}.txt"
    if not text_file.exists():
        raise FileNotFoundError(f"Text file not found: {text_file}")
    return text_file.read_text(encoding="utf-8")


def load_all_texts(texts_dir: str = "data/texts") -> dict[str, str]:
    """Load all extracted texts."""
    texts_path = Path(texts_dir)
    texts = {}
    for text_file in sorted(texts_path.glob("*.txt")):
        book_id = text_file.stem
        texts[book_id] = text_file.read_text(encoding="utf-8")
    return texts


if __name__ == "__main__":
    extract_and_save()
