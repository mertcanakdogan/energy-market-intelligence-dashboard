"""DuckDB star-schema construction and ordered SQL-model execution."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import duckdb
import pandas as pd


def execute_sql_models(connection: duckdb.DuckDBPyConnection, sql_dir: Path) -> list[str]:
    """Execute numbered SQL files in lexical order and return their names."""

    scripts = sorted(sql_dir.glob("[0-9][0-9]_*.sql"))
    if not scripts:
        raise FileNotFoundError(f"No numbered SQL models found in {sql_dir}")
    for script in scripts:
        connection.execute(script.read_text(encoding="utf-8"))
    return [script.name for script in scripts]


def build_database(
    bundle: Mapping[str, pd.DataFrame], database_path: Path, sql_dir: Path
) -> list[str]:
    """Rebuild the local analytical model from registered, validated dataframes."""

    database_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(database_path)) as connection:
        for table_name, frame in bundle.items():
            connection.register(f"source_{table_name}", frame)
        executed = execute_sql_models(connection, sql_dir)
        connection.execute("CHECKPOINT")
    return executed


def list_relations(database_path: Path) -> set[str]:
    """Return user-facing tables and views in the main schema."""

    with duckdb.connect(str(database_path), read_only=True) as connection:
        rows = connection.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
    return {row[0] for row in rows}


def query_dataframe(
    database_path: Path, query: str, parameters: list[object] | None = None
) -> pd.DataFrame:
    """Run a read-only, parameter-capable query and return a dataframe."""

    with duckdb.connect(str(database_path), read_only=True) as connection:
        return connection.execute(query, parameters or []).df()
