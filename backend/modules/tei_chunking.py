"""
TEI-XML chunking strategies for ATLAS corpus wizard.

Provides two chunking modes for TEI-XML documents:
1. Structural chunking: splits on TEI structural elements (div, p)
2. Whole-document chunking: one chunk per TEI document

Both modes prepend extracted metadata to chunk text so the LLM
receives contextual information alongside content.
"""

import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    from langchain.schema import Document
except ImportError:
    from langchain_core.documents import Document

from backend.modules.tei_xml_parser import parse_tei_document

logger = logging.getLogger(__name__)


def _build_metadata_prefix(metadata: Dict[str, Any]) -> str:
    """Build a structured metadata prefix to prepend to chunk text.

    Format:
        [Metadata]
        Sender: Charles Robert Darwin
        Recipient: Joseph Dalton Hooker
        Date: 1859-03-15
        Place: Down
        Keywords: natural selection; species theory
        Abstract: Discussion of species distribution...
        [/Metadata]
    """
    lines = ["[Metadata]"]

    field_labels = [
        ("tei_sender", "Sender"),
        ("tei_recipient", "Recipient"),
        ("tei_date", "Date"),
        ("tei_place", "Place"),
        ("tei_keywords", "Keywords"),
        ("tei_abstract", "Abstract"),
        ("tei_title", "Title"),
    ]

    for field, label in field_labels:
        value = metadata.get(field)
        if value:
            lines.append(f"{label}: {value}")

    lines.append("[/Metadata]")

    # Only return prefix if there's actual metadata (more than just delimiters)
    if len(lines) <= 2:
        return ""

    return "\n".join(lines)


def _generate_chunk_id(corpus_name: str, filename: str, chunk_index: int) -> str:
    """Generate a deterministic chunk ID."""
    raw = f"{corpus_name}:{filename}:{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def chunk_tei_document(
    parsed: Dict[str, Any],
    strategy: str = "whole_document",
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
    corpus_name: str = "",
    filter_id: str = "",
    filter_label: str = "",
    metadata_mappings: Optional[Dict[str, str]] = None,
) -> List[Document]:
    """Chunk a parsed TEI document into LangChain Documents.

    Args:
        parsed: Output from parse_tei_document()
        strategy: "whole_document" or "structural"
        chunk_size: Target chunk size in characters (structural only)
        chunk_overlap: Overlap between chunks (structural only)
        corpus_name: Corpus name for metadata
        filter_id: Filter ID for metadata (populates filter_1)
        filter_label: Filter label for metadata
        metadata_mappings: Optional dict mapping TEI fields to custom roles

    Returns:
        List of LangChain Document objects with metadata
    """
    if strategy == "whole_document":
        return _chunk_whole_document(
            parsed, corpus_name, filter_id, filter_label, metadata_mappings
        )
    elif strategy == "structural":
        return _chunk_structural(
            parsed, chunk_size, chunk_overlap,
            corpus_name, filter_id, filter_label, metadata_mappings
        )
    else:
        raise ValueError(f"Unknown chunking strategy: {strategy}")


