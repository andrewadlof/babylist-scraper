# Development

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
docs/           # this documentation
tests/          # offline tests against a captured fixture
```

## Setup

```bash
uv sync --extra dev
uv run playwright install chromium
```

## Testing

```bash
uv run pytest
```

Tests run **offline** against a captured `reg_items` fixture (`tests/fixtures/reg_items.json`),
so no network or browser is required:

- `test_parser.py` — field mapping, derived columns, sorting, slug extraction.
- `test_exporter.py` — Polars round-trip for CSV/Parquet and xlsx file creation.

## Code style and quality (prek + pre-commit hooks)

Hooks are managed with [prek](https://github.com/j178/prek), a fast drop-in replacement for
`pre-commit`. They run the tools pinned in `uv.lock` via `uv run`, so local and CI versions
match. Configuration lives in `.pre-commit-config.yaml`.

| Hook | Tool | Purpose |
| --- | --- | --- |
| `ruff-check` | Ruff | Lint (with `--fix`). |
| `ruff-format` | Ruff | Format Python code. |
| `ty` | ty | Static type checking. |
| `yamlfix` | yamlfix | Format YAML files. |
| `sqlfluff-lint` | SQLFluff | Lint SQL (`ansi` dialect; no SQL files yet). |

Install prek and enable the git hook:

```bash
uv tool install prek     # or: pipx install prek
prek install             # writes .git/hooks/pre-commit
```

Run everything on demand:

```bash
prek run --all-files
```

Tool settings live in `pyproject.toml`:

- `[tool.ruff]` — line length 100, target `py314`, lint rules `E/F/I/W/UP` (E501 ignored; the
  formatter handles code width).
- `[tool.ty.environment]` — Python 3.14.
- `[tool.sqlfluff.core]` — `ansi` dialect.

## Dataframes: Polars only

All dataframe construction and file writing goes through **Polars** in `exporter.py`. There is
no pandas dependency. xlsx output uses `XlsxWriter` via `DataFrame.write_excel`; CSV and Parquet
use Polars' native writers.

## Docstrings

Public and private functions/classes use **NumPy-style** docstrings (Parameters / Returns /
Raises). The Typer command in `cli.py` uses a Click `\f` truncation marker so `--help` shows
only the summary while the full docstring remains for introspection.

## Conventions

- Config precedence: CLI flags override `config.yaml`.
- User-facing failures raise `ScrapeError`; the CLI prints the message and exits `1` without a
  traceback.
- Keep the output column list (`parser.COLUMNS`) as the single source of truth for schema/order.
