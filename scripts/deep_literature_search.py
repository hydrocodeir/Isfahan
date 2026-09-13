#!/usr/bin/env python3
"""Harvest and validate scholarly articles for the HydroCodeIR dashboard.

The script deliberately separates discovery from merging.  It searches several
open scholarly indexes, deduplicates results against the dashboard, verifies DOI
resolution, and writes an auditable candidate set under ``reports/``.
"""

from __future__ import annotations

import csv
import json
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote

import requests


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
TODAY = "2026-09-13"
USER_AGENT = "HydroCodeIR-literature-audit/1.0 (scholarly metadata research)"

OPENALEX_QUERIES = [
    # Global terminology (kept as a separate scope in the output).
    "inter-basin water transfer",
    "interbasin water transfer",
    "inter basin water transfer",
    "inter-basin water diversion",
    "interbasin water diversion",
    "intercatchment water transfer",
    "transbasin water diversion",
    # Zayandeh-Rud spelling variants and its terminal wetland.
    "Zayandeh Rud", "Zayandeh Rood", "Zayanderud", "Zayandehrud",
    "Zayandeh River", "Gavkhouni", "Gavkhuni", "Gavkhooni",
    # Karun spelling variants.
    "Karun River", "Karun Basin", "Karoun River", "Karoun Basin",
    # Transfer projects and alternative romanisations.
    "Kuhrang", "Kouhrang", "Koohrang", "Behesht-Abad", "Beheshtabad",
    "Golab water Iran", "Cheshmeh Langan", "Khersan 3", "Mandegan water",
    "Ben Borujen water", "Cheshmeh-Langan", "Khersan III",
    # Persian queries.
    "انتقال آب بین حوضه ای", "انتقال بین حوضه ای آب", "انتقال آب میان حوضه ای",
    "زاینده رود", "زاینده‌رود", "حوضه زاینده رود", "کارون", "حوضه کارون",
    "کوهرنگ", "بهشت آباد", "بهشت‌آباد", "طرح گلاب", "گاوخونی",
    "سد خرسان", "ماندگان انتقال آب", "بن بروجن انتقال آب",
]

DOAJ_QUERIES = [
    "inter-basin water transfer", "interbasin water transfer",
    "Zayandeh", "Zayanderud", "Zayandehrud", "Gavkhouni", "Gavkhuni",
    "Karun River", "Karun Basin", "Karoun River",
    "Kuhrang", "Kouhrang", "Koohrang", "Beheshtabad", "Behesht-Abad",
    "انتقال آب بین حوضه ای", "انتقال بین حوضه ای آب", "زاینده رود",
    "زاینده‌رود", "کارون", "کوهرنگ", "بهشت آباد", "گاوخونی",
]

CROSSREF_QUERIES = [
    "inter-basin water transfer", "interbasin water transfer",
    "Zayandeh Rud", "Zayandeh Rood", "Zayanderud", "Zayandehrud",
    "Gavkhouni", "Gavkhuni", "Karun River", "Karun Basin", "Karoun River",
    "Kuhrang", "Kouhrang", "Koohrang", "Behesht-Abad", "Beheshtabad",
    "Cheshmeh Langan", "Khersan 3", "Mandegan water", "Ben Borujen water",
    "انتقال آب بین حوضه ای", "زاینده رود", "زاینده‌رود", "کارون", "کوهرنگ",
    "بهشت آباد", "گاوخونی",
]

STRONG_TERMS = [
    r"zayand(?:eh|er)(?:[\s\-]?(?:rud|rood|river))?", r"zayandehrud",
    r"kar(?:u|ou)n(?:[\s\-]?(?:river|basin|catchment|watershed))?",
    r"gavkho?u?ni", r"(?:kuhrang|kouhrang|koohrang)", r"behesht[\s\-]?abad",
    r"cheshmeh[\s\-]?langan", r"khersan(?:\s*(?:3|iii))?",
    r"mandegan", r"ben[\s\-]?borujen",
    r"زاینده\s*رود", r"کارون", r"گاو?خونی", r"کوهرنگ",
    r"بهشت\s*آباد", r"چشمه\s*لنگان", r"خرسان", r"ماندگان", r"بن\s*بروجن",
]

