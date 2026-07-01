"""Pydantic models for configuration and scraped data."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class OutputFormat(StrEnum):
    """Supported flat-file output formats.

    Attributes
    ----------
    xlsx : str
        Excel workbook (``.xlsx``). Best for hand-editing the annotation columns.
    csv : str
        Comma-separated values (``.csv``). Universal plain text.
    parquet : str
        Apache Parquet (``.parquet``). Compact columnar format for data pipelines.
    """

    xlsx = "xlsx"
    csv = "csv"
    parquet = "parquet"


class OutputConfig(BaseModel):
    """Where and how to write the scraped registry.

    Attributes
    ----------
    format : OutputFormat
        The flat-file format to write. Defaults to :attr:`OutputFormat.xlsx`.
    path : pathlib.Path
        Destination file path. Defaults to ``output/registry.xlsx``.
    """

    format: OutputFormat = OutputFormat.xlsx
    path: Path = Path("output/registry.xlsx")


class ScraperConfig(BaseModel):
    """Browser/scraper behaviour settings.

    Attributes
    ----------
    headless : bool
        Whether to run Chromium without a visible window. Defaults to ``True``.
    timeout_seconds : int
        Overall budget for page navigation and lazy-load scrolling, in seconds.
        Defaults to ``45``.
    """

    headless: bool = True
    timeout_seconds: int = 45


class ScrapeConfig(BaseModel):
    """Fully resolved configuration for a scrape run (YAML file + CLI overrides).

    Attributes
    ----------
    registry_url : str or None
        The registry link or bare slug to scrape. ``None`` when neither the config file
        nor the CLI supplied one.
    output : OutputConfig
        Output format and destination settings.
    scraper : ScraperConfig
        Browser/scraper behaviour settings.
    """

    registry_url: str | None = None
    output: OutputConfig = Field(default_factory=OutputConfig)
    scraper: ScraperConfig = Field(default_factory=ScraperConfig)


class Registry(BaseModel):
    """Metadata for a single registry.

    Populated from the public ``/api/v3/registries/<slug>`` endpoint.

    Attributes
    ----------
    id : int
        Numeric registry identifier used by Babylist's API.
    slug : str
        URL slug that identifies the registry (e.g. ``babyloewen``).
    owner_name : str or None
        Display name of the registry owner, if exposed.
    title : str or None
        Registry title, if set by the owner.
    reg_items_count : int or None
        Number of gift items Babylist reports for the registry. Used as a completeness
        target when scrolling the page to load all items.
    url : str
        The original link or slug the user supplied.
    """

    id: int
    slug: str
    owner_name: str | None = None
    title: str | None = None
    reg_items_count: int | None = None
    url: str
