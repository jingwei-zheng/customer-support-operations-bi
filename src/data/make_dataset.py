"""Read, validate and save the single operational source; no synthetic data required."""

import json
from datetime import datetime, timezone

from src.config import Paths
from src.data.clean import clean_issues
from src.data.load import load_issues
from src.data.validate import validate_tickets


def build() -> dict:
    tickets = clean_issues(load_issues())
    report = validate_tickets(tickets)
    report["validated_at"] = datetime.now(timezone.utc).isoformat()
    Paths.processed.mkdir(parents=True, exist_ok=True)
    Paths.reports.mkdir(parents=True, exist_ok=True)
    tickets.to_csv(Paths.processed / "tickets.csv", index=False)
    (Paths.reports / "data_quality.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    build()
