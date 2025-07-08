from __future__ import annotations

"""Hansard XML parsers (AU + UK).

Each parser yields *Speech* objects consisting of plain-text and a
metadata dictionary.  These are used by the new Chroma builder in
`create/xml/create_hansard_store.py`.

The contract is deliberately light-weight so that additional countries
or formats can be plugged in later by registering a new parser in
``PARSER_REGISTRY``.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Protocol
import re
import xml.etree.ElementTree as ET

__all__ = [
    "Speech",
    "BaseHansardParser",
    "AuHansardParser",
    "UkHansardParser",
    "NzHansardParser",
    "PARSER_REGISTRY",
]

# ---------------------------------------------------------------------------
# Generic speech container
# ---------------------------------------------------------------------------


@dataclass
class Speech:
    """Minimal unit fed to the downstream chunker/embeddings."""

    text: str
    metadata: Dict[str, str]

    def __post_init__(self) -> None:  # normalise whitespace
        self.text = re.sub(r"\s+", " ", self.text).strip()


# ---------------------------------------------------------------------------
# Base interface
# ---------------------------------------------------------------------------


class BaseHansardParser(Protocol):
    """Common interface for corpus-specific parsers."""

    corpus_id: str  #  e.g. "1901_au"

    def iter_speeches(self, xml_path: Path | str) -> Iterator[Speech]:
        """Yield Speech objects in the order they appear in the source."""
        ...


# ---------------------------------------------------------------------------
# AUSTRALIA – early Federation XML (REPS/SENATE etc.)
# ---------------------------------------------------------------------------


class AuHansardParser:
    """Parser for the Australian 1901 XML structure used earlier in the project."""

    corpus_id = "1901_au"

    # Pre-compile small helpers
    _TAG_RE = re.compile(r"<[^>]+>")

    def iter_speeches(self, xml_path: Path | str) -> Iterator[Speech]:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        ns = ""  # the AU XML doesn't use namespaces beyond xsi, which we ignore

        # Iterate over every <speech> element (child of <debate>)
        for speech_el in root.findall(".//speech"):
            text_parts: List[str] = []
            metadata: Dict[str, str] = {
                "corpus": self.corpus_id,
            }

            # speaker block is inside <talk.start>/<talker>
            talker = speech_el.find("talk.start/talker")
            if talker is not None:
                speaker_display = talker.findtext("name[@role='display']")
                electorate = talker.findtext("electorate")
                party = talker.findtext("party")
                if speaker_display:
                    metadata["speaker"] = speaker_display
                if electorate:
                    metadata["electorate"] = electorate
                if party:
                    metadata["party"] = party
                chamber_el = root.find("session.header/chamber")
                if chamber_el is not None:
                    metadata["chamber"] = chamber_el.text

            # debate metadata – walk up to nearest <debateinfo>
            debateinfo = speech_el.find("ancestor::debate/debateinfo")
            if debateinfo is not None:
                title = debateinfo.findtext("title")
                dtype = debateinfo.findtext("type")
                if title:
                    metadata["debate_title"] = title
                if dtype:
                    metadata["debate_type"] = dtype

            # date
            date_text = root.findtext("session.header/date")
            if date_text:
                metadata["date"] = date_text  # already ISO YYYY-MM-DD
                try:
                    year = datetime.strptime(date_text, "%Y-%m-%d").year
                    metadata["decade"] = f"{year//10*10}s"
                except Exception:
                    pass

            # Collect <para> descendants under this speech
            for para in speech_el.findall(".//para"):
                para_text = ET.tostring(para, encoding="unicode", method="text")
                text_parts.append(para_text)

            full_text = "\n".join(text_parts)
            # Very small speeches are rarely useful; skip (<30 chars)
            if len(full_text.strip()) < 30:
                continue

            yield Speech(text=full_text, metadata=metadata)


# ---------------------------------------------------------------------------
# UNITED KINGDOM – Commons / Lords merged XML volumes
# ---------------------------------------------------------------------------


class UkHansardParser:
    """Parser for UK volumes that contain many sitting days across Commons/Lords."""

    corpus_id = "1901_uk"

    _SPEAKER_LINE_RE = re.compile(r"^[A-Z][A-Z .'\-]+ \([^)]+\)\.")

    def iter_speeches(self, xml_path: Path | str) -> Iterator[Speech]:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Each <section> is roughly a sitting-day booklet
        for section in root.findall("section"):
            # date is inside <date> tag (machine readable)
            date_val: Optional[str] = section.findtext(".//date[@format]")
            if date_val is None:
                # fallback: try to parse from title
                title_txt = section.findtext("title") or ""
                m = re.search(r"(\d{1,2}(st|nd|rd|th)? [A-Za-z]+,? (18|19)\d{2})", title_txt)
                if m:
                    try:
                        date_val = datetime.strptime(m.group(1), "%d %B %Y").strftime("%Y-%m-%d")
                    except Exception:
                        date_val = None

            chamber: Optional[str] = None
            if section.find("housecommons") is not None:
                chamber = "Commons"
                content_parent = section.find("housecommons")
            elif section.find("houselords") is not None:
                chamber = "Lords"
                content_parent = section.find("houselords")
            else:
                content_parent = section  # fallback

            # Debate title
            debate_title = section.findtext("title")

            # Paragraph-wise iteration; UK XML stores text mostly in <p>
            buffer: List[str] = []
            current_speaker: Optional[str] = None
            for p in content_parent.findall(".//p"):
                raw = ET.tostring(p, encoding="unicode", method="text")
                raw = raw.strip()
                if not raw:
                    continue

                # detect speaker lines (all caps until first ".")
                if self._SPEAKER_LINE_RE.match(raw):
                    # flush previous buffer
                    if buffer:
                        yield Speech(
                            text="\n".join(buffer),
                            metadata=self._make_metadata(current_speaker, chamber, date_val, debate_title),
                        )
                        buffer = []
                    current_speaker = raw.split(".")[0].title()
                    buffer.append(raw)
                else:
                    buffer.append(raw)

            if buffer:
                # flush trailing buffer
                yield Speech(
                    text="\n".join(buffer),
                    metadata=self._make_metadata(current_speaker, chamber, date_val, debate_title),
                )

    # ---------------------------------------------------------------------
    # helpers
    # ---------------------------------------------------------------------

    @staticmethod
    def _make_metadata(
        speaker: Optional[str], chamber: Optional[str], date_val: Optional[str], title: Optional[str]
    ) -> Dict[str, str]:
        md: Dict[str, str] = {"corpus": "1901_uk"}
        if speaker:
            md["speaker"] = speaker
        if chamber:
            md["chamber"] = chamber
        if date_val:
            md["date"] = date_val
            try:
                year = datetime.strptime(date_val, "%Y-%m-%d").year
                md["decade"] = f"{year//10*10}s"
            except Exception:
                pass
        if title:
            md["debate_title"] = title
        return md


# ---------------------------------------------------------------------------
# NEW ZEALAND – plain-text Hansard files (minimal metadata)
# ---------------------------------------------------------------------------


class NzHansardParser:
    """Parser for the unstructured NZ Hansard plain-text transcriptions.

    Extraction heuristics:
        • Date is taken from file name e.g. "Friday, 12th July, 1901.txt" → 1901-07-12
        • Speaker lines are ALL-CAPS and end with a period ("MR SEDDON.")
          – If detection fails we assign speaker="UNKNOWN" and continue.
    """

    corpus_id = "1901_nz"

    _DATE_RE = re.compile(r"(\d{1,2})(?:st|nd|rd|th)? ([A-Za-z]+) (\d{4})")
    _SPEAKER_LINE_RE = re.compile(r"^[A-Z][A-Z .'\-]+\.")

    _MONTHS = {
        m.lower(): i for i, m in enumerate(
            [
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ],
            start=1,
        )
    }

    def iter_speeches(self, txt_path: str | Path) -> Iterator[Speech]:
        txt_path = Path(txt_path)
        raw_text = txt_path.read_text(encoding="utf-8", errors="ignore")

        # Build base metadata
        metadata: Dict[str, str] = {"corpus": self.corpus_id}

        # Date from filename
        m = self._DATE_RE.search(txt_path.stem)
        if m:
            day, month_name, year = m.groups()
            month_num = self._MONTHS.get(month_name.lower())
            if month_num:
                metadata["date"] = f"{year}-{month_num:02d}-{int(day):02d}"
                metadata["decade"] = f"{int(year)//10*10}s"

        # Session info from parent directory name (e.g. "1.July01-July26-1901")
        session_dir = txt_path.parent.name
        metadata["session_range"] = session_dir

        # Iterate over lines, detect speakers
        buffer: List[str] = []
        current_speaker = None

        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue

            if self._SPEAKER_LINE_RE.match(line):
                # flush previous buffer
                if buffer:
                    yield Speech(text="\n".join(buffer), metadata=self._make_md(metadata, current_speaker))
                    buffer = []
                current_speaker = line.rstrip(".")  # remove trailing period
                buffer.append(line)
            else:
                buffer.append(line)

        if buffer:
            yield Speech(text="\n".join(buffer), metadata=self._make_md(metadata, current_speaker))

    @staticmethod
    def _make_md(base: Dict[str, str], speaker: Optional[str]) -> Dict[str, str]:
        md = dict(base)
        if speaker:
            md["speaker"] = speaker.title()
        return md


# ---------------------------------------------------------------------------
# Registry helper
# ---------------------------------------------------------------------------

PARSER_REGISTRY: Dict[str, BaseHansardParser] = {
    AuHansardParser.corpus_id: AuHansardParser(),
    UkHansardParser.corpus_id: UkHansardParser(),
    NzHansardParser.corpus_id: NzHansardParser(),
} 