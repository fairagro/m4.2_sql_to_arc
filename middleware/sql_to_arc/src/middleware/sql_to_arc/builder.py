"""ARC object building logic for the SQL-to-ARC conversion process."""

import gc
import json
import logging
from collections import defaultdict
from typing import Any, cast

from arctrl import (  # type: ignore[import-untyped]
    ARC,
    ArcAssay,
    ArcStudy,
    ArcTable,
    CompositeCell,
    CompositeHeader,
    IOType,
    OntologyAnnotation,
)

from middleware.sql_to_arc.context import ArcBuildData
from middleware.sql_to_arc.mapper import (
    map_assay,
    map_contact,
    map_investigation,
    map_publication,
    map_study,
)
from middleware.sql_to_arc.models import (
    AssayRow,
    ContactRow,
    PublicationRow,
    StudyRow,
)

logger = logging.getLogger(__name__)


def _add_studies_to_arc(arc: ARC, study_rows: list[StudyRow]) -> dict[str, ArcStudy]:
    """Add studies to ARC and return study map."""
    study_map: dict[str, ArcStudy] = {}
    for s_row in study_rows:
        study = map_study(s_row)
        arc.AddRegisteredStudy(study)
        study_map[str(s_row.identifier)] = study
    return study_map


def _add_assays_to_arc(arc: ARC, assay_rows: list[AssayRow], study_map: dict[str, ArcStudy]) -> dict[str, ArcAssay]:
    """Add assays to ARC, link to studies, and return assay map."""
    assay_map: dict[str, ArcAssay] = {}
    for a_row in assay_rows:
        assay = map_assay(a_row)
        arc.AddAssay(assay)
        assay_map[str(a_row.identifier)] = assay

        # Link Assay to Studies
        _link_assay_to_studies(assay, a_row.study_ref, study_map)

    return assay_map


def _link_assay_to_studies(assay: ArcAssay, study_ref_val: Any, study_map: dict[str, ArcStudy]) -> None:
    """Link an assay to one or more studies based on the study_ref value."""
    if not study_ref_val:
        return

    if isinstance(study_ref_val, str):
        try:
            study_refs = json.loads(study_ref_val)
            if isinstance(study_refs, list):
                for s_ref in study_refs:
                    if str(s_ref) in study_map:
                        study_map[str(s_ref)].RegisterAssay(assay.Identifier)
                return
        except json.JSONDecodeError:
            # Handle single ID if it's not JSON (fall through)
            pass

    # Handle single ID (string or int)
    if str(study_ref_val) in study_map:
        study_map[str(study_ref_val)].RegisterAssay(assay.Identifier)


def _add_contacts_to_arc(
    arc: ARC,
    inv_id: str,
    contacts: list[ContactRow],
    study_map: dict[str, ArcStudy],
    assay_map: dict[str, ArcAssay],
) -> None:
    """Add contacts to investigation, studies, and assays."""
    # Investigation contacts
    inv_contacts = [
        c for c in contacts if str(c.investigation_ref) == inv_id and getattr(c, "target_type", None) == "investigation"
    ]
    for c_row in inv_contacts:
        arc.Contacts.append(map_contact(c_row))

    # Study contacts
    for s_id, study in study_map.items():
        stu_contacts = [
            c
            for c in contacts
            if str(c.investigation_ref) == inv_id
            and getattr(c, "target_type", None) == "study"
            and str(getattr(c, "target_ref", None)) == s_id
        ]
        for c_row in stu_contacts:
            study.Contacts.append(map_contact(c_row))

    # Assay contacts
    for a_id, assay in assay_map.items():
        ass_contacts = [
            c
            for c in contacts
            if str(c.investigation_ref) == inv_id
            and getattr(c, "target_type", None) == "assay"
            and str(getattr(c, "target_ref", None)) == a_id
        ]
        for c_row in ass_contacts:
            assay.Performers.append(map_contact(c_row))


def _add_publications_to_arc(
    arc: ARC,
    inv_id: str,
    publications: list[PublicationRow],
    study_map: dict[str, ArcStudy],
) -> None:
    """Add publications to investigation and studies."""
    # Investigation publications
    inv_pubs = [
        p
        for p in publications
        if str(p.investigation_ref) == inv_id and getattr(p, "target_type", None) == "investigation"
    ]
    for p_row in inv_pubs:
        arc.Publications.append(map_publication(p_row))

    # Study publications
    for s_id, study in study_map.items():
        stu_pubs = [
            p
            for p in publications
            if str(p.investigation_ref) == inv_id
            and getattr(p, "target_type", None) == "study"
            and str(getattr(p, "target_ref", None)) == s_id
        ]
        for p_row in stu_pubs:
            study.Publications.append(map_publication(p_row))


def _get_column_key(r: dict[str, Any]) -> tuple:
    """Extract a unique key for a column definition."""
    return (
        r.get("column_type"),
        r.get("column_io_type"),
        r.get("column_value"),
        r.get("column_annotation_term"),
        r.get("column_annotation_uri"),
        r.get("column_annotation_version"),
        r.get("column_name"),  # Fallback for simple tests
    )


