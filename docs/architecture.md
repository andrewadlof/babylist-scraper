# Architecture

## The problem: Babylist gates its item API

Babylist is a client-rendered React single-page app backed by an internal `/api/v3` JSON API.

- **Registry metadata is public.** `GET /api/v3/registries/<slug>` returns an object with
  `id`, `owner_name`, `title`, `url_slug`, `uuid`, `reg_items_count`, and more. A plain HTTP
  client can read it.
- **Gift items are gated.** `GET /api/v3/registries/<id>/reg_items` returns **403** for
  anonymous clients — it is protected by Cloudflare (`__cf_bm`) plus a synced browser session
  established via the `…?session_synced=true` redirect. This holds across id/uuid/slug forms,
  guest cookies, and CSRF/`Accept` header variations.

A real browser loads the items fine because it runs the SPA's JavaScript, which performs the
session sync and passes the Cloudflare challenge.

## The approach: intercept, don't reverse-engineer

Rather than replicate the session/CSRF handshake, the scraper drives a real headless browser
and captures the item JSON off the wire:

1. **Resolve metadata** (`scraper.resolve_registry`) via `httpx` against the public endpoint —
   cheap, and it gives an expected `reg_items_count` used as a completeness target.
2. **Launch Playwright Chromium** (`scraper.fetch_reg_items`) and navigate to the registry URL.
3. **Intercept** every network response whose URL matches `/reg_items` and parse its JSON,
   deduplicating items by `id`.
4. **Scroll** the page (`scraper._scroll_until_loaded`) to trigger lazy loading until the
   captured count reaches `reg_items_count` or the timeout elapses.

This is robust to session/CSRF/Cloudflare changes because it is exactly what a browser does.

## Pipeline

```
url ──► resolve_registry ──► Registry ─┐
                                       ├─► fetch_reg_items ──► raw item dicts
                                       │        (Playwright)
                          build_rows ◄─┘
                              │  (parser: map + derive + annotate columns)
                              ▼
                           write  (exporter: Polars ──► xlsx/csv/parquet)
```

## Module responsibilities

| Module | Responsibility |
| --- | --- |
| `cli.py` | Typer command; wires config → scrape → parse → export; prints a summary. |
| `config.py` | Load YAML defaults and merge CLI overrides (CLI wins). |
| `models.py` | Pydantic models: `ScrapeConfig`, `OutputConfig`, `ScraperConfig`, `Registry`, `OutputFormat`. |
| `scraper.py` | Metadata fetch (httpx) + item interception (Playwright). |
| `parser.py` | Map raw item JSON to ordered rows; derive and annotate columns. |
| `exporter.py` | Build a Polars `DataFrame` and write the chosen format. |

## Notes and limits

- Babylist's public item payload does not expose a reliable per-item purchased count for
  privacy; `is_reserved` and `quantity_needed` are the available signals, and
  `is_fully_purchased` is derived from the latter.
- Password-protected or private registries are out of scope; the tool reports a clear error.
- Please scrape responsibly: one registry per run, no aggressive automation.