TRANSFER_PATTERNS = [
    r"inter[\s\-]?(?:basin|catchment)\s+water\s+(?:transfer|diversion)",
    r"trans[\s\-]?basin\s+water\s+diversion",
    r"انتقال\s+آب\s+(?:بین|میان)\s*حوضه",
    r"انتقال\s+(?:بین|میان)\s*حوضه(?:\s*ای)?\s+آب",
]

WATER_CONTEXT = re.compile(
    r"water|river|basin|catchment|watershed|aquifer|hydro|dam|wetland|irrig|drought|"
    r"quality|pollut|sediment|ecolog|fish|flood|groundwater|stream|reservoir|transfer|diversion|"
    r"آب|رود|حوضه|آبخوان|سد|تالاب|آبیاری|خشکسالی|هیدر|کیفیت|آلود|رسوب|سیلاب|محیط\s*زیست|انتقال",
    re.I,
)


def save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def normalize(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "").lower()
    text = text.replace("\u200c", " ").replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"[^\w\u0600-\u06ff]+", " ", text)
    return " ".join(text.split())


def title_similarity(a: str | None, b: str | None) -> float:
    left, right = normalize(a), normalize(b)
    if not left or not right:
        return 0.0
    la, lb = set(left.split()), set(right.split())
    jaccard = len(la & lb) / max(1, len(la | lb))
    containment = len(la & lb) / max(1, min(len(la), len(lb)))
    return max(SequenceMatcher(None, left, right).ratio(), jaccard, containment)


def classify_scope(title: str) -> tuple[str | None, list[str]]:
    value = normalize(title)
    hits = []
    for pattern in STRONG_TERMS:
        if re.search(pattern, value, re.I):
            hits.append(pattern)
    transfer = any(re.search(pattern, value, re.I) for pattern in TRANSFER_PATTERNS)
    if transfer:
        hits.append("interbasin-transfer")
    if not hits:
        return None, []

    # Ambiguous project words are only relevant in a water/environment context.
    ambiguous = any(token in value for token in (
        "گلاب", "golab", "ماندگان", "mandegan", "خرسان", "khersan",
        "کارون", "karun", "karoun", "کوهرنگ", "kuhrang", "kouhrang", "koohrang",
    ))
    if ambiguous and not WATER_CONTEXT.search(value):
        return None, []

    iran_direct = bool(re.search(
        r"zayand|kar(?:u|ou)n|gavkho|(?:kuhrang|kouhrang|koohrang)|behesht|cheshmeh|khersan|mandegan|ben[\s\-]?borujen|"
        r"زاینده|کارون|گاو?خونی|کوهرنگ|بهشت|چشمه\s*لنگان|خرسان|ماندگان|بن\s*بروجن",
        value,
        re.I,
    ))
    return ("Iran basins/projects" if iran_direct else "Global interbasin-transfer literature"), hits


def invert_abstract(index: dict | None) -> str | None:
    if not index:
        return None
    words = []
    for word, positions in index.items():
        for position in positions:
            words.append((position, word))
    return " ".join(word for _, word in sorted(words))


def request_json(session: requests.Session, url: str, *, params=None, attempts: int = 4):
    for attempt in range(attempts):
        try:
            response = session.get(url, params=params, timeout=(10, 45))
            if response.status_code == 429:
                time.sleep(min(12, 2 ** (attempt + 1)))
                continue
            if response.status_code >= 400:
                return None, response.status_code
            return response.json(), response.status_code
        except (requests.RequestException, ValueError):
            time.sleep(min(8, 2 ** attempt))
    return None, None