def _build_header(key: tuple) -> CompositeHeader | None:
    """Build a CompositeHeader from a column key tuple."""
    c_type, c_io, c_val, c_ann_term, c_ann_uri, c_ann_ver, c_name = key
    try:
        oa = OntologyAnnotation(c_ann_term or "", c_ann_uri or "", c_ann_ver or "")

        # Dispatch table for different header types
        handlers = {
            "input": lambda: CompositeHeader.input(IOType.of_string(c_io or "source_name")),
            "output": lambda: CompositeHeader.output(IOType.of_string(c_io or "sample_name")),
            "characteristic": lambda: CompositeHeader.characteristic(oa),
            "factor": lambda: CompositeHeader.factor(oa),
            "parameter": lambda: CompositeHeader.parameter(oa),
            "component": lambda: CompositeHeader.component(oa),
            "comment": lambda: CompositeHeader.comment(c_val or ""),
            "performer": CompositeHeader.performer,
            "date": CompositeHeader.date,
        }

        if c_type in handlers:
            return handlers[c_type]()
        if c_name:
            # Fallback for simple/untyped headers
            return CompositeHeader.OfHeaderString(c_name)

    except (ValueError, TypeError, AttributeError) as e:
        logger.warning("Failed to create header for type %s: %s", c_type, e)
    return None


def _build_single_cell(cell_row: dict[str, Any], header: CompositeHeader) -> CompositeCell:
    """Build a single CompositeCell from a database row."""
    cv = cell_row.get("cell_value")
    cat = cell_row.get("cell_annotation_term")
    cau = cell_row.get("cell_annotation_uri") or ""
    cav = cell_row.get("cell_annotation_version") or ""
    v = cell_row.get("value")  # Fallback for old/simple tests

    # Unitized cell (value + ontology term)
    if cv is not None and cat is not None:
        return CompositeCell.unitized(str(cv), OntologyAnnotation(cat, cau, cav))

    # Term cell (ontology term only)
    if cat is not None:
        return CompositeCell.term(OntologyAnnotation(cat, cau, cav))

    # Text value? (either from new schema 'cell_value' or fallback 'value')
    val_to_use = cv if cv is not None else v
    if val_to_use is not None:
        if header.IsTermColumn:
            # If the column expects a term, wrap the text in an annotation
            return CompositeCell.term(OntologyAnnotation(str(val_to_use), "", ""))
        return CompositeCell.free_text(str(val_to_use))

    return CompositeCell.free_text("")


def _build_column_cells(
    rows_map: dict[int, dict[str, Any]], max_row_idx: int, header: CompositeHeader
) -> list[CompositeCell]:
    """Build a list of CompositeCell objects for a column."""
    col_cells = []
    for idx in range(max_row_idx + 1):
        cell_row = rows_map.get(idx)
        if not cell_row:
            col_cells.append(CompositeCell.free_text(""))
        else:
            col_cells.append(_build_single_cell(cell_row, header))
    return col_cells


def _build_arc_table(t_name: str, rows: list[dict[str, Any]]) -> ArcTable | None:
    """Build an ArcTable from flat database rows."""
    if not rows:
        return None

    table = ArcTable.init(t_name)

    # Determine max row index
    max_row_idx = max((cast(int, r.get("row_index", 0)) for r in rows), default=-1)
    if max_row_idx < 0:
        return None

    col_keys: list[tuple] = []
    seen_keys = set()
    col_to_rows: dict[tuple, dict[int, dict[str, Any]]] = defaultdict(dict)

    for r in rows:
        key = _get_column_key(r)
        if key not in seen_keys:
            col_keys.append(key)
            seen_keys.add(key)
        col_to_rows[key][cast(int, r.get("row_index", 0))] = r

    for key in col_keys:
        header = _build_header(key)
        if not header:
            continue

        # Build Cells for this column
        col_cells = _build_column_cells(col_to_rows[key], max_row_idx, header)
        table.AddColumn(header, col_cells)

    return table


def _process_annotation_tables(
    inv_id: str, annotations: list[dict[str, Any]], study_map: dict[str, Any], assay_map: dict[str, Any]
) -> None:
    """Process and add annotation tables."""
    tables_groups = defaultdict(list)
    for ann in annotations:
        if ann.get("investigation_ref") == inv_id:
            key = (ann.get("target_type"), ann.get("target_ref"), ann.get("table_name"))
            tables_groups[key].append(ann)

    for (t_type, t_ref, t_name), rows in tables_groups.items():
        if not t_name:
            continue

        target = None
        if t_type == "study" and isinstance(t_ref, str):
            target = study_map.get(t_ref)
        elif t_type == "assay" and isinstance(t_ref, str):
            target = assay_map.get(t_ref)

        if target:
            table = _build_arc_table(t_name, rows)
            if table:
                target.AddTable(table)


def build_single_arc_task(data: ArcBuildData) -> str:
    """Build a single ARC object from data.

    This function is designed to run in a separate process.
    It returns the JSON representation to minimize memory footprint in the main process.
    """
    inv_id = str(data.investigation_row.identifier)

    try:
        # Map Investigation and create ARC
        arc_inv = map_investigation(data.investigation_row)
        arc = ARC.from_arc_investigation(arc_inv)

        # Identify relevant studies and assays
        relevant_studies = [s for s in data.studies if str(s.investigation_ref) == inv_id]
        relevant_assays = [a for a in data.assays if str(a.investigation_ref) == inv_id]

        # Add studies and assays
        study_map = _add_studies_to_arc(arc, relevant_studies)
        assay_map = _add_assays_to_arc(arc, relevant_assays, study_map)

        # Add contacts and publications
        _add_contacts_to_arc(arc, inv_id, data.contacts, study_map, assay_map)
        _add_publications_to_arc(arc, inv_id, data.publications, study_map)

        # Process annotation tables
        _process_annotation_tables(inv_id, data.annotations, study_map, assay_map)

        # Serialize immediately in the worker process
        json_str: str = arc.ToROCrateJsonString()

        # Explicitly clean up memory before returning
        del arc
        del arc_inv
        del study_map
        del assay_map
        gc.collect()

        return json_str

    except Exception:
        gc.collect()
        raise
