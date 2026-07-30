"""Unit tests for harvest-report JSON-LD shape and counting semantics."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from middleware.shared.report import HarvestReport, JsonLdReportSerializer


def test_finished_report_uses_shared_jsonld_vocabulary() -> None:
    """Finished report renders shared vocabulary fields."""
    report = HarvestReport(
        name="SQL to ARC Conversion Run",
        start_time=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
    )
    scope = report.open_repository("edaphobase")
    scope.set_expected_datasets(2)
    scope.record_harvested()
    scope.add_studies(1)
    scope.add_assays(1)
    scope.record_failed("boom", record_id="inv-fail")
    report.finish(end_time=datetime(2026, 1, 1, 0, 1, tzinfo=UTC))

    doc = json.loads(JsonLdReportSerializer().render(report))

    assert doc["@type"] == "schema:Action"
    assert doc["name"] == "SQL to ARC Conversion Run"
    assert "schema:startTime" in doc
    assert "schema:endTime" in doc
    entry = doc["schema:result"][0]
    assert entry["identifier"] == "edaphobase"
    assert entry["fairagro:expectedDatasets"] == 2  # noqa: PLR2004
    assert entry["fairagro:harvestedDatasets"] == 1
    assert entry["fairagro:failedDatasets"] == 1
    assert entry["fairagro:totalStudies"] == 1
    assert entry["fairagro:totalAssays"] == 1
    assert entry["fairagro:failedRecords"][0]["fairagro:recordId"] == "inv-fail"


def test_failed_investigations_exclude_composition_from_totals() -> None:
    """Study/assay totals only include successfully harvested investigations."""
    report = HarvestReport(start_time=datetime(2026, 1, 1, 0, 0, tzinfo=UTC))
    scope = report.open_repository("edaphobase")
    scope.record_harvested()
    scope.add_studies(2)
    scope.add_assays(3)
    scope.record_failed("upload failed", record_id="bad-inv")
    report.finish(end_time=datetime(2026, 1, 1, 0, 1, tzinfo=UTC))
    entry = report.repository_reports[0]
    assert entry.harvested_datasets == 1
    assert entry.failed_datasets == 1
    assert entry.failed_records[0].record_id == "bad-inv"
    assert entry.total_studies == 2  # noqa: PLR2004
    assert entry.total_assays == 3  # noqa: PLR2004