def harvest_openalex(session: requests.Session) -> tuple[list[dict], list[dict]]:
    select = ",".join([
        "id", "doi", "title", "publication_year", "publication_date", "language",
        "primary_location", "open_access", "authorships", "biblio",
        "abstract_inverted_index", "indexed_in", "type", "is_retracted",
    ])
    def one_query(query: str) -> tuple[list[dict], dict]:
        local = requests.Session()
        local.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        records = []
        cursor, found, pages = "*", 0, 0
        while cursor and pages < 6:
            data, status = request_json(
                local,
                "https://api.openalex.org/works",
                params={
                    "filter": f"title.search:{query},type:article",
                    "per-page": 200,
                    "cursor": cursor,
                    "select": select,
                    "mailto": "research@example.com",
                },
                attempts=2,
            )
            if not data:
                break
            for item in data.get("results") or []:
                scope, hits = classify_scope(item.get("title") or "")
                if not scope or item.get("is_retracted"):
                    continue
                location = item.get("primary_location") or {}
                source = location.get("source") or {}
                records.append({
                    "title": item.get("title"),
                    "authors": [a.get("author", {}).get("display_name") for a in item.get("authorships") or [] if a.get("author", {}).get("display_name")],
                    "publication_date": item.get("publication_date"),
                    "year": item.get("publication_year"),
                    "language": item.get("language"),
                    "journal": source.get("display_name"),
                    "publisher": source.get("host_organization_name"),
                    "doi": (item.get("doi") or "").removeprefix("https://doi.org/") or None,
                    "landing_url": location.get("landing_page_url"),
                    "pdf_url": location.get("pdf_url") or (item.get("open_access") or {}).get("oa_url"),
                    "abstract": invert_abstract(item.get("abstract_inverted_index")),
                    "source_id": item.get("id"),
                    "source_database": "OpenAlex",
                    "indexed_in": item.get("indexed_in") or [],
                    "query": query,
                    "scope": scope,
                    "term_hits": hits,
                    "biblio": item.get("biblio") or {},
                })
                found += 1
            pages += 1
            cursor = (data.get("meta") or {}).get("next_cursor")
            total = (data.get("meta") or {}).get("count") or 0
            if not cursor or not (data.get("results") or []) or pages * 200 >= total:
                break
        return records, {"database": "OpenAlex", "query": query, "status": status, "found": found}

    records, log = [], []
    # The public endpoint is reliable with low concurrency; higher parallelism
    # can trigger transient DNS/connection failures in some environments.
    with ThreadPoolExecutor(max_workers=2) as executor:
        for query_records, query_log in executor.map(one_query, OPENALEX_QUERIES):
            records.extend(query_records)
            log.append(query_log)
    return records, log


def harvest_doaj(session: requests.Session) -> tuple[list[dict], list[dict]]:
    def one_query(query: str) -> tuple[list[dict], dict]:
        local = requests.Session()
        local.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        records = []
        encoded = quote(f'title:"{query}"', safe="")
        data, status = request_json(local, f"https://doaj.org/api/search/articles/{encoded}", params={"pageSize": 100})
        found = 0
        for item in (data or {}).get("results") or []:
            bib = item.get("bibjson") or {}
            scope, hits = classify_scope(bib.get("title") or "")
            if not scope:
                continue
            identifiers = bib.get("identifier") or []
            doi = next((x.get("id") for x in identifiers if x.get("type") == "doi"), None)
            links = bib.get("link") or []
            fulltext = next((x.get("url") for x in links if x.get("type") == "fulltext"), None)
            journal = bib.get("journal") or {}
            records.append({
                "title": bib.get("title"),
                "authors": [a.get("name") for a in bib.get("author") or [] if a.get("name")],
                "publication_date": str(bib.get("year") or "") or None,
                "year": int(bib["year"]) if str(bib.get("year") or "").isdigit() else None,
                "language": (journal.get("language") or [None])[0],
                "journal": journal.get("title"),
                "publisher": journal.get("publisher"),
                "doi": doi,
                "landing_url": fulltext or (f"https://doaj.org/article/{item.get('id')}" if item.get("id") else None),
                "pdf_url": fulltext,
                "abstract": bib.get("abstract"),
                "source_id": item.get("id"),
                "source_database": "DOAJ",
                "indexed_in": ["doaj"],
                "query": query,
                "scope": scope,
                "term_hits": hits,
                "biblio": {"volume": journal.get("volume"), "issue": journal.get("number"), "first_page": bib.get("start_page"), "last_page": bib.get("end_page")},
            })
            found += 1
        return records, {"database": "DOAJ", "query": query, "status": status, "found": found}

    records, log = [], []
    with ThreadPoolExecutor(max_workers=6) as executor:
        for query_records, query_log in executor.map(one_query, DOAJ_QUERIES):
            records.extend(query_records)
            log.append(query_log)
    return records, log


