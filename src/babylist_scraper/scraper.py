"""Scrape a Babylist registry.

Registry metadata comes from the public ``/api/v3/registries/<slug>`` endpoint via httpx.
The gift items themselves are gated behind Cloudflare + a synced browser session, so we
drive a headless Chromium (Playwright) to the registry page and intercept the ``reg_items``
JSON network response(s).
"""

from __future__ import annotations

import re
import time
from urllib.parse import urlparse

import httpx

from .models import Registry, ScraperConfig

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
API_BASE = "https://www.babylist.com/api/v3/registries"


class ScrapeError(RuntimeError):
    """Error raised for user-facing scrape failures.

    Examples include an unresolvable URL, a private or non-existent registry, or a missing
    Playwright browser binary. The CLI catches this and prints the message without a
    traceback.
    """


def extract_slug(url: str) -> str:
    """Extract the registry slug from a Babylist URL, or accept a bare slug.

    Handles the two public URL shapes -- ``www.babylist.com/list/<slug>`` and
    ``my.babylist.com/<slug>`` -- as well as a plain slug with no host or path.

    Parameters
    ----------
    url : str
        A Babylist registry link or a bare slug.

    Returns
    -------
    str
        The extracted slug.

    Raises
    ------
    ScrapeError
        If no slug can be found in the URL's path.
    """
    url = url.strip()
    if "/" not in url and "." not in url:
        return url  # already a bare slug

    parsed = urlparse(url if "://" in url else f"https://{url}")
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        raise ScrapeError(f"Could not find a registry slug in URL: {url!r}")
    # www.babylist.com/list/<slug>  ->  take the segment after 'list';
    # my.babylist.com/<slug>        ->  take the first segment.
    if "list" in parts:
        idx = parts.index("list")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return parts[0]


def resolve_registry(url: str, *, timeout: float = 30.0) -> Registry:
    """Fetch public registry metadata for the given URL or slug.

    Calls the public ``/api/v3/registries/<slug>`` endpoint, which does not require a
    browser session.

    Parameters
    ----------
    url : str
        A Babylist registry link or bare slug.
    timeout : float, optional
        HTTP request timeout in seconds. Defaults to ``30.0``.

    Returns
    -------
    Registry
        The resolved registry metadata.

    Raises
    ------
    ScrapeError
        If the network request fails, the registry is not found (HTTP 404), the API
        returns another error status, or the response body is malformed.
    """
    slug = extract_slug(url)
    api_url = f"{API_BASE}/{slug}"
    try:
        resp = httpx.get(
            api_url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=timeout,
            follow_redirects=True,
        )
    except httpx.HTTPError as exc:  # network-level failure
        raise ScrapeError(f"Failed to reach Babylist API for {slug!r}: {exc}") from exc

    if resp.status_code == 404:
        raise ScrapeError(
            f"No public registry found for slug {slug!r}. "
            "Check the link, or the registry may be private."
        )
    if resp.status_code >= 400:
        raise ScrapeError(
            f"Babylist API returned {resp.status_code} for {slug!r}: {resp.text[:200]}"
        )

    reg = resp.json().get("registry", {})
    if not reg:
        raise ScrapeError(f"Unexpected API response for {slug!r} (no 'registry').")

    return Registry(
        id=reg["id"],
        slug=reg.get("url_slug") or slug,
        owner_name=reg.get("owner_name"),
        title=reg.get("title"),
        reg_items_count=reg.get("reg_items_count"),
        url=url,
    )


