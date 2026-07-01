from babylist_scraper.parser import COLUMNS, build_rows
from babylist_scraper.scraper import extract_slug


def test_build_rows_shape_and_order(raw_items, registry):
    """Every row exposes exactly the declared columns, in order."""
    rows = build_rows(
        raw_items, registry, source_url=registry.url, scraped_at="2026-07-01T00:00:00+00:00"
    )
    assert len(rows) == len(raw_items)
    for row in rows:
        assert list(row.keys()) == COLUMNS


def test_source_fields_mapped(raw_items, registry):
    """Source fields map through, with a stripped title and coerced numeric price."""
    rows = build_rows(
        raw_items, registry, source_url=registry.url, scraped_at="2026-07-01T00:00:00+00:00"
    )
    src = raw_items[0]
    row = next(r for r in rows if r["id"] == src["id"])
    # titles are stripped of stray whitespace
    assert row["title"] == src["title"].strip()
    # price is coerced to a numeric value
    assert isinstance(row["price_numeric"], float)
    # store comes from the primary offer
    assert row["store"] == src["offers"][0]["storeDisplayName"]


def test_derived_and_annotation_columns(raw_items, registry):
    """Annotation columns are blank and provenance/derived columns are populated."""
    rows = build_rows(raw_items, registry, source_url="https://example.com/list/x", scraped_at="TS")
    row = rows[0]
    # annotation columns are blank for the user to fill in
    assert row["comments"] == ""
    assert row["is_necessary"] is None
    # provenance columns are populated
    assert row["scraped_at"] == "TS"
    assert row["source_url"] == "https://example.com/list/x"
    assert row["registry_owner"] == "Test Owner"
    # derived: quantity_needed==0 -> fully purchased; here needed==1 -> not purchased
    assert row["quantity_needed"] == 1
    assert row["is_fully_purchased"] is False
    assert row["quantity_purchased"] == 0


def test_is_fully_purchased_true_when_nothing_needed(raw_items, registry):
    """An item with nothing still needed is marked fully purchased."""
    item = dict(raw_items[0])
    item["quantity"] = 2
    item["quantityNeeded"] = 0
    rows = build_rows([item], registry, source_url="u", scraped_at="TS")
    assert rows[0]["is_fully_purchased"] is True
    assert rows[0]["quantity_purchased"] == 2


def test_rows_sorted_by_position(raw_items, registry):
    """Rows are ordered by the registry ``position`` field."""
    rows = build_rows(raw_items, registry, source_url="u", scraped_at="TS")
    positions = [r["position"] for r in rows if r["position"] is not None]
    assert positions == sorted(positions)


def test_extract_slug_variants():
    """Slugs are extracted from both URL shapes and a bare slug."""
    assert extract_slug("https://www.babylist.com/list/babyloewen") == "babyloewen"
    assert extract_slug("https://my.babylist.com/babyloewen") == "babyloewen"
    assert extract_slug("https://www.babylist.com/list/foo?ref=x") == "foo"
    assert extract_slug("babyloewen") == "babyloewen"
