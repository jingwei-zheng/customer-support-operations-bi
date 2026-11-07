"""Run: python scripts/pipeline.py data load dashboard-export sql validate dashboard-checks

Targets: data, load, dashboard-export, sql, validate, dashboard-checks, test, all.
The all target downloads the source, builds the warehouse, exports and validates.
"""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
TARGETS = {
    "data": [[PY, "-m", "src.data.download"], [PY, "-m", "src.data.make_dataset"]],
    "load": [[PY, "-m", "src.database.build"]],
    "dashboard-export": [[PY, "-m", "src.analysis.dashboard_export"]],
    "sql": [[PY, "-m", "src.analysis.run_sql_analysis"]],
    "validate": [[PY, "-m", "src.data.validate"]],
    "dashboard-checks": [[PY, "-m", "src.analysis.validate_dashboard"]],
    "test": [[PY, "-m", "pytest", "-q"]],
}
TARGETS["all"] = sum((TARGETS[name] for name in ["data", "load", "dashboard-export", "sql", "validate", "dashboard-checks"]), [])


def main(argv: list[str]) -> int:
    if not argv or any(name not in TARGETS for name in argv):
        print(__doc__)
        return 2
    for name in argv:
        for command in TARGETS[name]:
            print(f"Running {name}: {' '.join(command[1:])}", flush=True)
            result = subprocess.run(command, cwd=ROOT)
            if result.returncode:
                return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