def _reg_items_from_payload(payload: object) -> list[dict]:
    """Normalise the various shapes a ``reg_items`` response can take into a list of dicts.

    A captured response may be a bare JSON array of items, or an object wrapping the array
    under a ``reg_items``/``registry_items``/``items`` key.

    Parameters
    ----------
    payload : object
        The decoded JSON body of an intercepted network response.

    Returns
    -------
    list of dict
        The item dictionaries found in the payload, or an empty list if none are present.
    """
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("reg_items", "registry_items", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def fetch_reg_items(registry: Registry, cfg: ScraperConfig) -> list[dict]:
    """Drive a headless browser to the registry page and capture ``reg_items`` JSON.

    Babylist gates its item API behind Cloudflare and a synced browser session, so this
    launches Playwright Chromium, navigates to the registry, and intercepts every
    ``reg_items`` network response. The page is scrolled to trigger lazy loading until the
    captured count reaches :attr:`Registry.reg_items_count` or the timeout elapses.

    Parameters
    ----------
    registry : Registry
        The resolved registry metadata (provides the URL and expected item count).
    cfg : ScraperConfig
        Browser behaviour settings (headless mode and timeout).

    Returns
    -------
    list of dict
        The raw item dictionaries, deduplicated by item id. Field mapping is left to
        :func:`babylist_scraper.parser.build_rows`.

    Raises
    ------
    ScrapeError
        If Playwright is not installed or the Chromium browser binary is missing.
    """
    try:
        from playwright.sync_api import TimeoutError as PWTimeout
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - install-time guard
        raise ScrapeError(
            "Playwright is not installed. Run: uv sync && uv run playwright install chromium"
        ) from exc

    captured: dict[str, dict] = {}
    reg_items_re = re.compile(r"/reg_items(\b|/|\?|$)")

    def on_response(response) -> None:
        """Capture item dicts from any ``reg_items`` GET response into ``captured``.

        Parameters
        ----------
        response : playwright.sync_api.Response
            A network response observed by the page. Non-matching, non-GET or non-JSON
            responses are ignored.
        """
        if not reg_items_re.search(response.url):
            return
        if response.request.method != "GET":
            return
        try:
            data = response.json()
        except Exception:  # noqa: BLE001 - any decode/transport error: skip this response
            return
        for item in _reg_items_from_payload(data):
            key = str(item.get("id") or item.get("uuid") or id(item))
            captured[key] = item

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=cfg.headless)
        except Exception as exc:  # noqa: BLE001 - typically missing browser binary
            raise ScrapeError(
                "Could not launch Chromium. Run: uv run playwright install chromium"
            ) from exc

        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        page.on("response", on_response)

        timeout_ms = cfg.timeout_seconds * 1000
        try:
            page.goto(registry.url, wait_until="networkidle", timeout=timeout_ms)
        except PWTimeout:
            pass  # networkidle can time out on chatty pages; we may still have items

        _scroll_until_loaded(page, registry, captured, deadline_s=cfg.timeout_seconds)
        browser.close()

    return list(captured.values())


def _scroll_until_loaded(
    page,
    registry: Registry,
    captured: dict,
    *,
    deadline_s: int,
) -> None:
    """Scroll the page to trigger lazy loading until the item count settles or times out.

    Stops early once the number of captured items reaches the registry's expected count, or
    after several scrolls produce no new items.

    Parameters
    ----------
    page : playwright.sync_api.Page
        The page to scroll. Its response handler populates ``captured`` as a side effect.
    registry : Registry
        Registry metadata, used for the expected item count.
    captured : dict
        The shared mapping of item id to item dict populated by the response handler.
    deadline_s : int
        Maximum time to keep scrolling, in seconds.

    Returns
    -------
    None
        This function mutates ``captured`` via the page's response handler and returns
        nothing.
    """
    target = registry.reg_items_count or 0
    start = time.monotonic()
    last_count = -1
    stable_rounds = 0
    while time.monotonic() - start < deadline_s:
        if target and len(captured) >= target:
            break
        page.mouse.wheel(0, 20000)
        page.wait_for_timeout(1000)
        count = len(captured)
        if count == last_count:
            stable_rounds += 1
            if stable_rounds >= 3 and count > 0:
                break  # no new items after several scrolls
        else:
            stable_rounds = 0
        last_count = count


def scrape_registry(url: str, cfg: ScraperConfig) -> tuple[Registry, list[dict]]:
    """Resolve registry metadata and fetch its gift items.

    Convenience wrapper that chains :func:`resolve_registry` and :func:`fetch_reg_items`.

    Parameters
    ----------
    url : str
        A Babylist registry link or bare slug.
    cfg : ScraperConfig
        Browser behaviour settings, also used for the metadata request timeout.

    Returns
    -------
    tuple of (Registry, list of dict)
        The resolved registry metadata and the raw (unmapped) item dictionaries.

    Raises
    ------
    ScrapeError
        Propagated from :func:`resolve_registry` or :func:`fetch_reg_items`.
    """
    registry = resolve_registry(url, timeout=cfg.timeout_seconds)
    items = fetch_reg_items(registry, cfg)
    return registry, items
