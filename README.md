# babylist-scraper

[![CI](https://img.shields.io/github/actions/workflow/status/andrewadlof/babylist-scraper/ci.yml?branch=main&logo=github&label=CI)](https://github.com/andrewadlof/babylist-scraper/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.14%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/packaging-uv-DE5FE9?logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
[![Polars](https://img.shields.io/badge/dataframes-Polars-CD792C?logo=polars&logoColor=white)](https://pola.rs/)
[![Playwright](https://img.shields.io/badge/scraping-Playwright-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev/python/)
[![Typer](https://img.shields.io/badge/CLI-Typer-009688?logo=typer&logoColor=white)](https://typer.tiangolo.com/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with ty](https://img.shields.io/badge/types-ty-261230?logo=astral&logoColor=white)](https://github.com/astral-sh/ty)
[![pre-commit](https://img.shields.io/badge/pre--commit-prek-FAB040?logo=pre-commit&logoColor=black)](https://github.com/j178/prek)
[![Open PRs](https://img.shields.io/github/issues-pr/andrewadlof/babylist-scraper?logo=github&label=open%20PRs)](https://github.com/andrewadlof/babylist-scraper/pulls)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?logo=github)](https://github.com/andrewadlof/babylist-scraper/pulls)

A small CLI that scrapes a **public Babylist baby registry** from its share link and saves it
to a flat file (`xlsx` by default, or `csv` / `parquet`), enriched with extra columns for
annotation and analysis.

## How it works

Babylist is a React single-page app backed by an internal `/api/v3` JSON API:

- **Registry metadata** (`/api/v3/registries/<slug>`) is public and fetched directly with `httpx`.
- **Gift items** (`/api/v3/registries/<id>/reg_items`) are gated behind Cloudflare and a synced
  browser session, so plain HTTP requests get a `403`. The scraper therefore drives a headless
  **Playwright** Chromium browser to the registry page and intercepts the `reg_items` JSON
  response — exactly what a real browser loads.

Scraped rows are written with [**Polars**](https://pola.rs/) — the only dataframe library used
in this project (no pandas).

## Documentation

Full docs live in [`docs/`](docs/index.md):

- [Usage](docs/usage.md) — installation, CLI reference, configuration.
- [Architecture](docs/architecture.md) — how the item-API gating is handled.
- [Output schema](docs/output-schema.md) — every exported column.
- [Development](docs/development.md) — tooling, tests, and pre-commit hooks.

## Setup

Requires Python ≥ 3.14 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run playwright install chromium   # one-time: download the browser binary
```

## Usage

```bash
# Scrape a registry link (writes to the path in config/config.yaml -> output.path)
uv run babylist-scraper scrape https://www.babylist.com/list/<slug>

# No URL given -> falls back to registry_url in config/config.yaml
uv run babylist-scraper scrape

# Override format / output path
uv run babylist-scraper scrape <url> --format csv --output out.csv

# Watch the browser / cap rows while testing
uv run babylist-scraper scrape <url> --no-headless --limit 5 --verbose
```

CLI flags always override values from the config file.

### Options

| Flag | Description |
| --- | --- |
| `URL` (arg) | Registry link or bare slug. Optional — falls back to config. |
| `-c, --config` | Path to `config.yaml` (default `config/config.yaml`). |
| `-f, --format` | `xlsx` \| `csv` \| `parquet`. |
| `-o, --output` | Output file path. |
| `--headless / --no-headless` | Run the browser headless (default on). |
| `-l, --limit` | Cap the number of rows written. |
| `-v, --verbose` | Verbose output. |

## Output columns

Source data (from Babylist): `id`, `title`, `description`, `category_id`, `quantity`,
`quantity_needed`, `quantity_purchased`, `price`, `price_numeric`, `store`, `product_url`,
`image_url`, `is_reserved`, `is_favorite`, `is_group_gift`, `is_crowdfund`, `is_gift_card`,
`is_available_on_babylist`, `funded_amount`, `goal_amount`, `position`, `registry_owner`,
`registry_slug`.

Extra columns added by the tool:

- **`comments`** — blank text column for your own notes.
- **`is_necessary`** — blank boolean for you to mark must-haves.
- **`is_fully_purchased`** — derived from `quantity_needed` (nothing left to buy).
- **`scraped_at`**, **`source_url`** — provenance (UTC timestamp + the registry link).

## Project layout

```
config/config.yaml            # default registry URL, output, scraper settings
src/babylist_scraper/
  cli.py        # Typer CLI (entry point)
  config.py     # YAML + CLI-override loading
  models.py     # pydantic models
  scraper.py    # Playwright fetch + reg_items interception
  parser.py     # raw JSON -> normalised rows (+ extra columns)
  exporter.py   # Polars writer (xlsx / csv / parquet)
docs/           # documentation
tests/          # offline tests against a captured fixture
```

## Development

Install dev tooling and enable the git hooks:

```bash
uv sync --extra dev
uv tool install prek     # or: pipx install prek
prek install             # writes .git/hooks/pre-commit
```

Pre-commit hooks (managed by [prek](https://github.com/j178/prek), configured in
`.pre-commit-config.yaml`) run **ruff check**, **ruff format**, **ty** (type checking),
**yamlfix**, and **sqlfluff**. Run them on demand with:

```bash
prek run --all-files
```

## Testing

```bash
uv run pytest
```

Tests run offline against a captured `reg_items` fixture — no network required.

## Notes

- Please scrape responsibly: one registry per run, no aggressive automation.
- Password-protected or private registries are out of scope; the tool reports a clear error.
