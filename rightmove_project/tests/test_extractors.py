from lxml import html

from rightmove_scraper.extractors import (
    get_title,
    get_price_text,
    get_summary_panel_value,
    get_key_features,
    get_description,
    get_fact_value,
)


def _load_fixture(name: str):
    with open(f"tests/fixtures/html/{name}", "r", encoding="utf-8") as f:
        content = f.read()
    return html.fromstring(content)


def test_extract_basic_fields_snapshot1():
    doc = _load_fixture("sample_listing_1.html")
    assert get_title(doc) is not None
    assert get_price_text(doc) is None or isinstance(get_price_text(doc), str)
    # These may be None depending on snapshot, just smoke-call
    get_summary_panel_value(doc, "PROPERTY TYPE")
    get_key_features(doc)
    get_description(doc)
    get_fact_value(doc, "COUNCIL TAX")


