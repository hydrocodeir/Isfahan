#!/usr/bin/env python3
"""Supplement title discovery with Crossref bibliographic/abstract queries."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

from deep_literature_search import REPORTS, USER_AGENT, classify_scope, save_json


QUERIES = [
    "Zayandeh Rud", "Zayandeh Rood", "Zayanderud", "Zayandehrud",
    "Gavkhouni", "Gavkhuni", "Karun River", "Karun Basin", "Karoun River",
    "Kuhrang water", "Kouhrang water", "Koohrang water",
    "Beheshtabad water", "Behesht-Abad water", "Cheshmeh Langan water",
    "Khersan 3 water", "Mandegan water", "Ben Borujen water",
    "inter-basin water transfer Iran", "interbasin water transfer Iran",
    "زاینده رود", "کارون", "کوهرنگ", "بهشت آباد", "گاوخونی",
]


def text_only(value: str | None) -> str:
    return re.sub(r"<[^>]+>", " ", value or "")


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    records, log = [], []
    for query in QUERIES:
        status, items = None, []
        for attempt in range(5):
            try:
                response = session.get(
                    "https://api.crossref.org/works",
                    params={
                        "query.bibliographic": query,
                        "rows": 300,
                        "select": "DOI,title,author,published,published-online,publisher,container-title,URL,link,type,abstract",
                        "mailto": "research@example.com",
                    },
                    timeout=(10, 60),
                )
                status = response.status_code
                if status == 429:
                    time.sleep(2 ** (attempt + 1))
                    continue
                if status == 200:
                    items = (response.json().get("message") or {}).get("items") or []
                break
            except requests.RequestException:
                time.sleep(2 ** attempt)
        found = 0
        for item in items:
            if item.get("type") not in {"journal-article", "proceedings-article", "posted-content"}:
                continue
            title = (item.get("title") or [None])[0]
            abstract = text_only(item.get("abstract"))
            scope, hits = classify_scope(" ".join(filter(None, (title, abstract))))
            if not scope:
                continue
            parts = (((item.get("published-online") or item.get("published") or {}).get("date-parts") or [[]])[0])
            date_value = "-".join(str(x).zfill(2) if i else str(x) for i, x in enumerate(parts)) if parts else None
            links = item.get("link") or []
            pdf = next((x.get("URL") for x in links if "pdf" in (x.get("content-type") or "").lower()), None)
            records.append({
                "title": title,
                "authors": [" ".join(filter(None, (a.get("given"), a.get("family")))) for a in item.get("author") or []],
                "publication_date": date_value,
                "year": parts[0] if parts else None,
                "language": item.get("language"),
                "journal": (item.get("container-title") or [None])[0],
                "publisher": item.get("publisher"),
                "doi": item.get("DOI"),
                "landing_url": item.get("URL"),
                "pdf_url": pdf,
                "abstract": abstract or None,
                "source_id": item.get("DOI"),
                "source_database": "Crossref bibliographic",
                "indexed_in": ["crossref"],
                "query": query,
                "scope": scope,
                "term_hits": hits,
                "biblio": {},
                "match_location": "title/abstract/bibliographic metadata",
            })
            found += 1
        log.append({"database": "Crossref bibliographic", "query": query, "status": status, "found": found})
        print(query, status, found, flush=True)
        time.sleep(0.25)
    save_json(REPORTS / "crossref_abstract_search.json", {"records": records, "log": log})
    print(f"Total retained hits: {len(records)}")


if __name__ == "__main__":
    main()
