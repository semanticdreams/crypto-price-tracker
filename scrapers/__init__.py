from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, Iterable, List, Protocol, Sequence


@dataclass(frozen=True)
class PriceResult:
    slug: str
    symbol: str
    name: str
    source: str
    raw: str
    price: float
    currency: str
    url: str


class Scraper(Protocol):
    name: str

    def fetch(self) -> Sequence[PriceResult]:
        ...

def merge_results(results: Iterable[tuple[str, Sequence[PriceResult]]]) -> List[PriceResult]:
    merged: List[PriceResult] = []
    for source, data in results:
        for entry in data:
            merged.append(replace(entry, source=source))
    return merged


def list_sources(scrapers: Iterable[Scraper]) -> List[str]:
    return [scraper.name for scraper in scrapers]
