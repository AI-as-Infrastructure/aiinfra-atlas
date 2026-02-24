"""
Manifest loader for ATLAS.

Loads corpus information dynamically from manifest.json to avoid hardcoded corpus lists.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Module-level cache
_manifest_cache: Optional[Dict[str, Any]] = None

# Country code mappings for label generation
COUNTRY_CODES = {
    "au": "Australia",
    "nz": "New Zealand",
    "uk": "United Kingdom",
    "ca": "Canada",
    "ie": "Ireland",
    "us": "United States",
}


def _get_manifest_path() -> str:
    """Get the path to manifest.json.

    Checks backend/corpus/ first (where the wizard stores it),
    then falls back to backend/targets/ for backward compatibility.
    """
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Wizard-built corpora store manifest in corpus/
    corpus_path = os.path.join(backend_dir, "corpus", "manifest.json")
    if os.path.exists(corpus_path):
        return corpus_path
    # Legacy fallback
    return os.path.join(backend_dir, "targets", "manifest.json")


def load_manifest() -> Dict[str, Any]:
    """Load and cache manifest.json."""
    global _manifest_cache

    if _manifest_cache is not None:
        return _manifest_cache

    manifest_path = _get_manifest_path()

    if not os.path.exists(manifest_path):
        logger.warning(f"Manifest not found: {manifest_path}")
        return {}

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            _manifest_cache = json.load(f)
        logger.debug(f"Loaded manifest from {manifest_path}")
        return _manifest_cache
    except Exception as e:
        logger.error(f"Failed to load manifest: {e}")
        return {}


def get_corpus_values() -> List[str]:
    """Get list of valid corpus IDs from manifest."""
    manifest = load_manifest()

    # Try fields.corpus.values first (schema 1.1+)
    fields = manifest.get("fields", {})
    corpus_field = fields.get("corpus", {})
    if corpus_field.get("type") == "enum" and "values" in corpus_field:
        return corpus_field["values"]

    # Fallback to stats.corpora keys
    stats = manifest.get("stats", {})
    corpora = stats.get("corpora", {})
    if corpora:
        return list(corpora.keys())

    return []


def generate_corpus_label(corpus_id: str) -> str:
    """Generate human-readable label from corpus ID.

    Parses patterns like '{year}_{country_code}' -> '{Country} ({year})'
    e.g., '1901_au' -> 'Australia (1901)'
    """
    if not corpus_id or corpus_id == "all":
        return "All Collections"

    # Try to parse {year}_{country_code} pattern
    parts = corpus_id.split("_")
    if len(parts) == 2:
        year, code = parts
        if year.isdigit() and code.lower() in COUNTRY_CODES:
            country = COUNTRY_CODES[code.lower()]
            return f"{country} ({year})"

    # Fallback: capitalize and replace underscores
    return corpus_id.replace("_", " ").title()


def get_corpus_options() -> List[Dict[str, str]]:
    """Generate corpus options with labels from manifest.

    Returns list of dicts with 'value' and 'label' keys,
    always including 'all' as first option.
    """
    corpus_values = get_corpus_values()

    # Always start with "all" option
    options = [{"value": "all", "label": "All Collections"}]

    # Add options for each corpus in manifest (skip "all" since it's already added)
    for corpus_id in corpus_values:
        if corpus_id == "all":
            continue
        options.append({
            "value": corpus_id,
            "label": generate_corpus_label(corpus_id)
        })

    return options


def invalidate_cache() -> None:
    """Clear the manifest cache. Useful for testing or after manifest updates."""
    global _manifest_cache
    _manifest_cache = None
