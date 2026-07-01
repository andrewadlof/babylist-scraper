import json
from pathlib import Path

import pytest

from babylist_scraper.models import Registry

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def raw_items() -> list[dict]:
    """Load the captured ``reg_items`` fixture.

    Returns
    -------
    list of dict
        Raw ``reg_item`` dictionaries captured from a live registry.
    """
    return json.loads((FIXTURES / "reg_items.json").read_text())


@pytest.fixture
def registry() -> Registry:
    """Build a fixed :class:`~babylist_scraper.models.Registry` for tests.

    Returns
    -------
    Registry
        A registry matching the captured fixture.
    """
    return Registry(
        id=247201,
        slug="babyloewen",
        owner_name="Test Owner",
        title="Test Registry",
        reg_items_count=3,
        url="https://www.babylist.com/list/babyloewen",
    )
