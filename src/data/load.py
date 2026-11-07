"""Raw file readers with schema validation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import Paths
from src.data import schemas as S


class SchemaError(ValueError):
    """Raised when a source file does not match the expected contract."""


def _require_columns(df: pd.DataFrame, required: list[str], name: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SchemaError(f"{name}: missing expected columns {missing}")


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lower-case, strip and snake_case column names."""
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]
    return df


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run `python -m src.data.download` first.")
    return normalise_columns(pd.read_csv(path, low_memory=False))


def load_issues(path: Path | None = None) -> pd.DataFrame:
    df = _read_csv(path or Paths.raw_mendeley / "issues.csv")
    _require_columns(df, S.ISSUES_REQUIRED_COLUMNS, "issues.csv")
    return df