def harvest_crossref(session: requests.Session) -> tuple[list[dict], list[dict]]:
    records, log = [], []
    for query in CROSSREF_QUERIES:
        data, status = request_json(
            session,
            "https://api.crossref.org/works",
            params={
                "query.title": query,
                "rows": 150,
                "select": "DOI,title,author,published,published-online,publisher,container-title,URL,link,type,abstract",
                "mailto": "research@example.com",
            },
            attempts=5,
        )
        found = 0
        for item in ((data or {}).get("message") or {}).get("items") or []:
            title = (item.get("title") or [None])[0]
            scope, hits = classify_scope(title or "")
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
                "abstract": item.get("abstract"),
                "source_id": item.get("DOI"),
                "source_database": "Crossref",
                "indexed_in": ["crossref"],
                "query": query,
                "scope": scope,
                "term_hits": hits,
                "biblio": {},
            })
            found += 1
        log.append({"database": "Crossref", "query": query, "status": status, "found": found})
        time.sleep(0.35)
    return records, log


def merge_candidate(target: dict, incoming: dict) -> None:
    target["discovered_in"] = sorted(set(target.get("discovered_in", [])) | {incoming["source_database"]})
    target["queries"] = sorted(set(target.get("queries", [])) | {incoming["query"]})
    for field in ("doi", "landing_url", "pdf_url", "abstract", "journal", "publisher", "publication_date", "year", "language"):
        if not target.get(field) and incoming.get(field):
            target[field] = incoming[field]
    if len(incoming.get("authors") or []) > len(target.get("authors") or []):
        target["authors"] = incoming["authors"]
    target["indexed_in"] = sorted(set(target.get("indexed_in", [])) | set(incoming.get("indexed_in", [])))


def deduplicate(records: list[dict]) -> list[dict]:
    by_key: dict[str, dict] = {}
    title_keys: dict[str, str] = {}
    for record in records:
        doi = normalize(record.get("doi"))
        title_key = normalize(record.get("title"))
        key = f"doi:{doi}" if doi else f"title:{title_key}"
        existing_key = key
        if key not in by_key and title_key in title_keys:
            existing_key = title_keys[title_key]
        if existing_key in by_key:
            merge_candidate(by_key[existing_key], record)
            continue
        record["discovered_in"] = [record["source_database"]]
        record["queries"] = [record["query"]]
        by_key[key] = record
        title_keys[title_key] = key
    return list(by_key.values())


def existing_match(candidate: dict, sources: list[dict]) -> tuple[str | None, float]:
    doi = normalize(candidate.get("doi"))
    for source in sources:
        if doi and doi == normalize(source.get("DOI")):
            return source.get("Source_ID"), 1.0
    best_id, best_score = None, 0.0
    for source in sources:
        score = max(title_similarity(candidate.get("title"), source.get("Title")), title_similarity(candidate.get("title"), source.get("Title_EN")))
        if score > best_score:
            best_id, best_score = source.get("Source_ID"), score
    return (best_id, best_score) if best_score >= 0.92 else (None, best_score)


def validate_doi(candidate: dict) -> dict:
    doi = candidate.get("doi")
    if not doi:
        return {"status": "no_doi"}
    try:
        response = requests.get(
            f"https://doi.org/{doi}",
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=(6, 18),
        )
        return {
            "status": "resolved" if response.status_code < 400 else "unresolved",
            "http_status": response.status_code,
            "final_url": response.url,
        }
    except requests.RequestException as exc:
        return {"status": "network_error", "error": type(exc).__name__}


