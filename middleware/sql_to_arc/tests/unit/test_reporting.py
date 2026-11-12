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
        software_version="1.2.3",
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
    assert doc["schema:instrument"]["@type"] == "schema:SoftwareApplication"
    assert doc["schema:instrument"]["schema:softwareVersion"] == "1.2.3"
    assert "schema:startTime" in doc
    assert "schema:endTime" in doc
    entry = doc["schema:result"][0]
    assert entry["identifier"] == "edaphobase"
    assert entry["fairagro:expectedDatasets"] == expected_datasets
    assert entry["fairagro:harvestedDatasets"] == harvested_datasets
    assert entry["fairagro:failedDatasets"] == failed_datasets
    assert entry["fairagro:totalStudies"] == total_studies
    assert entry["fairagro:totalAssays"] == total_assays
    failure = entry["fairagro:failures"][0]
    assert failure["fairagro:recordId"] == "inv-fail"
    assert failure["fairagro:kind"] == "dataset"


def test_finished_report_includes_shared_warnings_vocabulary() -> None:
    """Warned datasets render fairagro:warnedDatasets and fairagro:warnings."""
    report = HarvestReport(
        name="SQL to ARC Conversion Run",
        start_time=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        software_version="1.2.3",
    )
    scope = report.open_repository("edaphobase")
    scope.record_harvested()
    scope.record_warning("plain study_ref coerced", record_id="inv-warn")
    report.finish(end_time=datetime(2026, 1, 1, 0, 1, tzinfo=UTC))

    doc = json.loads(JsonLdReportSerializer().render(report))
    entry = doc["schema:result"][0]
    assert entry["fairagro:harvestedDatasets"] == 1
    assert entry["fairagro:warnedDatasets"] == 1
    assert entry["fairagro:failedDatasets"] == 0
    warning = entry["fairagro:warnings"][0]
    assert warning["fairagro:recordId"] == "inv-warn"
    assert warning["fairagro:kind"] == "dataset"
    assert "plain study_ref" in warning["fairagro:message"]


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
    assert entry.failures[0].record_id == "bad-inv"
    assert entry.failures[0].kind.value == "dataset"
    assert entry.total_studies == total_studies
    assert entry.total_assays == total_assays
