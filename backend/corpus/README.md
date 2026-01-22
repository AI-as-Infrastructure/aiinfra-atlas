# Corpus Data Directory

This directory contains the active corpus data for ATLAS:

- `sources/` - Source documents for the corpus (e.g., text files organized by category)
- `chroma_db/` - Vector store database
- `manifest.json` - Corpus metadata and statistics
- `bm25_corpus.jsonl` - BM25 search index

These files are managed by the Corpus Wizard and should not be edited manually.

To create or update the corpus, use the Corpus Wizard interface in the web application.