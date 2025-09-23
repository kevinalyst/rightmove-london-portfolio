import asyncio

from scraper.src.slicer.interfaces import Slice, partition


class _Counter:
    def __init__(self, n: int):
        self.n = n

    async def count(self, location_identifier: str, *, min_price, max_price, query, property_type):
        return self.n


def test_partition_under_cap_returns_input():
    s = Slice(level="district", name="E14", location_identifier="OUTCODE^E14", price_min=300000, price_max=450000)
    out = asyncio.run(partition(s, result_counter=_Counter(100), district_provider=None, query="", property_type=None))
    assert out == [s]


def test_partition_over_cap_splits_price():
    s = Slice(level="district", name="E14", location_identifier="OUTCODE^E14", price_min=0, price_max=100)
    out = asyncio.run(partition(s, result_counter=_Counter(2000), district_provider=None, query="", property_type=None))
    assert len(out) == 2
    assert out[0].price_min == 0 and out[0].price_max == 50
    assert out[1].price_min == 50 and out[1].price_max == 100


