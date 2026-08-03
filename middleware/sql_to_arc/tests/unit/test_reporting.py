"""Unit tests for harvest-report JSON-LD shape and counting semantics."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from middleware.shared.report import HarvestReport, JsonLdReportSerializer


def test_finished_report_uses_shared_jsonld_vocabulary() -> None:
    """Finished report renders shared vocabulary fields."""
    expected_datasets = 2
    harvested_datasets = 1
    failed_datasets = 1
    total_studies = 1
    total_assays = 1

    report = HarvestReport(
        name="SQL to ARC Conversion Run",
        start_time=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
    )
    scope = report.open_repository("edaphobase")
    scope.set_expected_datasets(expected_datasets)
    scope.record_harvested()
    scope.add_studies(total_studies)
    scope.add_assays(total_assays)
    scope.record_failed("boom", record_id="inv-fail")
    report.finish(end_time=datetime(2026, 1, 1, 0, 1, tzinfo=UTC))

    doc = json.loads(JsonLdReportSerializer().render(report))

    assert doc["@type"] == "schema:Action"
    assert doc["name"] == "SQL to ARC Conversion Run"
    assert "schema:startTime" in doc
    assert "schema:endTime" in doc
    entry = doc["schema:result"][0]
    assert entry["identifier"] == "edaphobase"
    assert entry["fairagro:expectedDatasets"] == expected_datasets
    assert entry["fairagro:harvestedDatasets"] == harvested_datasets
    assert entry["fairagro:failedDatasets"] == failed_datasets
    assert entry["fairagro:totalStudies"] == total_studies
    assert entry["fairagro:totalAssays"] == total_assays
    assert entry["fairagro:failedRecords"][0]["fairagro:recordId"] == "inv-fail"


def test_failed_investigations_exclude_composition_from_totals() -> None:
    """Study/assay totals only include successfully harvested investigations."""
    total_studies = 2
    total_assays = 3

    report = HarvestReport(start_time=datetime(2026, 1, 1, 0, 0, tzinfo=UTC))
    scope = report.open_repository("edaphobase")
    scope.record_harvested()
    scope.add_studies(total_studies)
    scope.add_assays(total_assays)
    scope.record_failed("upload failed", record_id="bad-inv")
    report.finish(end_time=datetime(2026, 1, 1, 0, 1, tzinfo=UTC))
    entry = report.repository_reports[0]
    assert entry.harvested_datasets == 1
    assert entry.failed_datasets == 1
    assert entry.failed_records[0].record_id == "bad-inv"
    assert entry.total_studies == total_studies
    assert entry.total_assays == total_assays
