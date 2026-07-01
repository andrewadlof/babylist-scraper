import polars as pl
import pytest

from babylist_scraper.exporter import write
from babylist_scraper.models import OutputFormat
from babylist_scraper.parser import COLUMNS, build_rows


@pytest.mark.parametrize(
    ("fmt", "suffix", "reader"),
    [
        (OutputFormat.csv, "csv", pl.read_csv),
        (OutputFormat.parquet, "parquet", pl.read_parquet),
    ],
)
def test_write_roundtrip(raw_items, registry, tmp_path, fmt, suffix, reader):
    """CSV and Parquet round-trip with the declared schema and row count via Polars."""
    rows = build_rows(raw_items, registry, source_url="u", scraped_at="TS")
    out = tmp_path / f"registry.{suffix}"

    written = write(rows, out, fmt)
    assert written == out

    df = reader(out)
    assert df.columns == COLUMNS
    assert df.height == len(rows)


def test_write_xlsx_creates_file(raw_items, registry, tmp_path):
    """Writing xlsx produces a non-empty workbook (read-back needs an extra engine)."""
    rows = build_rows(raw_items, registry, source_url="u", scraped_at="TS")
    out = tmp_path / "registry.xlsx"
    write(rows, out, OutputFormat.xlsx)
    assert out.exists() and out.stat().st_size > 0


def test_write_empty_still_has_schema(tmp_path):
    """Writing zero rows still produces a file with the full column schema."""
    out = tmp_path / "empty.csv"
    write([], out, OutputFormat.csv)
    assert pl.read_csv(out).columns == COLUMNS
