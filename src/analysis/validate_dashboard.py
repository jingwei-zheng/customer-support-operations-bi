"""Compare live PostgreSQL results with the report's 13 recorded checks."""

import csv
import json
import math
from datetime import datetime, timezone

import psycopg

from src.config import Paths, database_settings


def run() -> dict:
    checks_root = Paths.root / "dashboard" / "validation"
    with (checks_root / "validation_checks.csv").open(encoding="utf-8-sig", newline="") as stream:
        checks = list(csv.DictReader(stream))
    recorded = json.loads((checks_root / "validation_results.json").read_text(encoding="utf-8-sig"))
    powerbi = {int(row["validation_checks[check_id]"]): float(row["[Power BI]"]) for row in recorded}
    ids = [int(row["check_id"]) for row in checks]
    if len(checks) != 13 or len(recorded) != 13 or set(ids) != set(range(1, 14)) or set(powerbi) != set(ids):
        raise ValueError("The dashboard requires exactly 13 unique, matching check IDs.")
    results = []
    with psycopg.connect(**database_settings()) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        version = conn.execute("SHOW server_version").fetchone()[0]
        database = conn.info.dbname
        for check in checks:
            query = check["sql_query"].strip()
            if not query.upper().startswith("SELECT "):
                raise ValueError("Dashboard validation accepts SELECT statements only.")
            rows = conn.execute(query).fetchall()
            if len(rows) != 1 or len(rows[0]) != 1 or rows[0][0] is None:
                raise ValueError(f"Check {check['check_id']} did not return one numeric result.")
            actual = float(rows[0][0])
            baseline = float(check["sql_result"])
            captured = powerbi[int(check["check_id"])]
            passed = (
                all(math.isfinite(v) for v in (actual, baseline, captured))
                and math.isclose(actual, baseline, rel_tol=0, abs_tol=1e-8)
                and math.isclose(actual, captured, rel_tol=0, abs_tol=1e-8)
            )
            results.append({
                "check_id": int(check["check_id"]),
                "check": check["check"],
                "postgres_result": actual,
                "report_baseline": baseline,
                "recorded_powerbi_value": captured,
                "passed": passed,
            })
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "database": database,
        "postgres_version": version,
        "baseline_date": "2026-11-01",
        "checks_passed": sum(row["passed"] for row in results),
        "checks_total": len(results),
        "status": "passed" if all(row["passed"] for row in results) else "failed",
        "scope": "Live PostgreSQL queries compared with the report's recorded baseline and Power BI values; DAX is not reevaluated by this command.",
        "checks": results,
    }
    Paths.reports.mkdir(parents=True, exist_ok=True)
    (Paths.reports / "powerbi_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Dashboard checks: {report['checks_passed']} of {report['checks_total']} matched ({report['status']}).")
    if report["status"] != "passed":
        raise ValueError("PostgreSQL results differ from the recorded dashboard values.")
    return report


if __name__ == "__main__":
    run()
