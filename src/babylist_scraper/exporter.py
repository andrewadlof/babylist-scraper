"""Write normalised registry rows to a flat file (xlsx / csv / parquet).

This module is the single place the project touches a dataframe library. Polars is used
for all dataframe construction and file writing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl

from .models import OutputFormat
from .parser import COLUMNS


def write(rows: list[dict[str, Any]], path: Path, fmt: OutputFormat) -> Path:
    """Write normalised rows to ``path`` in the requested flat-file format.

    A Polars :class:`polars.DataFrame` is built with the fixed column order defined by
    :data:`babylist_scraper.parser.COLUMNS`, so the output schema is identical regardless
    of how many rows were scraped (including zero).

    Parameters
    ----------
    rows : list of dict
        Normalised rows as produced by :func:`babylist_scraper.parser.build_rows`. Each
        dict must contain every key in :data:`babylist_scraper.parser.COLUMNS`.
    path : pathlib.Path
        Destination file path. Missing parent directories are created automatically.
    fmt : OutputFormat
        The output format to write: ``xlsx``, ``csv`` or ``parquet``.

    Returns
    -------
    pathlib.Path
        The path that was written (the same value as ``path``, as a :class:`~pathlib.Path`).

    Raises
    ------
    ValueError
        If ``fmt`` is not a supported :class:`~babylist_scraper.models.OutputFormat`.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if rows:
        # infer_schema_length=None scans every row so columns that are null in early
        # rows (e.g. a crowdfund item with no price) still get their true dtype.
        df = pl.DataFrame(rows, infer_schema_length=None).select(COLUMNS)
    else:
        df = pl.DataFrame(schema={col: pl.Utf8 for col in COLUMNS})

    if fmt is OutputFormat.xlsx:
        df.write_excel(path)
    elif fmt is OutputFormat.csv:
        df.write_csv(path)
    elif fmt is OutputFormat.parquet:
        df.write_parquet(path)
    else:  # pragma: no cover - enum is exhaustive
        raise ValueError(f"Unsupported output format: {fmt}")

    return path
