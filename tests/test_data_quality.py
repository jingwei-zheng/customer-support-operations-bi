"""Reporting risks: inconsistent populations, missing priorities and historical age."""

import pandas as pd
import pytest

from src.data.clean import clean_issues
from src.config import Paths
from src.data.validate import DataQualityError, validate_exports, validate_tickets


def raw_rows() -> pd.DataFrame:
    rows = []
    for i, kind in enumerate(["Ticket", "Service", "Story", "HD Service", "Assistance"], 1):
        rows.append({
            "id": str(i), "issue_num": str(i), "issue_proj": "C01PROJ", "issue_reporter": "R1",
            "issue_assignee": "A1", "issue_contr_count": "1", "issue_type": kind,
            "issue_priority": "Medium", "issue_created": "2022-01-01T00:00:00Z",
            "issue_resolution_date": "2022-01-02T00:00:00Z", "last_change_date": "2022-01-02T00:00:00Z",
            "issue_resolution": "Done", "issue_status": "closed", "issue_comments_count": "0",
            "wf_total_time": "86400", "processing_steps": "2",
        })
    return pd.DataFrame(rows)


def test_internal_items_do_not_inflate_customer_demand():
    report = validate_tickets(clean_issues(raw_rows()))
    assert report["work_items"] == 5
    assert report["helpdesk_tickets"] == 4
    assert report["internal_work_items"] == 1


def test_missing_priority_is_preserved_and_excluded_from_known_denominator():
    raw = raw_rows()
    raw.loc[0, "issue_priority"] = None
    tickets = clean_issues(raw)
    assert tickets.loc[0, "priority"] == "unknown"
    assert not tickets.loc[0, "priority_known"]
    assert not tickets.loc[0, "is_high_severity"]
    assert validate_tickets(tickets)["unknown_priority_helpdesk"] == 1


def test_terminal_without_resolution_is_not_open_backlog():
    raw = raw_rows()
    raw.loc[0, ["issue_resolution_date", "issue_resolution", "issue_status"]] = [None, None, "cancelled"]
    raw.loc[1, ["issue_resolution_date", "issue_resolution", "issue_status"]] = [None, None, "waiting"]
    tickets = clean_issues(raw)
    assert not tickets.loc[0, "is_open_backlog"]
    assert tickets.loc[1, "is_open_backlog"]
    assert validate_tickets(tickets)["open_helpdesk_at_extract"] == 1


def test_backlog_age_uses_extract_date_not_today():
    raw = raw_rows()
    raw.loc[0, ["issue_created", "issue_resolution_date", "issue_status"]] = ["2023-03-13T23:59:59Z", None, "waiting"]
    ticket = clean_issues(raw).iloc[0]
    assert ticket.age_days_at_extract == 1.0


def test_legacy_records_are_retained_but_flagged_out_of_service_period():
    raw = raw_rows()
    raw.loc[0, "issue_created"] = "2015-12-31T23:59:59Z"
    raw.loc[1, "issue_created"] = "2016-01-01T00:00:00Z"
    tickets = clean_issues(raw)
    assert not tickets.loc[0, "in_system_period"]
    assert tickets.loc[1, "in_system_period"]
    assert len(tickets) == 5


@pytest.mark.parametrize("problem", ["duplicate", "null_id", "invalid_created", "negative_resolution", "unknown_priority", "future_created"])
def test_bad_source_is_rejected_instead_of_silently_reported(problem):
    raw = raw_rows()
    if problem == "duplicate":
        raw.loc[1, "id"] = raw.loc[0, "id"]
    elif problem == "null_id":
        raw.loc[0, "id"] = None
    elif problem == "invalid_created":
        raw.loc[0, "issue_created"] = "invalid"
    elif problem == "negative_resolution":
        raw.loc[0, "issue_resolution_date"] = "2021-12-31T00:00:00Z"
    elif problem == "unknown_priority":
        raw.loc[0, "issue_priority"] = "Critical"
    else:
        raw.loc[0, "issue_created"] = "2024-01-01T00:00:00Z"
        raw.loc[0, "issue_resolution_date"] = None
    with pytest.raises(DataQualityError):
        validate_tickets(clean_issues(raw))


def test_missing_exports_require_rebuild_instead_of_reporting_success(tmp_path, monkeypatch):
    monkeypatch.setattr(Paths, "dashboard_exports", tmp_path)
    with pytest.raises(FileNotFoundError, match="fact_tickets.csv is missing"):
        validate_exports()


def test_export_duplicate_grain_fails_before_aggregates_can_hide_it(tmp_path, monkeypatch):
    monkeypatch.setattr(Paths, "dashboard_exports", tmp_path)
    row = {"ticket_id": 1, "is_helpdesk_ticket": True, "is_open_backlog": False,
           "is_high_severity": False, "is_resolved": True, "priority_known": True,
           "in_system_period": True}
    pd.DataFrame([row, row]).to_csv(tmp_path / "fact_tickets.csv", index=False)
    with pytest.raises(DataQualityError, match="one row per work item"):
        validate_exports()


