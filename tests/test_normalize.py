from rightmove_scraper.normalize import coerce_int, normalize_tenure, normalize_council_tax


def test_coerce_int():
    assert coerce_int("3 bedrooms") == 3
    assert coerce_int("1,234 sq ft") == 1234
    assert coerce_int(None) is None


def test_normalize_tenure():
    assert normalize_tenure("Freehold") == "Freehold"
    assert normalize_tenure("Leasehold (125 years)") == "Leasehold"
    assert normalize_tenure(None) is None


def test_normalize_council_tax():
    assert normalize_council_tax("Band: B") == "B"
    assert normalize_council_tax("Ask agent") == "Ask agent"
    assert normalize_council_tax(None) is None


