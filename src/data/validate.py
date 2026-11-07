"""Fail on invalid source records or disagreement between exported reporting tables."""

import json
import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.config import Paths
from src.data import schemas as S


class DataQualityError(ValueError):
    pass


def validate_tickets(t: pd.DataFrame) -> dict:
    failures = []
    if t.empty:
        failures.append("source has no work items")
    if t.ticket_id.isna().any() or t.ticket_id.duplicated().any():
        failures.append("ticket ids must be non-null and unique")
    if t.created_at.isna().any():
        failures.append("creation timestamps must be valid")
    if t.invalid_date_sequence.any():
        failures.append("resolution precedes creation")
    if (t.created_at > pd.Timestamp("2023-03-14 23:59:59", tz="UTC")).any():
        failures.append("creation timestamp exceeds this historical extract")
    unexpected_types = sorted(set(t.issue_type) - S.HELPDESK_ISSUE_TYPES - S.INTERNAL_ISSUE_TYPES)
    unexpected_priorities = sorted(set(t.priority) - set(S.PRIORITY_ORDER))
    if unexpected_types:
        failures.append(f"unexpected work-item types: {unexpected_types}")
    if unexpected_priorities:
        failures.append(f"unexpected priorities: {unexpected_priorities}")
    if failures:
        raise DataQualityError("; ".join(failures))
    return {
        "work_items": len(t),
        "helpdesk_tickets": int(t.is_helpdesk_ticket.sum()),
        "internal_work_items": int((~t.is_helpdesk_ticket).sum()),
        "unknown_priority_work_items": int((~t.priority_known).sum()),
        "unknown_priority_helpdesk": int((t.is_helpdesk_ticket & ~t.priority_known).sum()),
        "helpdesk_created_since_2016": int((t.is_helpdesk_ticket & t.in_system_period).sum()),
        "open_helpdesk_at_extract": int((t.is_helpdesk_ticket & t.is_open_backlog).sum()),
        "checks_passed": ["unique_non_null_id", "valid_created_timestamp", "nonnegative_resolution", "historical_extract_boundary", "known_type_vocabulary", "known_priority_vocabulary"],
    }