def _build_chunk_metadata(
    parsed: Dict[str, Any],
    chunk_index: int,
    corpus_name: str,
    filter_id: str,
    filter_label: str,
    metadata_mappings: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Build metadata dict for a chunk, including TEI fields and backward-compat fields."""
    tei_meta = parsed["metadata"]
    filename = Path(parsed["file_path"]).name

    chunk_id = _generate_chunk_id(corpus_name, filename, chunk_index)

    meta = {
        "chunk_id": chunk_id,
        "source_filename": filename,
        "source": parsed["file_path"],
    }

    # Corpus / filter metadata (backward-compat with existing pipeline)
    if corpus_name:
        meta["corpus"] = corpus_name
    if filter_id:
        meta["filter_1"] = filter_id
        meta["corpus"] = filter_id  # Legacy compatibility
    if filter_label:
        meta["corpus_label"] = filter_label

    # Copy all TEI metadata fields
    for key, value in tei_meta.items():
        meta[key] = value

    # Backward compatibility: populate filter_1/filter_2 from TEI fields if not set
    if "filter_1" not in meta and "tei_sender" in tei_meta:
        meta["filter_1"] = tei_meta["tei_sender"]
    if "filter_2" not in meta and "tei_recipient" in tei_meta:
        meta["filter_2"] = tei_meta["tei_recipient"]

    # Standard date field from TEI date
    if "date" not in meta and "tei_date" in tei_meta:
        meta["date"] = tei_meta["tei_date"]

    # Apply custom metadata mappings if provided
    if metadata_mappings:
        for tei_field, target_role in metadata_mappings.items():
            if tei_field in tei_meta:
                meta[target_role] = tei_meta[tei_field]

    return meta


def _chunk_whole_document(
    parsed: Dict[str, Any],
    corpus_name: str,
    filter_id: str,
    filter_label: str,
    metadata_mappings: Optional[Dict[str, str]] = None,
) -> List[Document]:
    """Create a single chunk from the entire TEI document."""
    body_text = parsed.get("body_text", "")
    if not body_text:
        logger.warning(f"No body text found in {parsed.get('file_path', 'unknown')}")
        return []

    # Build metadata prefix
    prefix = _build_metadata_prefix(parsed["metadata"])
    if prefix:
        page_content = f"{prefix}\n\n[Content]\n{body_text}\n[/Content]"
    else:
        page_content = body_text

    meta = _build_chunk_metadata(
        parsed, 0, corpus_name, filter_id, filter_label, metadata_mappings
    )

    return [Document(page_content=page_content, metadata=meta)]


def _chunk_structural(
    parsed: Dict[str, Any],
    chunk_size: int,
    chunk_overlap: int,
    corpus_name: str,
    filter_id: str,
    filter_label: str,
    metadata_mappings: Optional[Dict[str, str]] = None,
) -> List[Document]:
    """Split TEI document at structural boundaries, merging small sections."""
    sections = parsed.get("body_sections", [])

    if not sections:
        # Fall back to whole-document if no structural sections found
        return _chunk_whole_document(
            parsed, corpus_name, filter_id, filter_label, metadata_mappings
        )

    # Build metadata prefix (same for all chunks from this document)
    prefix = _build_metadata_prefix(parsed["metadata"])

    # Merge small adjacent sections up to chunk_size
    merged_texts = _merge_sections(sections, chunk_size, chunk_overlap)

    documents = []
    for idx, text in enumerate(merged_texts):
        if prefix:
            page_content = f"{prefix}\n\n[Content]\n{text}\n[/Content]"
        else:
            page_content = text

        meta = _build_chunk_metadata(
            parsed, idx, corpus_name, filter_id, filter_label, metadata_mappings
        )

        documents.append(Document(page_content=page_content, metadata=meta))

    return documents


def _merge_sections(
    sections: List[Dict[str, str]], chunk_size: int, chunk_overlap: int
) -> List[str]:
    """Merge small adjacent sections into chunks up to chunk_size.

    Returns a list of text strings, each representing a merged chunk.
    """
    if not sections:
        return []

    merged = []
    current_parts: List[str] = []
    current_len = 0

    for section in sections:
        text = section["text"]
        text_len = len(text)

        if current_len + text_len > chunk_size and current_parts:
            # Flush current chunk
            merged.append("\n\n".join(current_parts))

            # Keep overlap: take from the end of the current parts
            if chunk_overlap > 0:
                overlap_text = current_parts[-1]
                if len(overlap_text) > chunk_overlap:
                    overlap_text = overlap_text[-chunk_overlap:]
                current_parts = [overlap_text]
                current_len = len(overlap_text)
            else:
                current_parts = []
                current_len = 0

        current_parts.append(text)
        current_len += text_len

    # Flush remaining
    if current_parts:
        merged.append("\n\n".join(current_parts))

    return merged


def chunk_tei_corpus(
    directory: Path,
    strategy: str = "whole_document",
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
    corpus_name: str = "",
    filter_id: str = "",
    filter_label: str = "",
    metadata_mappings: Optional[Dict[str, str]] = None,
    selected_fields: Optional[List[str]] = None,
) -> List[Document]:
    """Chunk all TEI-XML files in a directory.

    Args:
        directory: Directory containing TEI-XML files
        strategy: Chunking strategy
        chunk_size: Target chunk size
        chunk_overlap: Chunk overlap
        corpus_name: Corpus name for metadata
        filter_id: Filter ID for metadata
        filter_label: Filter label
        metadata_mappings: Custom field mappings
        selected_fields: If set, only include these TEI fields in metadata

    Returns:
        List of all Document chunks from all files
    """
    from backend.modules.tei_xml_parser import is_tei_xml

    xml_files = sorted(directory.rglob("*.xml"))
    tei_files = [f for f in xml_files if is_tei_xml(f)]

    all_docs: List[Document] = []
    errors: List[str] = []

    for fpath in tei_files:
        try:
            parsed = parse_tei_document(fpath)

            # Filter to selected fields if specified
            if selected_fields:
                filtered_meta = {}
                for key, value in parsed["metadata"].items():
                    if key in selected_fields:
                        filtered_meta[key] = value
                parsed["metadata"] = filtered_meta

            chunks = chunk_tei_document(
                parsed,
                strategy=strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                corpus_name=corpus_name,
                filter_id=filter_id,
                filter_label=filter_label,
                metadata_mappings=metadata_mappings,
            )
            all_docs.extend(chunks)
        except ValueError as e:
            errors.append(str(e))
            logger.warning(f"Skipping malformed file: {e}")
        except Exception as e:
            errors.append(f"Error processing {fpath}: {e}")
            logger.error(f"Error processing TEI file {fpath}: {e}")

    logger.info(
        f"Chunked {len(tei_files)} TEI files into {len(all_docs)} chunks "
        f"({len(errors)} errors)"
    )

    return all_docs
