"""ARC object building logic for the SQL-to-ARC conversion process."""

import gc
import json
import logging
from collections import defaultdict
from typing import Any

from arctrl import (
    ARC,
    ArcAssay,
    ArcStudy,
    ArcTable,
    OntologyAnnotation,
)
from arctrl.py.Core.Table.composite_cell import CompositeCell_FreeText as CompositeCell, Data

# arctrl ≥3.2 exports CompositeHeader/IOType as typing.TypeAlias only; factories live
# on the tagged-union case classes.
from arctrl.py.Core.Table.composite_header import CompositeHeader_Output as CompositeHeader, IOType_Data as IOType

from middleware.sql_to_arc.context import ArcBuildData
from middleware.sql_to_arc.mapper import (
    map_assay,
    map_contact,
    map_investigation,
    map_publication,
    map_study,
)
from middleware.sql_to_arc.models import (
    AnnotationTableRow,
    AssayRow,
    ContactRow,
    PublicationRow,
    StudyRow,
)

logger = logging.getLogger(__name__)

# Fields ignored when comparing duplicate vAssay rows (same identifier).
_ASSAY_ROW_COMPARE_EXCLUDE = {"identifier", "investigation_ref", "study_ref"}

# Fields ignored when comparing duplicate vStudy rows (same identifier).
_STUDY_ROW_COMPARE_EXCLUDE = {"identifier", "investigation_ref"}


class DuplicateAssayRowError(ValueError):
    """Duplicate assay identifier with conflicting metadata (not just study_ref)."""

    def __init__(self, assay_id: str, fields: list[str]) -> None:
        """Initialize with the duplicate assay id and conflicting field names."""
        self.assay_id = assay_id
        self.fields = fields
        field_list = ", ".join(fields)
        super().__init__(f'Duplicate assay identifier "{assay_id}" with conflicting fields: {field_list}')

    def __reduce__(self) -> tuple[type["DuplicateAssayRowError"], tuple[str, list[str]]]:
        """Preserve assay_id and fields when the exception crosses a process pool boundary."""
        return (self.__class__, (self.assay_id, self.fields))


class DuplicateStudyRowError(ValueError):
    """Duplicate study identifier with conflicting metadata."""

    def __init__(self, study_id: str, fields: list[str]) -> None:
        """Initialize with the duplicate study id and conflicting field names."""
        self.study_id = study_id
        self.fields = fields
        field_list = ", ".join(fields)
        super().__init__(f'Duplicate study identifier "{study_id}" with conflicting fields: {field_list}')

    def __reduce__(self) -> tuple[type["DuplicateStudyRowError"], tuple[str, list[str]]]:
        """Preserve study_id and fields when the exception crosses a process pool boundary."""
        return (self.__class__, (self.study_id, self.fields))


def _conflicting_assay_fields(first: AssayRow, second: AssayRow) -> list[str]:
    """Return field names that differ between two rows excluding link-only columns."""
    first_payload = first.model_dump(exclude=_ASSAY_ROW_COMPARE_EXCLUDE)
    second_payload = second.model_dump(exclude=_ASSAY_ROW_COMPARE_EXCLUDE)
    return sorted(
        key for key in first_payload.keys() | second_payload.keys() if first_payload.get(key) != second_payload.get(key)
    )


def _conflicting_study_fields(first: StudyRow, second: StudyRow) -> list[str]:
    """Return field names that differ between two study rows excluding link-only columns."""
    first_payload = first.model_dump(exclude=_STUDY_ROW_COMPARE_EXCLUDE)
    second_payload = second.model_dump(exclude=_STUDY_ROW_COMPARE_EXCLUDE)
    return sorted(
        key for key in first_payload.keys() | second_payload.keys() if first_payload.get(key) != second_payload.get(key)
    )


def _add_studies_to_arc(arc: ARC, investigation_id: str, study_rows: list[StudyRow]) -> dict[str, ArcStudy]:
    """Add studies to ARC (deduped by identifier) and return study map."""
    study_map: dict[str, ArcStudy] = {}
    study_row_by_id: dict[str, StudyRow] = {}
    duplicate_row_skip_count = 0
    for s_row in study_rows:
        study_id = str(s_row.identifier)
        if study_id in study_map:
            conflicting = _conflicting_study_fields(study_row_by_id[study_id], s_row)
            if conflicting:
                raise DuplicateStudyRowError(study_id, conflicting)
            duplicate_row_skip_count += 1
            continue
        study = map_study(s_row)
        arc.AddRegisteredStudy(study)
        study_map[study_id] = study
        study_row_by_id[study_id] = s_row
    if duplicate_row_skip_count:
        logger.warning(
            'Investigation "%s": skipped %d duplicate vStudy row(s) with the same study identifier '
            "(ARCtrl requires unique study identifiers).",
            investigation_id,
            duplicate_row_skip_count,
        )
    return study_map


