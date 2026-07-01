"""Turn raw Babylist ``reg_items`` JSON into normalised, export-ready rows.

Field names below come from the live gift-giver ``reg_items`` payload. Everything is read
defensively (``.get``) because the API omits keys per item (e.g. crowdfund-only fields).
"""

from __future__ import annotations

from typing import Any

from .models import Registry

# Stable, ordered output columns. Source columns first, then derived/annotation columns.
COLUMNS: list[str] = [
    # --- source ---
    "id",
    "title",
    "description",
    "category_id",
    "quantity",
    "quantity_needed",
    "quantity_purchased",
    "price",
    "price_numeric",
    "store",
    "product_url",
    "image_url",
    "is_reserved",
    "is_favorite",
    "is_group_gift",
    "is_crowdfund",
    "is_gift_card",
    "is_available_on_babylist",
    "funded_amount",
    "goal_amount",
    "position",
    "registry_owner",
    "registry_slug",
    # --- derived / annotation ---
    "is_fully_purchased",
    "comments",
    "is_necessary",
    "scraped_at",
    "source_url",
]


def _to_float(value: Any) -> float | None:
    """Coerce a price-like value to a float.

    Strips currency symbols and thousands separators before parsing.

    Parameters
    ----------
    value : Any
        A number, or a string such as ``'20.67'`` or ``'$1,299.00'``. May be ``None``.

    Returns
    -------
    float or None
        The parsed value, or ``None`` if ``value`` is ``None`` or cannot be parsed.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _primary_offer(item: dict) -> dict:
    """Return the first store offer for an item.

    Parameters
    ----------
    item : dict
        A raw ``reg_item`` dictionary.

    Returns
    -------
    dict
        The first entry of the item's ``offers`` list, or an empty dict if there is none.
    """
    offers = item.get("offers")
    if isinstance(offers, list) and offers and isinstance(offers[0], dict):
        return offers[0]
    return {}


def _price_numeric(item: dict, offer: dict) -> float | None:
    """Resolve a numeric price for an item.

    Prefers the structured list price, then the primary offer's price, then the item's
    display price string.

    Parameters
    ----------
    item : dict
        A raw ``reg_item`` dictionary.
    offer : dict
        The item's primary offer, as returned by :func:`_primary_offer`.

    Returns
    -------
    float or None
        The best available numeric price, or ``None`` if none can be parsed.
    """
    details = item.get("priceDetails") or {}
    list_price = (details.get("listPrice") or {}).get("price")
    return _to_float(list_price) or _to_float(offer.get("price")) or _to_float(item.get("price"))


def build_row(
    item: dict,
    registry: Registry,
    *,
    source_url: str,
    scraped_at: str,
) -> dict[str, Any]:
    """Map a single raw ``reg_item`` into an ordered output row.

    Reads every field defensively because the API omits keys per item. Derived columns
    (``quantity_purchased``, ``is_fully_purchased``) are computed from ``quantity`` and
    ``quantityNeeded``, and the annotation columns (``comments``, ``is_necessary``) are left
    blank for the user to fill in.

    Parameters
    ----------
    item : dict
        A raw ``reg_item`` dictionary from the intercepted API response.
    registry : Registry
        Registry metadata, used to populate the ``registry_owner`` and ``registry_slug``
        provenance columns.
    source_url : str
        The registry link the user supplied, recorded in the ``source_url`` column.
    scraped_at : str
        An ISO-8601 UTC timestamp for the scrape, recorded in the ``scraped_at`` column.

    Returns
    -------
    dict
        A row whose keys are exactly :data:`COLUMNS`, in order.
    """
    offer = _primary_offer(item)

    quantity = item.get("quantity")
    quantity_needed = item.get("quantityNeeded")
    quantity_purchased = None
    if isinstance(quantity, int) and isinstance(quantity_needed, int):
        quantity_purchased = max(quantity - quantity_needed, 0)

    # "Fully purchased" = nothing still needed. quantityNeeded is the remaining count.
    is_fully_purchased: bool | None = None
    if isinstance(quantity_needed, int):
        is_fully_purchased = quantity_needed <= 0

    title = item.get("title")
    row = {
        "id": item.get("id"),
        "title": title.strip() if isinstance(title, str) else title,
        "description": item.get("description"),
        "category_id": item.get("categoryId"),
        "quantity": quantity,
        "quantity_needed": quantity_needed,
        "quantity_purchased": quantity_purchased,
        "price": item.get("price"),
        "price_numeric": _price_numeric(item, offer),
        "store": offer.get("storeDisplayName") or offer.get("storeName"),
        "product_url": offer.get("normalUrl") or offer.get("url"),
        "image_url": item.get("imgUrl"),
        "is_reserved": item.get("isReserved"),
        "is_favorite": item.get("isFavorite"),
        "is_group_gift": item.get("isGroupGift"),
        "is_crowdfund": item.get("isCrowdfund"),
        "is_gift_card": item.get("isGiftCard"),
        "is_available_on_babylist": item.get("isAvailableOnBabylist"),
        "funded_amount": _to_float(item.get("fundedAmount")),
        "goal_amount": _to_float(item.get("goalAmount")),
        "position": item.get("position"),
        "registry_owner": registry.owner_name,
        "registry_slug": registry.slug,
        # derived / annotation
        "is_fully_purchased": is_fully_purchased,
        "comments": "",  # blank, for the user to fill in
        "is_necessary": None,  # blank boolean, for the user to fill in
        "scraped_at": scraped_at,
        "source_url": source_url,
    }
    return {col: row.get(col) for col in COLUMNS}


def build_rows(
    items: list[dict],
    registry: Registry,
    *,
    source_url: str,
    scraped_at: str,
) -> list[dict[str, Any]]:
    """Build ordered output rows for all items, sorted by their registry position.

    Parameters
    ----------
    items : list of dict
        Raw ``reg_item`` dictionaries from the scraper.
    registry : Registry
        Registry metadata for provenance columns.
    source_url : str
        The registry link the user supplied.
    scraped_at : str
        An ISO-8601 UTC timestamp for the scrape.

    Returns
    -------
    list of dict
        One row per item (keys are :data:`COLUMNS`), sorted by the item ``position`` field
        with position-less items placed last.
    """
    rows = [
        build_row(item, registry, source_url=source_url, scraped_at=scraped_at) for item in items
    ]
    rows.sort(key=lambda r: (r["position"] is None, r["position"]))
    return rows