def _bools(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series
    mapped = series.astype(str).str.lower().map({"true": True, "false": False})
    if mapped.isna().any():
        raise DataQualityError(f"Invalid Boolean in {series.name}")
    return mapped.astype(bool)


def _validate_fact_dates_and_backlog(fact: pd.DataFrame) -> None:
    created = pd.to_datetime(fact.created_date, errors="coerce", utc=True)
    resolved = pd.to_datetime(fact.resolved_date, errors="coerce", utc=True)
    if created.isna().any() or (fact.resolved_date.notna() & resolved.isna()).any():
        raise DataQualityError("Fact contains invalid created/resolved dates")
    if not fact.is_resolved.eq(resolved.notna()).all():
        raise DataQualityError("is_resolved disagrees with resolved_date")
    if (resolved < created).any():
        raise DataQualityError("Fact resolution date precedes creation")
    durations = pd.to_numeric(fact.resolution_hours, errors="coerce")
    if not np.isfinite(durations[fact.is_resolved]).all() or (durations[fact.is_resolved] < 0).any():
        raise DataQualityError("Resolved rows require finite nonnegative resolution hours")
    if durations[~fact.is_resolved].notna().any():
        raise DataQualityError("Unresolved rows must have blank resolution hours")
    ages = pd.to_numeric(fact.age_days_at_extract, errors="coerce")
    opened = fact.is_open_backlog
    if not np.isfinite(ages[opened]).all() or (ages[opened] < 0).any():
        raise DataQualityError("Open backlog requires finite nonnegative extract ages")
    if ages[~opened].notna().any():
        raise DataQualityError("Non-backlog rows must have blank extract ages")
    flag = _bools(fact.is_backlog_30_plus)
    if not flag.eq(opened & ages.ge(30)).all():
        raise DataQualityError("is_backlog_30_plus disagrees with full-precision extract age")
    labels = ["0-7 days", "7-30 days", "30-90 days", "90-365 days", "365+ days"]
    expected = pd.cut(ages.where(opened), [0, 7, 30, 90, 365, np.inf], right=False, labels=labels)
    if not fact.backlog_age_bucket.fillna("<blank>").eq(expected.astype(object).fillna("<blank>")).all():
        raise DataQualityError("backlog_age_bucket disagrees with full-precision extract age")
    expected_order = pd.cut(ages.where(opened), [0, 7, 30, 90, 365, np.inf], right=False, labels=[1, 2, 3, 4, 5]).astype(float)
    actual_order = pd.to_numeric(fact.backlog_age_bucket_order, errors="coerce")
    if not np.isclose(actual_order, expected_order, equal_nan=True).all():
        raise DataQualityError("backlog_age_bucket_order disagrees with extract age")


def validate_exports() -> dict:
    root = Paths.dashboard_exports
    fact_path = root / "fact_tickets.csv"
    if not fact_path.exists():
        raise FileNotFoundError("fact_tickets.csv is missing. Run data, load, dashboard-export first.")
    fact = pd.read_csv(fact_path, low_memory=False)
    if fact.empty:
        raise DataQualityError("Exported fact has no work items")
    for column in ["is_helpdesk_ticket", "is_open_backlog", "is_high_severity", "is_resolved", "priority_known", "in_system_period"]:
        fact[column] = _bools(fact[column])
    if fact.ticket_id.isna().any() or fact.ticket_id.duplicated().any():
        raise DataQualityError("Exported fact grain is not one row per work item")
    _validate_fact_dates_and_backlog(fact)
    joins = [
        ("dim_date", "full_date", "created_date"),
        ("dim_date", "full_date", "resolved_date"),
        ("dim_priority", "priority", "priority"),
        ("dim_issue_type", "issue_type", "issue_type"),
        ("dim_project", "project_key", "project_key"),
        ("dim_reporter", "reporter_id", "reporter_id"),
    ]
    for name, dim_key, fact_key in joins:
        dim = pd.read_csv(root / f"{name}.csv", dtype={dim_key: str})
        if dim[dim_key].isna().any() or dim[dim_key].duplicated().any():
            raise DataQualityError(f"{name} is not unique on {dim_key}")
        if not fact[fact_key].dropna().astype(str).isin(dim[dim_key]).all():
            raise DataQualityError(f"Unmatched fact keys for {name}")
    hd = fact[fact.is_helpdesk_ticket]
    opened = hd[hd.is_open_backlog]
    resolved = hd[hd.is_resolved & hd.in_system_period]
    kpi_table = pd.read_csv(root / "kpi_summary.csv")
    if len(kpi_table) != 1:
        raise DataQualityError("KPI summary must contain exactly one row")
    kpi = kpi_table.iloc[0]
    expected = {
        "total_work_items": len(fact),
        "total_helpdesk_tickets": len(hd),
        "tickets_since_2016": int(hd.in_system_period.sum()),
        "open_backlog": len(opened),
    }
    for name, value in expected.items():
        if int(kpi[name]) != value:
            raise DataQualityError(f"KPI {name} differs from fact recount")
    median = None if resolved.empty else float(resolved.resolution_hours.median())
    if median is None:
        if not pd.isna(kpi.median_resolution_hours):
            raise DataQualityError("Median resolution must be blank when there are no resolved service rows")
    elif not math.isfinite(median) or not math.isfinite(float(kpi.median_resolution_hours)) or abs(float(kpi.median_resolution_hours) - median) > 0.11:
        raise DataQualityError("Median resolution differs from fact recount or is not finite")
    backlog = pd.read_csv(root / "backlog_ageing.csv")
    if int(backlog.open_tickets.sum()) != len(opened):
        raise DataQualityError("Backlog ageing does not sum to open tickets")
    aged = int((opened.age_days_at_extract >= 30).sum())
    if int(backlog.loc[backlog.age_bucket_order >= 3, "open_tickets"].sum()) != aged:
        raise DataQualityError("Age bucket totals differ from fact recount")
    monthly = pd.read_csv(root / "monthly_volume.csv")
    if int(monthly.tickets_created.sum()) != len(hd):
        raise DataQualityError("Monthly demand does not sum to helpdesk population")
    priority = pd.read_csv(root / "priority_breakdown.csv")
    if int(priority.tickets.sum()) != int(hd.priority_known.sum()):
        raise DataQualityError("Priority summary uses a different denominator")
    processed_path = Paths.processed / "tickets.csv"
    compared_to_python = False
    if processed_path.exists():
        py = pd.read_csv(processed_path, low_memory=False)
        if len(py) != len(fact) or set(py.ticket_id) != set(fact.ticket_id):
            raise DataQualityError("Python and SQL ticket populations disagree")
        joined = fact.merge(py, on="ticket_id", suffixes=("_sql", "_py"), validate="one_to_one")
        for col in ["is_helpdesk_ticket", "is_open_backlog", "is_high_severity", "is_resolved", "priority_known", "in_system_period"]:
            if not (_bools(joined[col+"_sql"]) == _bools(joined[col+"_py"])).all():
                raise DataQualityError(f"Python and SQL disagree on {col}")
        for col, tolerance in [("resolution_hours", 0.00501), ("resolution_days", 0.00501), ("age_days_at_extract", 1e-8)]:
            actual = pd.to_numeric(joined[col+"_sql"], errors="coerce")
            reference = pd.to_numeric(joined[col+"_py"], errors="coerce")
            if not np.isclose(actual, reference, atol=tolerance, rtol=0, equal_nan=True).all():
                raise DataQualityError(f"Python and SQL disagree on {col}")
        compared_to_python = True
    report = {
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "extract_as_at": "2023-03-14",
        **expected,
        "open_at_least_30_days": aged,
        "median_resolution_hours_recount": None if median is None else round(median, 1),
        "python_sql_flags_compared": compared_to_python,
        "python_sql_durations_compared": compared_to_python,
        "status": "passed",
    }
    Paths.reports.mkdir(parents=True, exist_ok=True)
    (Paths.reports / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    validate_exports()