def _log_edaphobase_contact_warnings(
    investigation_id: str,
    *,
    native_roles_count: int,
    missing_given_name_count: int,
) -> None:
    """Emit aggregated warnings per investigation for non-spec Edaphobase contact shapes."""
    if native_roles_count:
        logger.warning(
            'Investigation "%s": %d contact(s) use native JSON roles (list) instead of '
            "a JSON string per SQL-to-ARC view spec; coerced automatically (common in Edaphobase exports).",
            investigation_id,
            native_roles_count,
        )
    if missing_given_name_count:
        logger.warning(
            'Investigation "%s": %d contact(s) have no first_name in vContact; using an empty '
            "given name for ARCtrl serialization (common in Edaphobase exports).",
            investigation_id,
            missing_given_name_count,
        )


def _log_edaphobase_study_ref_warnings(
    investigation_id: str,
    *,
    plain_study_ref_count: int,
    duplicate_row_merge_count: int,
) -> None:
    """Emit at most two warnings per investigation for non-spec Edaphobase study_ref shapes."""
    if plain_study_ref_count:
        logger.warning(
            'Investigation "%s": %d assay(s) use plain-text study_ref (single study ID) instead of '
            "a JSON array per SQL-to-ARC view spec; coerced automatically (common in Edaphobase exports).",
            investigation_id,
            plain_study_ref_count,
        )
    if duplicate_row_merge_count:
        logger.warning(
            'Investigation "%s": merged %d duplicate vAssay row(s) with the same assay identifier '
            "(Edaphobase export format). Spec expects one row with study_ref as a JSON array.",
            investigation_id,
            duplicate_row_merge_count,
        )


def _add_assays_to_arc(
    arc: ARC,
    investigation_id: str,
    assay_rows: list[AssayRow],
    study_map: dict[str, ArcStudy],
) -> dict[str, ArcAssay]:
    """Add assays to ARC, link to studies, and return assay map."""
    assay_map: dict[str, ArcAssay] = {}
    assay_row_by_id: dict[str, AssayRow] = {}
    duplicate_row_merge_count = 0
    if assay_rows and not study_map:
        logger.warning(
            "Investigation has %d assay(s) but no studies — assays will not be linked to any study.",
            len(assay_rows),
        )
    for a_row in assay_rows:
        assay_id = str(a_row.identifier)
        if assay_id in assay_map:
            conflicting = _conflicting_assay_fields(assay_row_by_id[assay_id], a_row)
            if conflicting:
                raise DuplicateAssayRowError(assay_id, conflicting)
            duplicate_row_merge_count += 1
            _link_assay_to_studies(assay_map[assay_id], a_row.study_ref, study_map)
            continue

        assay = map_assay(a_row)
        arc.AddAssay(assay)
        assay_map[assay_id] = assay
        assay_row_by_id[assay_id] = a_row
        _link_assay_to_studies(assay, a_row.study_ref, study_map)

    plain_study_ref_count = sum(1 for row in assay_rows if row.study_ref_plain_coerced)
    _log_edaphobase_study_ref_warnings(
        investigation_id,
        plain_study_ref_count=plain_study_ref_count,
        duplicate_row_merge_count=duplicate_row_merge_count,
    )

    return assay_map


def _link_assay_to_studies(assay: ArcAssay, study_ref_val: Any, study_map: dict[str, ArcStudy]) -> None:
    """Link an assay to one or more studies based on the study_ref value."""
    if not study_ref_val:
        return

    study_refs: list[Any]
    if isinstance(study_ref_val, list):
        study_refs = study_ref_val
    elif isinstance(study_ref_val, str):
        try:
            parsed = json.loads(study_ref_val)
            study_refs = parsed if isinstance(parsed, list) else [study_ref_val]
        except json.JSONDecodeError:
            study_refs = [study_ref_val]
    else:
        study_refs = [study_ref_val]

    for s_ref in study_refs:
        s_key = str(s_ref)
        if s_key in study_map:
            study_map[s_key].RegisterAssay(assay.Identifier)


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

    inv_contacts_for_warnings = [c for c in contacts if str(c.investigation_ref) == inv_id]
    _log_edaphobase_contact_warnings(
        inv_id,
        native_roles_count=sum(1 for c in inv_contacts_for_warnings if c.roles_native_json_coerced),
        missing_given_name_count=sum(1 for c in inv_contacts_for_warnings if c.given_name_missing_coerced),
    )


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


