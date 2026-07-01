"""Typer CLI for the Babylist scraper."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console

from . import parser as row_parser
from .config import load_config
from .exporter import write
from .models import OutputFormat
from .scraper import ScrapeError, scrape_registry

app = typer.Typer(
    add_completion=False,
    help="Scrape a public Babylist registry to a flat file (xlsx/csv/parquet).",
)
console = Console()
err_console = Console(stderr=True)

DEFAULT_CONFIG = Path("config/config.yaml")


@app.callback()
def _main() -> None:
    """Provide the CLI's top-level help and keep ``scrape`` as an explicit subcommand.

    The presence of a callback stops Typer from collapsing this single-command app and
    dropping the ``scrape`` command name.

    Returns
    -------
    None
        This callback performs no work.
    """


@app.command()
def scrape(
    url: str | None = typer.Argument(
        None,
        help="Babylist registry link or slug. If omitted, uses registry_url from the config file.",
    ),
    config: Path = typer.Option(DEFAULT_CONFIG, "--config", "-c", help="Path to config.yaml."),
    output_format: OutputFormat | None = typer.Option(
        None, "--format", "-f", help="Output format (overrides config)."
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output file path (overrides config)."
    ),
    headless: bool | None = typer.Option(
        None, "--headless/--no-headless", help="Run the browser headless (overrides config)."
    ),
    limit: int | None = typer.Option(
        None, "--limit", "-l", min=1, help="Cap the number of rows written (for testing)."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output."),
) -> None:
    """Scrape a registry and write it to a flat file.

    Resolves configuration (config file plus CLI overrides), scrapes the registry, maps the
    items to rows, and writes them in the requested format. Exits with a non-zero status and
    a friendly message on configuration or scrape errors.

    \f

    Parameters
    ----------
    url : str or None
        Registry link or slug. If ``None``, ``registry_url`` from the config file is used.
    config : pathlib.Path
        Path to the YAML config file.
    output_format : OutputFormat or None
        Output format override (``xlsx``/``csv``/``parquet``).
    output : pathlib.Path or None
        Output file path override.
    headless : bool or None
        Headless-browser override.
    limit : int or None
        Cap on the number of rows written, applied after scraping.
    verbose : bool
        Whether to print the resolved registry URL and output target.

    Raises
    ------
    typer.Exit
        With code ``1`` on a configuration error, a missing registry URL, or a scrape
        failure.
    """
    try:
        cfg = load_config(
            config,
            registry_url=url,
            output_format=output_format,
            output_path=output,
            headless=headless,
        )
    except (ValueError, OSError) as exc:
        err_console.print(f"[red]Config error:[/red] {exc}")
        raise typer.Exit(code=1)

    if not cfg.registry_url:
        err_console.print(
            "[red]No registry URL provided.[/red] Pass one as an argument or set "
            "'registry_url' in the config file."
        )
        raise typer.Exit(code=1)

    if verbose:
        console.print(f"Registry: [cyan]{cfg.registry_url}[/cyan]")
        console.print(f"Output:   [cyan]{cfg.output.path}[/cyan] ({cfg.output.format.value})")

    try:
        with console.status("Resolving registry and scraping items..."):
            registry, raw_items = scrape_registry(cfg.registry_url, cfg.scraper)
    except ScrapeError as exc:
        err_console.print(f"[red]Scrape failed:[/red] {exc}")
        raise typer.Exit(code=1)

    expected = registry.reg_items_count
    if expected is not None and len(raw_items) < expected:
        err_console.print(
            f"[yellow]Warning:[/yellow] captured {len(raw_items)} of {expected} expected items. "
            "Consider raising scraper.timeout_seconds."
        )

    scraped_at = datetime.now(UTC).isoformat()
    rows = row_parser.build_rows(
        raw_items, registry, source_url=cfg.registry_url, scraped_at=scraped_at
    )
    if limit is not None:
        rows = rows[:limit]

    written = write(rows, cfg.output.path, cfg.output.format)

    owner = registry.owner_name or registry.slug
    console.print(
        f"[green]✓[/green] Wrote [bold]{len(rows)}[/bold] items from "
        f"[cyan]{owner}[/cyan]'s registry to [bold]{written}[/bold]"
    )


def main() -> None:  # pragma: no cover - console-script shim
    """Run the Typer application.

    Entry point referenced by the ``babylist-scraper`` console script.

    Returns
    -------
    None
    """
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
