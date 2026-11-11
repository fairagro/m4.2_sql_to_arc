"""Ontology source name derivation and OntologySourceReference registry."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from arctrl import ArcInvestigation
from arctrl.py.Core.ontology_source_reference import OntologySourceReference

# OBO / OLS-style term IRIs: …/ENVO_00002001 or …/EFO_0000001 → ENVO / EFO
_OBO_TERM_ID = re.compile(
    r"(?:^|/)([A-Za-z][A-Za-z0-9]*)_(\d+)(?:\D|$)",
)


def derive_ontology_source_name(uri: str | None) -> str | None:
    """Return an ISA TermSourceREF short name from a term-accession URI, or None if unparseable.

    Recognises OBO/purl-style local ids (``PREFIX_digits``). Does not invent a name when the URI
    is missing or does not match.
    """
    if uri is None:
        return None
    stripped = uri.strip()
    if not stripped:
        return None
    match = _OBO_TERM_ID.search(stripped)
    if match is None:
        return None
    return match.group(1)


@dataclass
class OntologySourceRegistry:
    """Collect unique OntologySourceReference objects for one investigation build."""

    _by_key: dict[tuple[str, str], OntologySourceReference] = field(default_factory=dict)

    def register(self, name: str, version: str, *, file: str = "", description: str = "") -> None:
        """Register an OSR for ``(name, version)`` once (first wins)."""
        key = (name, version)
        if key in self._by_key:
            return
        self._by_key[key] = OntologySourceReference(
            name=name,
            version=version,
            file=file,
            description=description,
        )

    def __len__(self) -> int:
        """Return the number of unique registered OSRs."""
        return len(self._by_key)

    def apply_to_investigation(self, investigation: ArcInvestigation) -> None:
        """Append registered OSRs onto ``OntologySourceReferences`` (ARC / ArcInvestigation)."""
        for osr in self._by_key.values():
            investigation.OntologySourceReferences.append(osr)
