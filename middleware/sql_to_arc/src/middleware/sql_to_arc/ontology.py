"""Ontology source name derivation and OntologySourceReference registry."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from arctrl import ArcInvestigation, OntologyAnnotation
from arctrl.py.Core.ontology_source_reference import OntologySourceReference

# Final path segment: OBO-style PREFIX_digits (PREFIX is uppercase, e.g. ENVO_00002001).
_OBO_TERM_SEGMENT = re.compile(r"^([A-Z][A-Z0-9]*)_(\d+)$")


def derive_ontology_source_name(uri: str | None) -> str | None:
    """Return an ISA TermSourceREF short name from a term-accession URI, or None if unparseable.

    Recognises an uppercase OBO/purl-style local id as the final path segment
    (``…/ENVO_00002001`` → ``ENVO``). Does not invent a name when the URI is missing or does not
    match (including lowercase ``user_123``-style segments).
    """
    if uri is None:
        return None
    stripped = uri.strip()
    if not stripped:
        return None
    path = urlsplit(stripped).path.rstrip("/")
    segment = path.rsplit("/", 1)[-1]
    match = _OBO_TERM_SEGMENT.fullmatch(segment)
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


def make_ontology_annotation(
    term: str | None,
    uri: str | None,
    version: str | None,
    registry: OntologySourceRegistry | None = None,
) -> OntologyAnnotation:
    """Map a view ontology triple to OntologyAnnotation; optionally register an OSR.

    Does not invent terms or URIs when absent. TermSourceREF is set only when a source
    short name can be derived from the URI. An OntologySourceReference is registered
    when both a derived source name and a non-empty version are present.
    """
    if not term:
        return OntologyAnnotation()

    source = derive_ontology_source_name(uri)
    if registry is not None and source is not None and version and version.strip():
        registry.register(source, version.strip())

    if source is not None:
        return OntologyAnnotation(name=term, tan=uri or "", tsr=source)
    return OntologyAnnotation(name=term, tan=uri or "")
