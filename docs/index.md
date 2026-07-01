# babylist-scraper documentation

`babylist-scraper` is a small CLI that scrapes a **public Babylist baby registry** from its
share link and writes it to a flat file (`xlsx` by default, or `csv` / `parquet`), enriched
with extra columns for annotation and analysis.

## Contents

- [Usage](usage.md) — installation, CLI reference, and configuration.
- [Architecture](architecture.md) — how the scraper gets past Babylist's item API gating.
- [Output schema](output-schema.md) — every column in the exported file.
- [Development](development.md) — project layout, tooling, and testing.

## At a glance

```bash
uv sync
uv run playwright install chromium        # one-time browser download
uv run babylist-scraper scrape https://www.babylist.com/list/<slug>
```

## Design notes

- **Dataframes:** [Polars](https://pola.rs/) is the one and only dataframe library used
  (see `exporter.py`). There is no pandas dependency.
- **Browser automation:** [Playwright](https://playwright.dev/python/) drives headless
  Chromium to load a registry and intercept its item JSON.
- **Config:** a YAML file provides defaults; CLI flags override them per run.