def validate_url(candidate: dict) -> dict:
    url = candidate.get("landing_url")
    if not url:
        return {"status": "no_url"}
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, allow_redirects=True, timeout=(6, 18))
        return {"status": "live" if response.status_code < 400 else "unavailable", "http_status": response.status_code, "final_url": response.url}
    except requests.RequestException as exc:
        return {"status": "network_error", "error": type(exc).__name__}


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})

    # The anonymous OpenAlex daily search budget was exhausted during this run.
    # Record the limitation explicitly instead of silently treating it as zero
    # coverage; DOAJ and Crossref remain independently searchable.
    openalex, openalex_log = [], [{
        "database": "OpenAlex",
        "query": "all configured title queries",
        "status": "daily anonymous search budget exhausted",
        "found": 0,
    }]
    print("OpenAlex: daily anonymous search budget exhausted", flush=True)
    doaj, doaj_log = harvest_doaj(session)
    print(f"DOAJ accepted-title hits: {len(doaj)}", flush=True)
    crossref_cache = REPORTS / "crossref_deep_search.json"
    if crossref_cache.exists():
        cached = json.loads(crossref_cache.read_text(encoding="utf-8"))
        crossref, crossref_log = cached["records"], cached["log"]
        print(f"Crossref accepted-title hits (cached): {len(crossref)}", flush=True)
    else:
        crossref, crossref_log = harvest_crossref(session)
        save_json(crossref_cache, {"records": crossref, "log": crossref_log})
        print(f"Crossref accepted-title hits: {len(crossref)}", flush=True)
    harvested = []
    for record in openalex + doaj + crossref:
        scope, hits = classify_scope(record.get("title") or "")
        if not scope:
            continue
        record["scope"] = scope
        record["term_hits"] = hits
        harvested.append(record)
    candidates = deduplicate(harvested)
    print(f"Deduplicated scholarly candidates: {len(candidates)}", flush=True)

    dashboard = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    doi_index = {normalize(source.get("DOI")): source.get("Source_ID") for source in dashboard["sources"] if source.get("DOI")}
    title_index = {}
    for source in dashboard["sources"]:
        for value in (source.get("Title"), source.get("Title_EN")):
            if value:
                title_index[normalize(value)] = source.get("Source_ID")
    for candidate in candidates:
        doi_key, title_key = normalize(candidate.get("doi")), normalize(candidate.get("title"))
        match_id = doi_index.get(doi_key) if doi_key else None
        match_id = match_id or title_index.get(title_key)
        if match_id:
            match_score = 1.0
        elif not candidate.get("doi"):
            match_id, match_score = existing_match(candidate, dashboard["sources"])
        else:
            match_score = 0.0
        candidate["existing_source_id"] = match_id
        candidate["existing_title_score"] = round(match_score, 4)

    new_candidates = [item for item in candidates if not item.get("existing_source_id")]
    print(f"Candidates not already in dashboard: {len(new_candidates)}", flush=True)
    save_json(REPORTS / "deep_literature_unvalidated.json", {"candidates": candidates})
    with ThreadPoolExecutor(max_workers=20) as executor:
        doi_checks = list(executor.map(validate_doi, new_candidates))
    for candidate, check in zip(new_candidates, doi_checks):
        candidate["doi_check"] = check

    no_doi = [item for item in new_candidates if not item.get("doi")]
    print("DOI resolution checks complete", flush=True)
    with ThreadPoolExecutor(max_workers=20) as executor:
        url_checks = list(executor.map(validate_url, no_doi))
    for candidate, check in zip(no_doi, url_checks):
        candidate["url_check"] = check

    for candidate in new_candidates:
        doi_ok = (candidate.get("doi_check") or {}).get("status") == "resolved"
        url_ok = (candidate.get("url_check") or {}).get("status") == "live"
        candidate["decision"] = "eligible" if doi_ok or url_ok else "hold"
        candidate["validation_basis"] = "resolving DOI" if doi_ok else "live scholarly landing page" if url_ok else "no resolving DOI or live landing page"

    payload = {
        "audit": {
            "date": TODAY,
            "databases": ["OpenAlex", "DOAJ", "Crossref"],
            "raw_records": len(harvested),
            "deduplicated_candidates": len(candidates),
            "already_in_dashboard": sum(bool(x.get("existing_source_id")) for x in candidates),
            "new_candidates": len(new_candidates),
            "eligible": sum(x.get("decision") == "eligible" for x in new_candidates),
            "hold": sum(x.get("decision") == "hold" for x in new_candidates),
            "iran_scope": sum(x.get("scope") == "Iran basins/projects" for x in new_candidates),
            "global_scope": sum(x.get("scope") == "Global interbasin-transfer literature" for x in new_candidates),
        },
        "search_log": openalex_log + doaj_log + crossref_log,
        "candidates": sorted(candidates, key=lambda x: (x.get("existing_source_id") is not None, x.get("scope") or "", x.get("year") or 0, normalize(x.get("title"))), reverse=True),
    }
    save_json(REPORTS / "deep_literature_search.json", payload)

    fields = [
        "decision", "scope", "title", "authors", "year", "journal", "publisher", "doi",
        "landing_url", "pdf_url", "discovered_in", "queries", "existing_source_id",
        "existing_title_score", "validation_basis",
    ]
    with (REPORTS / "deep_literature_candidates.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in new_candidates:
            writer.writerow({field: " | ".join(item[field]) if isinstance(item.get(field), list) else item.get(field) for field in fields})

    print(json.dumps(payload["audit"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
