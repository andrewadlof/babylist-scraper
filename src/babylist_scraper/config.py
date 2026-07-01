"""Load configuration from YAML and merge CLI overrides (CLI wins)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import OutputFormat, ScrapeConfig


def load_config(
    config_path: Path | None,
    *,
    registry_url: str | None = None,
    output_format: OutputFormat | None = None,
    output_path: Path | None = None,
    headless: bool | None = None,
) -> ScrapeConfig:
    """Build a :class:`ScrapeConfig` from an optional YAML file plus CLI overrides.

    File values form the base configuration; any non-``None`` CLI override then takes
    precedence over the corresponding file value.

    Parameters
    ----------
    config_path : pathlib.Path or None
        Path to a YAML config file. If ``None`` or the file does not exist, defaults are
        used as the base.
    registry_url : str or None, optional
        Registry link/slug override. When provided, replaces the file's ``registry_url``.
    output_format : OutputFormat or None, optional
        Output format override. When provided, replaces the file's ``output.format``.
    output_path : pathlib.Path or None, optional
        Output path override. When provided, replaces the file's ``output.path``.
    headless : bool or None, optional
        Headless-browser override. When provided, replaces the file's ``scraper.headless``.

    Returns
    -------
    ScrapeConfig
        The merged, validated configuration.

    Raises
    ------
    ValueError
        If the YAML file does not contain a mapping at its top level.
    """
    data: dict[str, Any] = {}
    if config_path is not None and config_path.exists():
        loaded = yaml.safe_load(config_path.read_text()) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Config file {config_path} must contain a YAML mapping.")
        data = loaded

    cfg = ScrapeConfig.model_validate(data)

    if registry_url is not None:
        cfg.registry_url = registry_url
    if output_format is not None:
        cfg.output.format = output_format
    if output_path is not None:
        cfg.output.path = output_path
    if headless is not None:
        cfg.scraper.headless = headless

    return cfg
