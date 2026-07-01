# Usage

## Requirements

- Python ≥ 3.14
- [uv](https://docs.astral.sh/uv/)

## Installation

```bash
uv sync
uv run playwright install chromium   # one-time: download the Chromium binary
```

If the browser binary is missing at runtime, the tool exits with a message telling you to run
the `playwright install chromium` step.

## Commands

The CLI exposes a single command, `scrape`:

```bash
# Scrape a registry link (writes to output.path from the config file)
uv run babylist-scraper scrape https://www.babylist.com/list/<slug>

# No URL given -> falls back to registry_url in config/config.yaml
uv run babylist-scraper scrape

# Override format / output path
uv run babylist-scraper scrape <url> --format csv --output out.csv

# Watch the browser / cap rows while testing
uv run babylist-scraper scrape <url> --no-headless --limit 5 --verbose
```

A bare slug works too: `uv run babylist-scraper scrape babyloewen`.

## Options

| Flag | Description |
| --- | --- |
| `URL` (argument) | Registry link or bare slug. Optional — falls back to config. |
| `-c, --config` | Path to `config.yaml` (default `config/config.yaml`). |
| `-f, --format` | `xlsx` \| `csv` \| `parquet`. |
| `-o, --output` | Output file path. |
| `--headless / --no-headless` | Run the browser headless (default on). |
| `-l, --limit` | Cap the number of rows written. |
| `-v, --verbose` | Verbose output. |

**CLI flags always override the config file.**

## Configuration

Defaults live in `config/config.yaml`:

```yaml
registry_url: "https://www.babylist.com/list/babyloewen"  # used when no URL is passed
output:
  format: xlsx          # xlsx | csv | parquet
  path: output/registry.xlsx
scraper:
  headless: true        # set false to watch the browser while debugging
  timeout_seconds: 45   # raise if large registries don't fully load
```

Point at a different file with `--config path/to/config.yaml`.

## Exit codes

- `0` — success.
- `1` — configuration error, missing registry URL, or scrape failure (a friendly message is
  printed; no traceback).
