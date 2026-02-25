"""
TEI-XML parser for ATLAS corpus wizard.

Namespace-aware parser using lxml that extracts structured metadata
from TEI P5 documents. Corpus-agnostic: discovers available elements
at analysis time rather than hardcoding field names.

Security: Parses with XXE protection (no external entity resolution,
no network access).
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

from lxml import etree

logger = logging.getLogger(__name__)

# TEI P5 namespace
TEI_NS = "http://www.tei-c.org/ns/1.0"
TEI_NSMAP = {"tei": TEI_NS}


def _safe_parser() -> etree.XMLParser:
    """Create an XML parser with XXE protection."""
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        dtd_validation=False,
        load_dtd=False,
        remove_comments=True,
    )


def _xpath(element: etree._Element, expr: str) -> List[etree._Element]:
    """Run XPath with TEI namespace. Falls back to no-namespace if needed."""
    result = element.xpath(expr, namespaces=TEI_NSMAP)
    if not result:
        # Try without namespace for unnamespaced TEI documents
        no_ns_expr = expr.replace("tei:", "")
        result = element.xpath(no_ns_expr)
    return result


def _text(element: Optional[etree._Element]) -> Optional[str]:
    """Extract cleaned text from an element, or None if absent."""
    if element is None:
        return None
    # Get all text content including tail of children
    text = element.text or ""
    for child in element:
        if child.text:
            text += child.text
        if child.tail:
            text += child.tail
    text = text.strip()
    return text if text else None


def _deep_text(element: Optional[etree._Element]) -> Optional[str]:
    """Extract all nested text content, stripping tags."""
    if element is None:
        return None
    text = etree.tostring(element, method="text", encoding="unicode")
    # Normalise whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else None


def is_tei_xml(file_path: Path) -> bool:
    """Check if a file is a TEI-XML document.

    Looks for <TEI> root element or TEI namespace declaration.
    Uses fast partial parsing — reads only the first few KB.
    """
    try:
        # Read first 2KB for quick detection
        with open(file_path, "rb") as f:
            head = f.read(2048)

        if b"http://www.tei-c.org/ns/1.0" in head:
            return True
        if b"<TEI " in head or b"<TEI>" in head:
            return True
        return False
    except Exception:
        return False


def parse_tei_document(file_path: Path) -> Dict[str, Any]:
    """Parse a single TEI-XML document, extracting metadata and body text.

    Returns a dictionary with:
        - metadata: dict of extracted metadata fields (only non-empty)
        - body_text: cleaned body text (tags stripped)
        - body_sections: list of structural sections (div/p) with text
        - file_path: original file path

    Missing fields are omitted (no null values or empty strings).
    """
    parser = _safe_parser()

    try:
        tree = etree.parse(str(file_path), parser)
    except etree.XMLSyntaxError as e:
        raise ValueError(f"Malformed XML in {file_path}: {e}") from e

    root = tree.getroot()
    metadata = {}

    # --- teiHeader extraction ---
    _extract_corresp_desc(root, metadata)
    _extract_abstract(root, metadata)
    _extract_keywords(root, metadata)
    _extract_title(root, metadata)
    _extract_source_desc(root, metadata)

    # --- Body text extraction ---
    body_text = _extract_body_text(root)
    body_sections = _extract_body_sections(root)

    result = {
        "metadata": metadata,
        "body_text": body_text,
        "body_sections": body_sections,
        "file_path": str(file_path),
    }
    return result


def _extract_corresp_desc(root: etree._Element, metadata: Dict[str, Any]) -> None:
    """Extract correspondence metadata: sender, recipient, date, place."""
    # Sent action
    sent_actions = _xpath(root, ".//tei:correspDesc/tei:correspAction[@type='sent']")
    if sent_actions:
        sent = sent_actions[0]
        sender_els = _xpath(sent, "tei:persName")
        if sender_els:
            sender = _deep_text(sender_els[0])
            if sender:
                metadata["tei_sender"] = sender

        place_els = _xpath(sent, "tei:placeName")
        if place_els:
            place = _deep_text(place_els[0])
            if place and place.lower() != "unstated":
                metadata["tei_place"] = place

        date_els = _xpath(sent, "tei:date")
        if date_els:
            # Prefer @when attribute (ISO format)
            when = date_els[0].get("when")
            if when:
                metadata["tei_date"] = when
            else:
                # Fall back to text content
                date_text = _deep_text(date_els[0])
                if date_text:
                    metadata["tei_date"] = date_text

    # Received action
    recv_actions = _xpath(root, ".//tei:correspDesc/tei:correspAction[@type='received']")
    if recv_actions:
        recv = recv_actions[0]
        recip_els = _xpath(recv, "tei:persName")
        if recip_els:
            recipient = _deep_text(recip_els[0])
            if recipient:
                metadata["tei_recipient"] = recipient


def _extract_abstract(root: etree._Element, metadata: Dict[str, Any]) -> None:
    """Extract abstract from profileDesc."""
    abstract_els = _xpath(root, ".//tei:profileDesc/tei:abstract")
    if abstract_els:
        abstract = _deep_text(abstract_els[0])
        if abstract:
            metadata["tei_abstract"] = abstract


def _extract_keywords(root: etree._Element, metadata: Dict[str, Any]) -> None:
    """Extract keywords from textClass."""
    term_els = _xpath(root, ".//tei:profileDesc/tei:textClass/tei:keywords/tei:term")
    if term_els:
        keywords = []
        for term in term_els:
            text = _deep_text(term)
            if text:
                keywords.append(text)
        if keywords:
            metadata["tei_keywords"] = "; ".join(keywords)


def _extract_title(root: etree._Element, metadata: Dict[str, Any]) -> None:
    """Extract title from titleStmt."""
    title_els = _xpath(root, ".//tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title")
    if title_els:
        title = _deep_text(title_els[0])
        if title:
            metadata["tei_title"] = title


def _extract_source_desc(root: etree._Element, metadata: Dict[str, Any]) -> None:
    """Extract source/provenance from sourceDesc."""
    # Repository
    repo_els = _xpath(root, ".//tei:sourceDesc/tei:msDesc/tei:msIdentifier/tei:repository")
    if repo_els:
        repo = _deep_text(repo_els[0])
        if repo:
            metadata["tei_repository"] = repo

    # Collection + ID
    idno_els = _xpath(root, ".//tei:sourceDesc/tei:msDesc/tei:msIdentifier/tei:idno")
    if idno_els:
        idno = _deep_text(idno_els[0])
        if idno:
            metadata["tei_source_id"] = idno


def _extract_body_text(root: etree._Element) -> str:
    """Extract all text from the body, stripping XML tags.

    Extracts only the transcription content — excludes footnotes,
    annotations, and editorial notes.
    """
    # Try to find the transcription div first
    transcription_divs = _xpath(root, ".//tei:text/tei:body//tei:div[@type='transcription']")
    if transcription_divs:
        parts = []
        for div in transcription_divs:
            text = _deep_text(div)
            if text:
                parts.append(text)
        if parts:
            return "\n\n".join(parts)

    # Fall back to the letter div (excluding footnotes)
    letter_divs = _xpath(root, ".//tei:text/tei:body/tei:div[@type='letter']")
    if letter_divs:
        parts = []
        for div in letter_divs:
            # Get text div children, skip footnotes/annotations
            text_divs = _xpath(div, "tei:div[@type='text']")
            for td in text_divs:
                text = _deep_text(td)
                if text:
                    parts.append(text)
        if parts:
            return "\n\n".join(parts)

    # Fall back to entire body
    body_els = _xpath(root, ".//tei:text/tei:body")
    if body_els:
        text = _deep_text(body_els[0])
        return text or ""

    return ""


def _extract_body_sections(root: etree._Element) -> List[Dict[str, str]]:
    """Extract structural sections from the body for structural chunking.

    Returns a list of dicts with 'type' and 'text' keys, representing
    div and paragraph boundaries.
    """
    sections = []

    # Look for structural divs in the body
    body_els = _xpath(root, ".//tei:text/tei:body")
    if not body_els:
        return sections

    body = body_els[0]
    _collect_sections(body, sections)
    return sections


def _collect_sections(element: etree._Element, sections: List[Dict[str, str]]) -> None:
    """Recursively collect text sections from structural elements."""
    tag = etree.QName(element.tag).localname if isinstance(element.tag, str) else ""

    # Skip footnotes, annotations, and editorial notes
    div_type = element.get("type", "")
    if div_type in ("footnotes", "annotations", "tnotes"):
        return

    if tag == "p":
        text = _deep_text(element)
        if text:
            sections.append({"type": "paragraph", "text": text})
        return

    if tag == "div":
        # Check if this div has any structural children (p or div)
        has_structural_children = False
        for child in element:
            if isinstance(child.tag, str):
                child_tag = etree.QName(child.tag).localname
                if child_tag in ("p", "div"):
                    has_structural_children = True
                    break

        if has_structural_children:
            # Recurse into children
            for child in element:
                if isinstance(child.tag, str):
                    _collect_sections(child, sections)
        else:
            # Leaf div — extract its text as a section
            text = _deep_text(element)
            if text:
                sections.append({"type": f"div:{div_type}" if div_type else "div", "text": text})
            return

    # For other elements, recurse
    for child in element:
        if isinstance(child.tag, str):
            _collect_sections(child, sections)


def discover_tei_schema(
    directory: Path, sample_size: int = 20
) -> Dict[str, Any]:
    """Discover available TEI metadata elements by sampling files.

    Scans up to sample_size files to identify which teiHeader elements
    are present and how frequently they appear.

    Returns:
        Dictionary with:
            - total_files: count of TEI-XML files found
            - sample_size: files actually sampled
            - elements: dict mapping element paths to their coverage
              (count, percentage, sample_values)
    """
    xml_files = sorted(directory.rglob("*.xml"))

    # Filter to TEI files
    tei_files = [f for f in xml_files if is_tei_xml(f)]
    total_tei = len(tei_files)

    if total_tei == 0:
        return {
            "total_files": len(xml_files),
            "tei_files": 0,
            "sample_size": 0,
            "elements": {},
        }

    # Sample
    actual_sample = min(sample_size, total_tei)
    # Evenly space samples across the sorted list
    if actual_sample < total_tei:
        step = total_tei / actual_sample
        sampled = [tei_files[int(i * step)] for i in range(actual_sample)]
    else:
        sampled = tei_files

    # Track element presence and sample values
    element_counts: Dict[str, int] = {}
    element_values: Dict[str, Set[str]] = {}

    # Elements we look for (paths relative to root)
    check_paths = {
        "correspDesc/sender": ".//tei:correspDesc/tei:correspAction[@type='sent']/tei:persName",
        "correspDesc/recipient": ".//tei:correspDesc/tei:correspAction[@type='received']/tei:persName",
        "correspDesc/date": ".//tei:correspDesc/tei:correspAction[@type='sent']/tei:date",
        "correspDesc/place": ".//tei:correspDesc/tei:correspAction[@type='sent']/tei:placeName",
        "abstract": ".//tei:profileDesc/tei:abstract",
        "keywords": ".//tei:profileDesc/tei:textClass/tei:keywords/tei:term",
        "title": ".//tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title",
        "repository": ".//tei:sourceDesc/tei:msDesc/tei:msIdentifier/tei:repository",
        "sourceId": ".//tei:sourceDesc/tei:msDesc/tei:msIdentifier/tei:idno",
    }

    for fpath in sampled:
        try:
            tree = etree.parse(str(fpath), _safe_parser())
            root = tree.getroot()

            for elem_name, xpath_expr in check_paths.items():
                matches = _xpath(root, xpath_expr)
                if matches:
                    element_counts[elem_name] = element_counts.get(elem_name, 0) + 1
                    # Collect sample values (up to 10)
                    if elem_name not in element_values:
                        element_values[elem_name] = set()
                    for m in matches[:3]:
                        val = _deep_text(m)
                        if val and len(element_values[elem_name]) < 10:
                            element_values[elem_name].add(val[:80])

        except Exception as e:
            logger.warning(f"Error sampling TEI file {fpath}: {e}")

    # Build result
    elements = {}
    for elem_name in check_paths:
        count = element_counts.get(elem_name, 0)
        elements[elem_name] = {
            "count": count,
            "percentage": round(100 * count / actual_sample, 1) if actual_sample > 0 else 0,
            "sample_values": sorted(element_values.get(elem_name, set()))[:5],
        }

    return {
        "total_files": len(xml_files),
        "tei_files": total_tei,
        "sample_size": actual_sample,
        "elements": elements,
    }
