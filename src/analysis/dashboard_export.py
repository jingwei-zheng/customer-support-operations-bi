"""Export the fact, dimensions and reconciliation tables for Power BI."""

from datetime import datetime, timezone
import json

import pandas as pd
import psycopg
from psycopg import sql

from src.config import Paths, database_settings

EXPORTS = {
    "fact_tickets": "v_powerbi_tickets",
    "dim_date": "dim_date",
    "dim_priority": "dim_priority",
    "dim_issue_type": "dim_issue_type",
    "dim_project": "dim_project",
    "dim_reporter": "dim_reporter",
    "kpi_summary": "v_kpi_summary",
    "monthly_volume": "v_monthly_volume",
    "priority_breakdown": "v_priority_breakdown",
    "resolution_metrics": "v_resolution_metrics",
    "backlog_ageing": "v_backlog_ageing",
    "longest_open_cases": "v_longest_open_cases",
}


def run() -> None:
    Paths.dashboard_exports.mkdir(parents=True, exist_ok=True)
    manifest = {"generated_at": datetime.now(timezone.utc).isoformat(), "extract_as_at": "2023-03-14", "exports": {}}
    with psycopg.connect(**database_settings()) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        for name, source in EXPORTS.items():
            with conn.cursor() as cursor:
                cursor.execute(sql.SQL("SELECT * FROM analytics.{}").format(sql.Identifier(source)))
                frame = pd.DataFrame(cursor.fetchall(), columns=[c.name for c in cursor.description])
            frame.to_csv(Paths.dashboard_exports / f"{name}.csv", index=False)
            manifest["exports"][name] = {"source": f"analytics.{source}", "rows": len(frame)}
            print(f"Exported {name}: {len(frame):,} rows")
    (Paths.dashboard_exports / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    run()
