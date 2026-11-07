"""Load issues.csv and execute the original SQL's reporting layers in one transaction."""

import csv
import sys

import psycopg
from psycopg import sql

from src.config import Paths, database_settings
from src.data.make_dataset import build as validate_source

SQL_ORDER = ["00_create_schemas.sql", "01_raw_tables.sql", "02_staging.sql", "03_dimensions.sql", "04_facts.sql", "05_analytics_views.sql"]


def build(sql_only: bool = False) -> None:
    path = Paths.raw_mendeley / "issues.csv"
    validate_source()  # fail before writing to the database if the source is invalid
    with psycopg.connect(**database_settings()) as conn:
        for name in SQL_ORDER:
            if sql_only and name in SQL_ORDER[:2]:
                continue
            conn.execute((Paths.sql / name).read_text(encoding="utf-8"))
            if name == "01_raw_tables.sql":
                with path.open(encoding="utf-8", newline="") as stream:
                    header = next(csv.reader(stream))
                columns = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in header]
                statement = sql.SQL("COPY raw.issues ({}) FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')").format(sql.SQL(", ").join(map(sql.Identifier, columns)))
                with path.open(encoding="utf-8", newline="") as stream, conn.cursor() as cursor:
                    with cursor.copy(statement) as copy:
                        while chunk := stream.read(1 << 20):
                            copy.write(chunk)
            print(f"Built {name}")
    print("Warehouse build committed.")


if __name__ == "__main__":
    build(sql_only="--sql-only" in sys.argv)