# Maps DB schema column_io_type values (snake_case DB contract) to the canonical
# strings recognised by IOType.of_string() (ARCitect display names).
_IO_TYPE_MAP: dict[str, str] = {
    "source_name": "Source Name",
    "sample_name": "Sample Name",
    "data": "Data",
    "material_name": "Material",
}


def _get_column_key(r: AnnotationTableRow) -> tuple[Any, ...]:
    """Extract a unique key for a column definition."""
    return (
        r.column_type,
        r.column_io_type,
        r.column_value,
        r.column_annotation_term,
        r.column_annotation_uri,
        r.column_annotation_version,
        r.column_name,  # Fallback for simple tests
    )


def _build_header(key: tuple[Any, ...]) -> CompositeHeader | None:
    """Build a CompositeHeader from a column key tuple."""
    c_type, c_io, c_val, c_ann_term, c_ann_uri, c_ann_ver, c_name = key
    try:
        oa = OntologyAnnotation(c_ann_term or "", c_ann_uri or "", c_ann_ver or "")

        if c_type in {"input", "output"} and not c_io:
            default_io = "Source Name" if c_type == "input" else "Sample Name"
            logger.warning(
                "column_io_type missing for column_type '%s'; defaulting to '%s'",
                c_type,
                default_io,
            )

        # Dispatch table for different header types
        handlers = {
            "input": lambda: CompositeHeader.input(
                IOType.of_string(_IO_TYPE_MAP.get(c_io or "", c_io or "Source Name"))
            ),
            "output": lambda: CompositeHeader.output(
                IOType.of_string(_IO_TYPE_MAP.get(c_io or "", c_io or "Sample Name"))
            ),
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


def _build_single_cell(cell_row: AnnotationTableRow, header: CompositeHeader) -> CompositeCell:
    """Build a single CompositeCell from a database row."""
    cv = cell_row.cell_value
    cat = cell_row.cell_annotation_term
    cau = cell_row.cell_annotation_uri or ""
    cav = cell_row.cell_annotation_version or ""

    # Unitized cell (value + ontology term)
    if cv is not None and cat is not None:
        return CompositeCell.unitized(str(cv), OntologyAnnotation(cat, cau, cav))

    # Term cell (ontology term only)
    if cat is not None:
        return CompositeCell.term(OntologyAnnotation(cat, cau, cav))

    # Data cell (file path) — required when header is a Data-type IO column
    if header.IsDataColumn:
        return CompositeCell.data(Data(name=str(cv)) if cv is not None else Data())

    # Text value? (either from new schema 'cell_value' or fallback 'value')
    val_to_use = cv
    if val_to_use is not None:
        if header.IsTermColumn:
            # If the column expects a term, wrap the text in an annotation
            return CompositeCell.term(OntologyAnnotation(str(val_to_use), "", ""))
        return CompositeCell.free_text(str(val_to_use))

    return CompositeCell.free_text("")


def _build_column_cells(
    rows_map: dict[int, AnnotationTableRow], max_row_idx: int, header: CompositeHeader
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


def _build_arc_table(t_name: str, rows: list[AnnotationTableRow]) -> ArcTable | None:
    """Build an ArcTable from flat database rows."""
    if not rows:
        return None

    table = ArcTable.init(t_name)

    # Determine max row index
    max_row_idx = max((r.row_index for r in rows), default=-1)
    if max_row_idx < 0:
        return None

    col_keys: list[tuple[Any, ...]] = []
    seen_keys = set()
    col_to_rows: dict[tuple[Any, ...], dict[int, AnnotationTableRow]] = defaultdict(dict)

    for r in rows:
        key = _get_column_key(r)
        if key not in seen_keys:
            col_keys.append(key)
            seen_keys.add(key)
        col_to_rows[key][r.row_index] = r

    for key in col_keys:
        header = _build_header(key)
        if not header:
            continue

        # Build Cells for this column
        col_cells = _build_column_cells(col_to_rows[key], max_row_idx, header)
        table.AddColumn(header, col_cells)

    return table


def _process_annotation_tables(
    inv_id: str, annotations: list[AnnotationTableRow], study_map: dict[str, Any], assay_map: dict[str, Any]
) -> None:
    """Process and add annotation tables."""
    tables_groups: dict[tuple[Any, ...], list[AnnotationTableRow]] = defaultdict(list)
    for ann in annotations:
        if ann.investigation_ref == inv_id:
            key = (ann.target_type, ann.target_ref, ann.table_name)
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
        else:
            logger.warning(
                "Annotation table '%s' targets %s '%s' which does not exist in this investigation; skipping.",
                t_name,
                t_type,
                t_ref,
            )


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
        study_map = _add_studies_to_arc(arc, investigation_id=inv_id, study_rows=relevant_studies)
        assay_map = _add_assays_to_arc(arc, inv_id, relevant_assays, study_map)

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