@pytest.fixture
def reporting_exports(tmp_path, monkeypatch):
    monkeypatch.setattr(Paths, "dashboard_exports", tmp_path)
    monkeypatch.setattr(Paths, "processed", tmp_path / "processed")
    monkeypatch.setattr(Paths, "reports", tmp_path / "reports")
    common = {"is_helpdesk_ticket": True, "priority_known": True, "in_system_period": True,
              "issue_type": "Ticket", "project_key": "C01PROJ", "reporter_id": "R1"}
    rows = [
        {**common, "ticket_id": 1, "created_date": "2022-01-01", "resolved_date": "2022-01-02",
         "is_open_backlog": False, "is_high_severity": False, "is_resolved": True,
         "priority": "Medium", "resolution_hours": 24.0, "resolution_days": 1.0,
         "age_days_at_extract": None, "is_backlog_30_plus": False,
         "backlog_age_bucket": None, "backlog_age_bucket_order": None},
        {**common, "ticket_id": 2, "created_date": "2023-02-13", "resolved_date": None,
         "is_open_backlog": True, "is_high_severity": True, "is_resolved": False,
         "priority": "High", "resolution_hours": None, "resolution_days": None,
         "age_days_at_extract": 29.999, "is_backlog_30_plus": False,
         "backlog_age_bucket": "7-30 days", "backlog_age_bucket_order": 2},
    ]
    pd.DataFrame(rows).to_csv(tmp_path / "fact_tickets.csv", index=False)
    for name, data in {
        "dim_date": {"full_date": ["2022-01-01", "2022-01-02", "2023-02-13"]},
        "dim_priority": {"priority": ["Medium", "High"]},
        "dim_issue_type": {"issue_type": ["Ticket"]},
        "dim_project": {"project_key": ["C01PROJ"]},
        "dim_reporter": {"reporter_id": ["R1"]},
        "kpi_summary": {"total_work_items": [2], "total_helpdesk_tickets": [2],
                        "tickets_since_2016": [2], "open_backlog": [1], "median_resolution_hours": [24.0]},
        "backlog_ageing": {"open_tickets": [1], "age_bucket_order": [2]},
        "monthly_volume": {"tickets_created": [1, 1]},
        "priority_breakdown": {"tickets": [1, 1]},
    }.items():
        pd.DataFrame(data).to_csv(tmp_path / f"{name}.csv", index=False)
    return tmp_path


def test_complete_export_reconciliation_succeeds(reporting_exports):
    result = validate_exports()
    assert result["open_at_least_30_days"] == 0  # 29.999 must not round into the aged backlog
    assert result["median_resolution_hours_recount"] == 24.0


def test_empty_fact_is_rejected(reporting_exports):
    path = reporting_exports / "fact_tickets.csv"
    pd.read_csv(path).iloc[:0].to_csv(path, index=False)
    with pytest.raises(DataQualityError, match="no work items"):
        validate_exports()


@pytest.mark.parametrize("bad_median", [float("nan"), float("inf")])
def test_missing_or_nonfinite_kpi_median_is_rejected(reporting_exports, bad_median):
    path = reporting_exports / "kpi_summary.csv"
    data = pd.read_csv(path)
    data.loc[0, "median_resolution_hours"] = bad_median
    data.to_csv(path, index=False)
    with pytest.raises(DataQualityError, match="Median resolution"):
        validate_exports()


@pytest.mark.parametrize("field,value", [("is_backlog_30_plus", True),
                                          ("backlog_age_bucket", "30-90 days"),
                                          ("backlog_age_bucket_order", 3)])
def test_corrupted_dashboard_backlog_fields_are_rejected(reporting_exports, field, value):
    path = reporting_exports / "fact_tickets.csv"
    data = pd.read_csv(path)
    data.loc[1, field] = value
    data.to_csv(path, index=False)
    with pytest.raises(DataQualityError, match="backlog"):
        validate_exports()


@pytest.mark.parametrize("problem", ["missing_date", "unmatched_date"])
def test_resolved_flag_and_date_relationship_are_verified(reporting_exports, problem):
    if problem == "missing_date":
        path = reporting_exports / "fact_tickets.csv"
        data = pd.read_csv(path)
        data.loc[0, "resolved_date"] = None
    else:
        path = reporting_exports / "dim_date.csv"
        data = pd.read_csv(path)
        data = data[data.full_date != "2022-01-02"]
    data.to_csv(path, index=False)
    with pytest.raises(DataQualityError, match="resolved_date|Unmatched fact keys"):
        validate_exports()


def test_no_resolved_service_rows_require_blank_median(reporting_exports):
    path = reporting_exports / "fact_tickets.csv"
    fact = pd.read_csv(path)
    fact.loc[0, "in_system_period"] = False
    fact.to_csv(path, index=False)
    path = reporting_exports / "kpi_summary.csv"
    kpi = pd.read_csv(path)
    kpi.loc[0, "tickets_since_2016"] = 1
    kpi.loc[0, "median_resolution_hours"] = float("nan")
    kpi.to_csv(path, index=False)
    assert validate_exports()["median_resolution_hours_recount"] is None
    kpi.loc[0, "median_resolution_hours"] = 0.0
    kpi.to_csv(path, index=False)
    with pytest.raises(DataQualityError, match="must be blank"):
        validate_exports()
