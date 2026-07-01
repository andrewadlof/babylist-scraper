# Output schema

Every export contains the same columns in the same order, whether it is `xlsx`, `csv`, or
`parquet`, and regardless of how many rows were scraped. The column list is defined once as
`babylist_scraper.parser.COLUMNS`.

## Source columns

Mapped from Babylist's `reg_items` API payload.

| Column | Type | Description |
| --- | --- | --- |
| `id` | int | Babylist item id. |
| `title` | str | Item name (whitespace-trimmed). |
| `description` | str | Item description, if any. |
| `category_id` | int | Numeric category id assigned on the registry. |
| `quantity` | int | Total quantity the owner wants. |
| `quantity_needed` | int | Quantity still needed (not yet reserved/purchased). |
| `quantity_purchased` | int | Derived: `quantity - quantity_needed` (floored at 0). |
| `price` | str | Display price string as shown on Babylist (e.g. `"$20.67"`). |
| `price_numeric` | float | Numeric price parsed from the structured/offer/display price. |
| `store` | str | Primary offer's store display name. |
| `product_url` | str | Primary offer's product URL. |
| `image_url` | str | Item image URL. |
| `is_reserved` | bool | Whether the item is reserved by a gift-giver. |
| `is_favorite` | bool | Whether the owner starred the item. |
| `is_group_gift` | bool | Whether the item is a group gift. |
| `is_crowdfund` | bool | Whether the item is a crowdfund. |
| `is_gift_card` | bool | Whether the item is a gift card. |
| `is_available_on_babylist` | bool | Whether Babylist itself stocks the item. |
| `funded_amount` | float | Amount funded (crowdfund/group gifts). |
| `goal_amount` | float | Funding goal (crowdfund/group gifts). |
| `position` | int | The item's position on the registry (used for row ordering). |
| `registry_owner` | str | Registry owner display name. |
| `registry_slug` | str | Registry URL slug. |

## Derived and annotation columns

Added by the tool, not present in the source payload.

| Column | Type | Description |
| --- | --- | --- |
| `is_fully_purchased` | bool | Derived: `quantity_needed <= 0` (nothing left to buy). |
| `comments` | str | **Blank** — free-text column for your own notes. |
| `is_necessary` | bool | **Blank** — mark must-haves yourself (`TRUE`/`FALSE`). |
| `scraped_at` | str | ISO-8601 UTC timestamp of the scrape run. |
| `source_url` | str | The registry link/slug that was scraped. |

## Notes on typing

- Booleans may be null when the source omits the field for a given item.
- `comments` is written as an empty string; when reopened in some tools an empty cell may read
  back as null. `is_necessary` is intentionally null so you can fill it in.
- Babylist does not expose a reliable per-item purchased count publicly; `quantity_purchased`
  and `is_fully_purchased` are inferred from `quantity_needed`.
