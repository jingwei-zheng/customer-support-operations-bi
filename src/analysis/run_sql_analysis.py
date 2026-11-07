"""Execute the six named reporting questions and save their actual results."""

import re

import pandas as pd
import psycopg

from src.config import Paths, database_settings


def run() -> None:
    body = (Paths.sql / "analysis_queries.sql").read_text(encoding="utf-8")
    parts = re.split(r"^-- name: (\w+)\s*$", body, flags=re.MULTILINE)
    target = Paths.reports / "sql"
    target.mkdir(parents=True, exist_ok=True)
    with psycopg.connect(**database_settings()) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        for name, statement in zip(parts[1::2], parts[2::2]):
            with conn.cursor() as cursor:
                cursor.execute(statement)
                frame = pd.DataFrame(cursor.fetchall(), columns=[c.name for c in cursor.description])
            frame.to_csv(target / f"{name}.csv", index=False)
            print(f"Saved {name}: {len(frame)} rows")


if __name__ == "__main__":
    run()
