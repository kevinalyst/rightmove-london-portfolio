from lxml import html

from rightmove_scraper.extractors import (
    get_title,
    get_summary_panel_value,
    get_key_features,
    get_description,
    get_fact_value,
)
from rightmove_scraper.normalize import coerce_int, normalize_tenure, normalize_council_tax


def _load_fixture(name: str):
    with open(f"tests/fixtures/html/{name}", "r", encoding="utf-8") as f:
        content = f.read()
    return html.fromstring(content)


def test_integration_snapshot1():
    doc = _load_fixture("sample_listing_1.html")
    title = get_title(doc)
    ptype = get_summary_panel_value(doc, "PROPERTY TYPE")
    beds = coerce_int(get_summary_panel_value(doc, "BEDROOMS"))
    baths = coerce_int(get_summary_panel_value(doc, "BATHROOMS"))
    size = get_summary_panel_value(doc, "SIZE")
    tenure = normalize_tenure(get_summary_panel_value(doc, "TENURE"))
    kf = get_key_features(doc)
    desc = get_description(doc)
    council = normalize_council_tax(get_fact_value(doc, "COUNCIL TAX"))

    assert title is None or isinstance(title, str)
    assert ptype is None or isinstance(ptype, str)
    assert beds is None or isinstance(beds, int)
    assert baths is None or isinstance(baths, int)
    assert size is None or isinstance(size, str)
    assert tenure is None or isinstance(tenure, str)
    assert isinstance(kf, list)
    assert desc is None or isinstance(desc, str)
    assert council is None or isinstance(council, str)


