"""
Streamlit dashboard for Livy text analysis.

Run with: streamlit run app/dashboard.py
"""

import re
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analyzer import (
    get_word_frequencies,
    get_word_snippets,
    get_words_by_position,
    search_words,
)

# Configuration
DB_PATH = Path(__file__).parent.parent / "data" / "analysis" / "word_index.sqlite"

st.set_page_config(
    page_title="Livy Text Analysis",
    page_icon=":scroll:",
    layout="wide"
)


def check_database():
    """Check if the database exists and is populated."""
    if not DB_PATH.exists():
        return False
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM books")
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except sqlite3.OperationalError:
        conn.close()
        return False


def get_corpus_stats():
    """Get summary statistics about the corpus."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*), SUM(total_words), SUM(unique_words) FROM books")
    num_books, total_words, _ = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM word_stats")
    unique_words = cursor.fetchone()[0]

    conn.close()
    return {
        "num_books": num_books,
        "total_words": total_words,
        "unique_words": unique_words
    }


def main():
    st.title("Livy Text Analysis")
    st.markdown("*Ab Urbe Condita* - Analyzing word frequencies across Livy's Roman history")

    # Check database
    if not check_database():
        st.error("Database not found. Please run the analysis pipeline first:")
        st.code("python scripts/download_corpus.py\npython scripts/run_analysis.py")
        return

    # Sidebar
    st.sidebar.header("Word Search")

    # Word input with search suggestions
    search_term = st.sidebar.text_input(
        "Enter a Latin word:",
        placeholder="e.g., romanus, hannibal, consul"
    ).strip().lower()

    # Show suggestions if typing
    if search_term and len(search_term) >= 2:
        suggestions = search_words(search_term, limit=10, db_path=str(DB_PATH))
        if suggestions and search_term not in suggestions:
            st.sidebar.caption("Suggestions: " + ", ".join(suggestions[:5]))

    # Corpus statistics
    stats = get_corpus_stats()
    st.sidebar.markdown("---")
    st.sidebar.subheader("Corpus Statistics")
    st.sidebar.markdown(f"**Books:** {stats['num_books']}")
    st.sidebar.markdown(f"**Total words:** {stats['total_words']:,}")
    st.sidebar.markdown(f"**Unique words:** {stats['unique_words']:,}")

    # Main content area
    tab1, tab2, tab3 = st.tabs(["Word Frequency", "Snippets", "Position Explorer"])

    # Tab 1: Word Frequency Histogram
    with tab1:
        st.header("Word Frequency by Book")

        if search_term:
            frequencies = get_word_frequencies(search_term, db_path=str(DB_PATH))

            if not frequencies or all(f["count"] == 0 for f in frequencies):
                st.warning(f"Word '{search_term}' not found in the corpus.")
            else:
                df = pd.DataFrame(frequencies)

                # Summary stats
                total_count = df["count"].sum()
                books_present = (df["count"] > 0).sum()
                st.markdown(f"**'{search_term}'** appears **{total_count:,}** times across **{books_present}** books")

                # Bar chart
                fig = px.bar(
                    df,
                    x="title",
                    y="relative_frequency",
                    title=f"Relative Frequency of '{search_term}' (per 10,000 words)",
                    labels={
                        "relative_frequency": "Frequency per 10k words",
                        "title": "Book"
                    },
                    color="relative_frequency",
                    color_continuous_scale="Viridis"
                )
                fig.update_layout(
                    xaxis_tickangle=-45,
                    showlegend=False,
                    height=500
                )
                st.plotly_chart(fig, use_container_width=True)

                # Raw data table
                with st.expander("View raw data"):
                    display_df = df[["title", "count", "relative_frequency"]].copy()
                    display_df.columns = ["Book", "Count", "Frequency (per 10k)"]
                    display_df["Frequency (per 10k)"] = display_df["Frequency (per 10k)"].round(2)
                    st.dataframe(display_df, hide_index=True)
        else:
            st.info("Enter a Latin word in the sidebar to see its frequency distribution across Livy's books.")

    # Tab 2: Snippets
    with tab2:
        st.header("Word in Context")

        if search_term:
            snippets = get_word_snippets(search_term, db_path=str(DB_PATH))

            if not snippets:
                st.warning(f"No snippets found for '{search_term}'.")
            else:
                st.markdown(f"Found **{len(snippets)}** occurrences of **'{search_term}'**")

                # Group by book
                current_book = None
                for snippet in snippets:
                    if snippet["title"] != current_book:
                        current_book = snippet["title"]
                        st.subheader(current_book)

                    # Highlight the search term
                    context = snippet["context"]
                    highlighted = re.sub(
                        rf'\b({re.escape(search_term)})\b',
                        r'**\1**',
                        context,
                        flags=re.IGNORECASE
                    )
                    st.markdown(f"_{highlighted}_")
        else:
            st.info("Enter a Latin word in the sidebar to see it in context from each book.")

    # Tab 3: Position Explorer
    with tab3:
        st.header("Words by Chronological Distribution")
        st.markdown("""
        The **mean position** indicates where a word tends to appear in Livy's narrative:
        - **Low values (0-10):** Words appearing more in early books (Praefatio, Books 1-10)
        - **Mid values (11-25):** Words distributed across Books 21-35
        - **High values (26-35):** Words appearing more in later books (Books 36-45)
        """)

        col1, col2 = st.columns(2)

        with col1:
            min_freq = st.slider(
                "Minimum word frequency",
                min_value=5,
                max_value=100,
                value=20,
                help="Filter out rare words"
            )

        with col2:
            num_words = st.slider(
                "Number of words to show",
                min_value=20,
                max_value=200,
                value=50
            )

        col_early, col_late = st.columns(2)

        with col_early:
            st.subheader("Early Books (Low Mean Position)")
            early_words = get_words_by_position(
                ascending=True,
                min_count=min_freq,
                limit=num_words,
                db_path=str(DB_PATH)
            )
            if early_words:
                df_early = pd.DataFrame(early_words)
                df_early.columns = ["Word", "Total Count", "Books", "Mean Position"]
                df_early["Mean Position"] = df_early["Mean Position"].round(2)
                st.dataframe(df_early, hide_index=True, height=400)

        with col_late:
            st.subheader("Late Books (High Mean Position)")
            late_words = get_words_by_position(
                ascending=False,
                min_count=min_freq,
                limit=num_words,
                db_path=str(DB_PATH)
            )
            if late_words:
                df_late = pd.DataFrame(late_words)
                df_late.columns = ["Word", "Total Count", "Books", "Mean Position"]
                df_late["Mean Position"] = df_late["Mean Position"].round(2)
                st.dataframe(df_late, hide_index=True, height=400)

        # Word comparison feature
        st.markdown("---")
        st.subheader("Compare Words")
        compare_words = st.text_input(
            "Enter words to compare (comma-separated):",
            placeholder="e.g., hannibal, scipio, consul"
        )

        if compare_words:
            words = [w.strip().lower() for w in compare_words.split(",") if w.strip()]
            if words:
                comparison_data = []
                for word in words[:5]:  # Limit to 5 words
                    freqs = get_word_frequencies(word, db_path=str(DB_PATH))
                    for f in freqs:
                        comparison_data.append({
                            "word": word,
                            "book": f["title"],
                            "sequence": f["sequence_index"],
                            "frequency": f["relative_frequency"]
                        })

                if comparison_data:
                    df_compare = pd.DataFrame(comparison_data)
                    fig = px.line(
                        df_compare,
                        x="sequence",
                        y="frequency",
                        color="word",
                        title="Word Frequency Comparison Across Books",
                        labels={
                            "frequency": "Frequency per 10k words",
                            "sequence": "Book (in sequence)"
                        },
                        markers=True
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
