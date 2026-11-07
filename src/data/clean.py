"""Cleaning and feature derivation for the Mendeley operational dataset.

Functions take a DataFrame and return a DataFrame so transformations can be checked separately.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from src.data import schemas as S

EXTRACT_DATE_UTC = pd.Timestamp("2023-03-14 23:59:59", tz="UTC")  # last activity in the export


# --------------------------------------------------------------------------- helpers
def parse_ts(series: pd.Series) -> pd.Series:
    """Parse ISO-8601 timestamps (with or without fractional seconds) to tz-aware UTC."""
    return pd.to_datetime(series, errors="coerce", utc=True, format="ISO8601")


def clean_label(series: pd.Series, fill: str = "unknown") -> pd.Series:
    """Strip whitespace, collapse internal spaces, fill missing with a sentinel."""
    s = series.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    return s.fillna(fill).replace("", fill).astype(object)


def to_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").round().astype("Int64")


def requester_segment(ticket_count: pd.Series) -> pd.Series:
    """Derived analytical segment from a reporter total ticket count (not a source field)."""
    out = pd.Series("single", index=ticket_count.index, dtype="object")
    for lo, hi, label in S.REQUESTER_SEGMENT_BANDS:
        out[(ticket_count >= lo) & (ticket_count <= hi)] = label
    return out


_EXTERNAL_PROJ = re.compile(r"^(C\d{2})")


def project_country_code(proj: pd.Series) -> pd.Series:
    """Derive the masked country code (C00..C17) from external project keys, per FEATURES.md.

    External projects are >6 characters and start with the masked country code; shorter
    internal project keys get the label ``internal``.
    """
    s = proj.astype("string").fillna("")
    is_ext = s.str.len() >= 7
    code = s.str.extract(_EXTERNAL_PROJ, expand=False)
    return pd.Series(np.where(is_ext & code.notna(), code, "internal"), index=proj.index).astype(object)


# --------------------------------------------------------------------------- issues
def clean_issues(raw: pd.DataFrame) -> pd.DataFrame:
    """Clean issues.csv into the ticket-level processed table."""
    df = pd.DataFrame()
    df["ticket_id"] = to_int(raw["id"])
    df["issue_num"] = to_int(raw["issue_num"])
    df["project_key"] = clean_label(raw["issue_proj"])
    df["reporter_id"] = clean_label(raw["issue_reporter"])
    df["assignee_id"] = clean_label(raw["issue_assignee"], fill="unassigned")
    df["contributor_count"] = to_int(raw["issue_contr_count"]).fillna(0)
    df["issue_type"] = clean_label(raw["issue_type"])
    df["priority"] = clean_label(raw["issue_priority"])
    df["created_at"] = parse_ts(raw["issue_created"])
    df["resolved_at"] = parse_ts(raw["issue_resolution_date"])
    df["last_change_at"] = parse_ts(raw["last_change_date"])
    df["resolution"] = clean_label(raw["issue_resolution"], fill="unresolved")
    df["status"] = clean_label(raw["issue_status"]).str.lower()
    df["comment_count"] = to_int(raw["issue_comments_count"]).fillna(0)
    df["wf_total_seconds"] = pd.to_numeric(raw["wf_total_time"], errors="coerce")
    df["processing_steps"] = to_int(raw["processing_steps"])
    # workflow state durations that matter for service analysis (seconds; NaN = never in state)
    for col in ["wf_open", "wf_in_progress", "wf_waiting", "wf_resolved", "wf_validation", "wf_reopened"]:
        if col in raw.columns:
            df[f"{col}_seconds"] = pd.to_numeric(raw[col], errors="coerce")
    for col in ["wfe_reopened", "wfe_waiting", "wfe_in_progress"]:
        if col in raw.columns:
            df[f"{col}_count"] = to_int(raw[col]).fillna(0)

    # ---- derived, transparent features
    df["is_helpdesk_ticket"] = df["issue_type"].isin(S.HELPDESK_ISSUE_TYPES)
    df["work_item_class"] = np.where(df["is_helpdesk_ticket"], "helpdesk", "internal")
    df["priority_known"] = df["priority"] != "unknown"
    df["is_high_severity"] = df["priority"].isin(S.HIGH_SEVERITY_PRIORITIES)
    df["is_resolved"] = df["resolved_at"].notna()
    df["is_terminal_status"] = df["status"].isin(S.TERMINAL_STATUSES)
    df["is_open_backlog"] = ~df["is_resolved"] & ~df["is_terminal_status"]
    df["resolution_hours"] = (df["resolved_at"] - df["created_at"]).dt.total_seconds() / 3600.0
    df["resolution_days"] = df["resolution_hours"] / 24.0
    df["age_days_at_extract"] = np.where(
        df["is_open_backlog"], (EXTRACT_DATE_UTC - df["created_at"]).dt.total_seconds() / 86400.0, np.nan
    )
    df["invalid_date_sequence"] = df["resolution_hours"] < 0
    reopened = df["wfe_reopened_count"] if "wfe_reopened_count" in df else pd.Series(0, index=df.index)
    df["was_reopened"] = reopened.fillna(0).astype(int) > 0
    df["project_country_code"] = project_country_code(df["project_key"])
    df["project_scope"] = np.where(df["project_country_code"] == "internal", "internal", "external")
    counts = df.groupby("reporter_id")["ticket_id"].transform("count")
    df["reporter_ticket_count"] = counts
    df["requester_segment_derived"] = requester_segment(counts)
    df["in_system_period"] = df["created_at"] >= pd.Timestamp("2016-01-01", tz="UTC")
    df["created_month"] = df["created_at"].dt.strftime("%Y-%m")
    df["created_year"] = df["created_at"].dt.year.astype("Int64")
    return df
