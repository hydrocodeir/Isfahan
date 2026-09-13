#!/usr/bin/env python3
"""Audit Antigravity-generated sources against live web evidence.

The audit is intentionally conservative.  A record is accepted only when a live
landing page, DOI registry record, or an independently indexed search result
substantially matches the supplied title.  Every decision retains machine-readable
evidence so the data merge can be reproduced and reviewed.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import html
import io
import json
import re
import sys
import threading
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, urlparse
from urllib.parse import unquote

import requests
import urllib3
from bs4 import BeautifulSoup
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "new_data.json"
RESULTS = ROOT / "reports" / "source_validation_results.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
)
MAX_HTML_BYTES = 2_000_000
MAX_PDF_BYTES = 16_000_000
HTTP_TIMEOUT = (12, 28)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_thread_local = threading.local()
_print_lock = threading.Lock()


PERSIAN_TRANSLATION = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ة": "ه",
        "ۀ": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "ٱ": "ا",
        "‌": " ",  # ZWNJ
        "ـ": "",
    }
)

STOPWORDS = {
    # Persian title boilerplate
    "آب", "آبی", "ای", "از", "است", "اثر", "اثرات", "ارائه", "ارزیابی", "استان",
    "استانی", "استفاده", "انتقال", "این", "با", "بر", "برای", "بررسی", "به", "بین",
    "پیامد", "پیامدهای", "تحلیل", "تحلیلی", "تبیین", "توسعه", "در", "درباره", "را",
    "راهکار", "رود", "رودخانه", "سال", "سامانه", "شهر", "شهرستان", "شرایط", "طرح",
    "عنوان", "علی", "فرایند", "فنی", "گزارش", "مطالعه", "مدیریت", "مدل", "مورد",
    "منابع", "منطقه", "نقش", "و", "یا", "یک", "های", "هایی", "حوضه",
    # English title boilerplate
    "a", "an", "and", "analysis", "assessment", "based", "case", "effects", "evaluation",
    "for", "from", "in", "iran", "of", "on", "study", "the", "to", "using", "water", "with",
}

SOFT_404_MARKERS = (
    "page not found",
    "404 not found",
    "خطای 404",
    "صفحه مورد نظر یافت نشد",
    "صفحه یافت نشد",
    "مطلب مورد نظر یافت نشد",
    "the requested url was not found",
)

CHALLENGE_MARKERS = (
    "just a moment",
    "checking your browser",
    "transferring to the website",
    "در حال انتقال به سایت مورد نظر",
    "cf-chl-",
)

KNOWN_TRUSTED_DOMAINS = {
    "civilica.com", "sid.ir", "magiran.com", "doi.org", "link.springer.com",
    "sciencedirect.com", "researchgate.net", "irna.ir", "isna.ir", "mehrnews.com",
    "tasnimnews.com", "ilna.ir", "farsnews.ir", "icana.ir", "khabaronline.ir",
    "imna.ir", "tabnak.ir", "asriran.com", "donya-e-eqtesad.com", "sharghdaily.com",
    "etemadnewspaper.ir", "hammihanonline.ir", "jamaran.news", "yjc.ir",
}

# A search index contained the title, but the only recovered URL did not resolve
# during repeated direct checks and no second copy was found.
MANUAL_REJECTIONS = {
    "S524": "Indexed title found, but the recovered source URL was unavailable and no live alternative link was found.",
}


@dataclass
class FetchResult:
    requested_url: str
    final_url: str | None = None
    status: int | None = None
    content_type: str | None = None
    page_title: str | None = None
    body_excerpt: str | None = None
    outcome: str = "error"
    error: str | None = None


def log(message: str) -> None:
    with _print_lock:
        print(message, flush=True)


def session() -> requests.Session:
    if not hasattr(_thread_local, "session"):
        s = requests.Session()
        s.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
                "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
            }
        )
        _thread_local.session = s
    return _thread_local.session


def normalize(text: Any) -> str:
    if text is None:
        return ""
    value = html.unescape(str(text)).translate(PERSIAN_TRANSLATION).lower()
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"[\u064b-\u065f\u0670]", "", value)
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    value = re.sub(r"_+", " ", value)
    return " ".join(value.split())


def meaningful_tokens(text: Any) -> list[str]:
    return [
        token
        for token in normalize(text).split()
        if len(token) >= 3 and token not in STOPWORDS and not token.isdigit()
    ]


def title_similarity(expected: Any, observed: Any) -> tuple[float, dict[str, float | int]]:
    a = normalize(expected)
    b = normalize(observed)
    if not a or not b:
        return 0.0, {"sequence": 0.0, "containment": 0.0, "jaccard": 0.0, "common": 0}
    ta, tb = set(meaningful_tokens(a)), set(meaningful_tokens(b))
    common = ta & tb
    seq = SequenceMatcher(None, a, b).ratio()
    containment = len(common) / max(1, min(len(ta), len(tb)))
    jaccard = len(common) / max(1, len(ta | tb))
    score = max(seq, 0.58 * containment + 0.42 * jaccard)
    # A single generic shared token must not validate a record.
    if len(common) < 2:
        score = min(score, 0.34)
    elif len(common) == 2:
        score = min(score, 0.54)
    return round(score, 4), {
        "sequence": round(seq, 4),
        "containment": round(containment, 4),
        "jaccard": round(jaccard, 4),
        "common": len(common),
        "expected_coverage": round(len(common) / max(1, len(ta)), 4),
    }


def best_similarity(source: dict[str, Any], observed: Any) -> tuple[float, str, dict[str, Any]]:
    candidates = [("Title", source.get("Title")), ("Title_EN", source.get("Title_EN"))]
    scored: list[tuple[float, str, dict[str, Any]]] = []
    for field, expected in candidates:
        if expected:
            score, details = title_similarity(expected, observed)
            scored.append((score, field, details))
    return max(scored, default=(0.0, "Title", {}), key=lambda item: item[0])


def root_domain(url: str | None) -> str:
    if not url:
        return ""
    host = urlparse(url).netloc.lower().split("@")[(-1)].split(":")[0]
    return host[4:] if host.startswith("www.") else host


def trusted_domain(url: str | None) -> bool:
    domain = root_domain(url)
    return bool(
        domain.endswith(".gov.ir")
        or domain.endswith(".ac.ir")
        or domain.endswith(".edu")
        or domain.endswith(".edu.ir")
        or domain in KNOWN_TRUSTED_DOMAINS
        or any(domain.endswith("." + known) for known in KNOWN_TRUSTED_DOMAINS)
    )


def is_listing_or_search_page(url: str | None, title: str | None = None) -> bool:
    if not url:
        return True
    parsed = urlparse(url)
    path = parsed.path.lower().rstrip("/")
    query = parsed.query.lower()
    normalized_title = normalize(title)
    path_markers = ("/search", "/tag/", "/tags/", "/category/", "/categories/", "/teachers", "/authors")
    return bool(
        any(marker in path for marker in path_markers)
        or re.search(r"(^|&)(q|query|s|search)=", query)
        or normalized_title.startswith(("جستجو ", "جست وجو ", "نتایج جستجو ", "search results "))
    )


def extract_page_title(content: bytes, encoding: str | None) -> tuple[str, str]:
    try:
        text = content.decode(encoding or "utf-8", errors="replace")
    except LookupError:
        text = content.decode("utf-8", errors="replace")
    soup = BeautifulSoup(text, "html.parser")
    candidates: list[str] = []
    for attrs in (
        {"property": "og:title"},
        {"name": "twitter:title"},
        {"name": "citation_title"},
        {"name": "dc.title"},
    ):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            candidates.append(tag["content"])
    for tag_name in ("h1", "title"):
        tag = soup.find(tag_name)
        if tag:
            candidates.append(tag.get_text(" ", strip=True))
    title = max((" ".join(c.split()) for c in candidates if c.strip()), key=len, default="")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    body = " ".join(soup.get_text(" ", strip=True).split())
    return title[:1200], body[:12000]


def fetch_url(url: str) -> FetchResult:
    result = FetchResult(requested_url=url)
    if not url or not url.lower().startswith(("http://", "https://")):
        result.outcome = "invalid_url"
        return result
    try:
        response = session().get(url, timeout=HTTP_TIMEOUT, allow_redirects=True, stream=True)
        result.status = response.status_code
        result.final_url = response.url
        result.content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        appears_pdf = "pdf" in (result.content_type or "") or urlparse(response.url).path.lower().endswith(".pdf")
        byte_limit = MAX_PDF_BYTES if appears_pdf else MAX_HTML_BYTES
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_content(chunk_size=65_536):
            chunks.append(chunk)
            size += len(chunk)
            if size >= byte_limit:
                break
        content = b"".join(chunks)
        if response.status_code >= 400:
            result.outcome = "http_error"
            result.error = f"HTTP {response.status_code}"
            return result
        if "pdf" in (result.content_type or "") or content.startswith(b"%PDF"):
            result.outcome = "live_pdf"
            filename = Path(urlparse(result.final_url or url).path).name
            result.page_title = filename
            try:
                reader = PdfReader(io.BytesIO(content), strict=False)
                metadata_title = (reader.metadata.title if reader.metadata else None) or ""
                extracted: list[str] = []
                for page in reader.pages[:6]:
                    extracted.append(page.extract_text() or "")
                    if sum(len(part) for part in extracted) >= 16_000:
                        break
                pdf_text = " ".join(" ".join(extracted).split())[:16_000]
                if metadata_title.strip():
                    result.page_title = " ".join(metadata_title.split())[:1200]
                result.body_excerpt = pdf_text or None
            except Exception as exc:
                result.error = f"PDF parse warning: {type(exc).__name__}: {str(exc)[:220]}"
            return result
        title, body = extract_page_title(content, response.encoding or response.apparent_encoding)
        result.page_title = title or None
        result.body_excerpt = body or None
        normalized_probe = normalize((title or "") + " " + (body[:1500] if body else ""))
        if any(marker in normalized_probe for marker in SOFT_404_MARKERS):
            result.outcome = "soft_404"
        elif any(marker in normalized_probe for marker in CHALLENGE_MARKERS):
            result.outcome = "challenge"
        elif len(normalized_probe) < 40:
            result.outcome = "empty"
        else:
            result.outcome = "live_html"
        return result
    except requests.RequestException as exc:
        result.error = f"{type(exc).__name__}: {str(exc)[:300]}"
        result.outcome = "network_error"
        return result


def crossref_lookup(doi: str) -> dict[str, Any]:
    url = "https://api.crossref.org/works/" + quote(doi, safe="")
    try:
        response = session().get(url, timeout=HTTP_TIMEOUT)
        if response.status_code == 404:
            return {"status": "not_registered", "http_status": 404, "url": url}
        response.raise_for_status()
        message = response.json().get("message", {})
        title = " ".join(message.get("title") or [])
        published = message.get("published-print") or message.get("published-online") or message.get("issued") or {}
        date_parts = (published.get("date-parts") or [[]])[0]
        return {
            "status": "registered",
            "http_status": response.status_code,
            "url": message.get("URL") or f"https://doi.org/{doi}",
            "title": title,
            "publisher": message.get("publisher"),
            "year": date_parts[0] if date_parts else None,
            "authors": [
                " ".join(filter(None, (author.get("given"), author.get("family"))))
                for author in message.get("author", [])
            ],
            "type": message.get("type"),
        }
    except (requests.RequestException, ValueError) as exc:
        return {"status": "lookup_error", "url": url, "error": f"{type(exc).__name__}: {str(exc)[:300]}"}


def candidate_urls(source: dict[str, Any]) -> list[str]:
    values = [source.get("Canonical_URL"), source.get("URL"), source.get("PDF_URL")]
    if source.get("DOI"):
        values.insert(0, f"https://doi.org/{source['DOI']}")
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def brave_search(query: str) -> dict[str, Any]:
    url = "https://search.brave.com/search?q=" + quote(query)
    try:
        response = session().get(url, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        results: list[dict[str, str]] = []
        for snippet in soup.select('div.snippet[data-type="web"]'):
            anchor = snippet.select_one("a.l1[href]") or snippet.select_one("a[href]")
            if not anchor:
                continue
            title_node = snippet.select_one(".search-snippet-title")
            title = ""
            if title_node:
                title = title_node.get("title") or title_node.get_text(" ", strip=True)
            if not title:
                title = anchor.get_text(" ", strip=True)
            description_node = snippet.select_one(".snippet-description") or snippet.select_one(".generic-snippet")
            description = description_node.get_text(" ", strip=True) if description_node else ""
            href = anchor.get("href", "")
            if href.startswith("http"):
                results.append(
                    {
                        "title": " ".join(title.split())[:1200],
                        "url": href,
                        "description": " ".join(description.split())[:2500],
                    }
                )
        if not results:
            marker = normalize(response.text[:6000])
            status = "rate_limited" if "captcha" in marker or response.status_code == 429 else "no_results"
        else:
            status = "ok"
        return {"status": status, "query": query, "search_url": url, "results": results[:10]}
    except requests.RequestException as exc:
        return {
            "status": "search_error",
            "query": query,
            "search_url": url,
            "results": [],
            "error": f"{type(exc).__name__}: {str(exc)[:300]}",
        }


def yahoo_target_url(href: str) -> str:
    """Decode Yahoo's result redirect while leaving ordinary result URLs intact."""
    match = re.search(r"/RU=([^/]+)/RK=", href)
    if match:
        return unquote(match.group(1))
    return href


def yahoo_search(query: str) -> dict[str, Any]:
    endpoints = (
        "search.yahoo.com",
        "uk.search.yahoo.com",
        "ca.search.yahoo.com",
        "au.search.yahoo.com",
        "sg.search.yahoo.com",
    )
    endpoint = endpoints[sum(ord(char) for char in query) % len(endpoints)]
    url = f"https://{endpoint}/search?p=" + quote(query)
    try:
        response = session().get(url, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        results: list[dict[str, str]] = []
        for item in soup.select("#web ol.reg > li .algo-sr"):
            anchor = item.select_one(".compTitle h3 a[href]")
            if not anchor:
                continue
            clean_anchor = copy.copy(anchor)
            for span in clean_anchor.select("span"):
                span.decompose()
            title = " ".join(clean_anchor.get_text(" ", strip=True).split())
            if title.endswith("...") and anchor.get("aria-label"):
                title = anchor.get("aria-label", title)
            description_node = item.select_one(".compText p")
            description = description_node.get_text(" ", strip=True) if description_node else ""
            href = yahoo_target_url(anchor.get("href", ""))
            if href.startswith("http"):
                results.append(
                    {
                        "title": " ".join(title.split())[:1200],
                        "url": href,
                        "description": " ".join(description.split())[:2500],
                    }
                )
        status = "ok" if results else "no_results"
        return {"status": status, "provider": "Yahoo", "query": query, "search_url": url, "results": results[:10]}
    except requests.RequestException as exc:
        return {
            "status": "search_error",
            "provider": "Yahoo",
            "query": query,
            "search_url": url,
            "results": [],
            "error": f"{type(exc).__name__}: {str(exc)[:300]}",
        }


def evaluate_direct(source: dict[str, Any], fetched: list[FetchResult]) -> dict[str, Any]:
    best: dict[str, Any] | None = None
    for item in fetched:
        if item.outcome == "live_html":
            if is_listing_or_search_page(item.final_url or item.requested_url, item.page_title):
                continue
            title_score, field, details = best_similarity(source, item.page_title or "")
            body_score, body_field, body_details = best_similarity(source, item.body_excerpt or "")
            # Page-title evidence is stronger than a diffuse body match.
            score = max(title_score, min(body_score, 0.72))
            evidence = {
                "url": item.final_url or item.requested_url,
                "title": item.page_title,
                "score": score,
                "title_score": title_score,
                "body_score": body_score,
                "matched_field": field if title_score >= body_score else body_field,
                "score_details": details if title_score >= body_score else body_details,
                "evidence_type": "live_page",
                "trusted_domain": trusted_domain(item.final_url or item.requested_url),
            }
        elif item.outcome == "live_pdf":
            title_score, field, details = best_similarity(source, item.page_title or "")
            body_score, body_field, body_details = best_similarity(source, item.body_excerpt or "")
            score = max(title_score, min(body_score, 0.78))
            evidence = {
                "url": item.final_url or item.requested_url,
                "title": item.page_title,
                "score": score,
                "title_score": title_score,
                "body_score": body_score,
                "matched_field": field if title_score >= body_score else body_field,
                "score_details": details if title_score >= body_score else body_details,
                "evidence_type": "live_pdf",
                "trusted_domain": trusted_domain(item.final_url or item.requested_url),
            }
        else:
            continue
        if best is None or evidence["score"] > best["score"]:
            best = evidence
    return best or {}


def audit_one_search(source: dict[str, Any], max_queries: int, delay: float) -> dict[str, Any]:
    queries: list[str] = []
    for value in (source.get("Title"), source.get("Title_EN")):
        if value and value not in queries:
            queries.append(value)
    searches: list[dict[str, Any]] = []
    best: dict[str, Any] = {}
    for query in queries[:max_queries]:
        search = yahoo_search(query)
        searches.append(search)
        candidate = choose_search_evidence(source, search)
        if candidate and candidate.get("score", 0) > best.get("score", 0):
            best = candidate
        if best.get("title_score", 0) >= 0.72 and best.get("score_details", {}).get("common", 0) >= 3:
            break
        time.sleep(delay)
    return {"searches": searches, "best": best}


def choose_search_evidence(source: dict[str, Any], search: dict[str, Any]) -> dict[str, Any]:
    input_domains = {root_domain(url) for url in candidate_urls(source)}
    best: dict[str, Any] | None = None
    for rank, result in enumerate(search.get("results", []), 1):
        if is_listing_or_search_page(result.get("url"), result.get("title")):
            continue
        title_score, field, details = best_similarity(source, result.get("title"))
        description_score, desc_field, desc_details = best_similarity(source, result.get("description"))
        score = max(title_score, min(description_score, 0.70))
        domain_match = root_domain(result.get("url")) in input_domains
        if domain_match:
            score = min(1.0, score + 0.04)
        evidence = {
            "url": result.get("url"),
            "title": result.get("title"),
            "description": result.get("description"),
            "rank": rank,
            "score": round(score, 4),
            "title_score": title_score,
            "description_score": description_score,
            "matched_field": field if title_score >= description_score else desc_field,
            "score_details": details if title_score >= description_score else desc_details,
            "evidence_type": "search_index",
            "domain_match": domain_match,
            "trusted_domain": trusted_domain(result.get("url")),
        }
        if best is None or evidence["score"] > best["score"]:
            best = evidence
    return best or {}


def decision_from_evidence(source: dict[str, Any], row: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    if source.get("Source_ID") in MANUAL_REJECTIONS:
        return "rejected", MANUAL_REJECTIONS[source["Source_ID"]], row.get("evidence") or {}
    doi_result = row.get("doi_check") or {}
    if doi_result.get("status") == "registered":
        score, matched_field, details = best_similarity(source, doi_result.get("title"))
        doi_result["match_score"] = score
        doi_result["matched_field"] = matched_field
        doi_result["score_details"] = details
        if score >= 0.62 and details.get("expected_coverage", 0) >= 0.50:
            return (
                "accepted",
                "DOI is registered and its bibliographic title matches the supplied record.",
                {
                    "evidence_type": "crossref_doi",
                    "url": doi_result.get("url") or f"https://doi.org/{source['DOI']}",
                    "title": doi_result.get("title"),
                    "score": score,
                    "matched_field": matched_field,
                    "score_details": details,
                    "trusted_domain": True,
                },
            )

    fetched = [FetchResult(**item) for item in row.get("url_checks", [])]
    direct = evaluate_direct(source, fetched)
    details = direct.get("score_details") or {}
    if (
        direct
        and direct.get("title_score", 0) >= 0.58
        and details.get("common", 0) >= 3
        and details.get("expected_coverage", 0) >= 0.50
    ):
        return "accepted", "Supplied URL is live and the page title substantially matches the supplied record.", direct
    if (
        direct
        and direct.get("title_score", 0) >= 0.50
        and direct.get("trusted_domain")
        and details.get("common", 0) >= 4
        and details.get("expected_coverage", 0) >= 0.50
    ):
        return "accepted", "Trusted supplied URL is live with a strong multi-keyword title match.", direct
    if (
        direct
        and direct.get("evidence_type") == "live_pdf"
        and direct.get("body_score", 0) >= 0.62
        and direct.get("trusted_domain")
        and details.get("common", 0) >= 4
        and details.get("expected_coverage", 0) >= 0.55
    ):
        return "accepted", "Trusted live PDF text strongly matches the supplied record.", direct

    best_search: dict[str, Any] = {}
    for search in row.get("search_check") or []:
        candidate = choose_search_evidence(source, search)
        if candidate.get("score", 0) > best_search.get("score", 0):
            best_search = candidate
    details = best_search.get("score_details") or {}
    if (
        best_search
        and best_search.get("title_score", 0) >= 0.66
        and details.get("common", 0) >= 3
        and details.get("expected_coverage", 0) >= 0.50
        and best_search.get("trusted_domain")
    ):
        return "accepted", "Independent search found a trusted, strongly title-matched source page.", best_search
    if (
        best_search
        and best_search.get("title_score", 0) >= 0.74
        and details.get("common", 0) >= 4
        and details.get("expected_coverage", 0) >= 0.62
    ):
        return "accepted", "Independent search found a strongly title-matched source page.", best_search

    if doi_result.get("status") == "not_registered":
        reason = "Supplied DOI is not registered and no independent matching source was found."
    elif any(check.get("outcome") == "soft_404" for check in row.get("url_checks", [])):
        reason = "Supplied page is a soft-404 and no independent matching source was found."
    elif all(
        check.get("outcome") in {"http_error", "network_error", "invalid_url", "soft_404", "empty"}
        for check in row.get("url_checks", [])
    ):
        reason = "Supplied links are unavailable and no independent matching source was found."
    else:
        reason = "Available pages/search results do not substantively match the supplied source title."
    return "rejected", reason, best_search or direct or {}


def audit_one_direct(source: dict[str, Any]) -> dict[str, Any]:
    source_id = source["Source_ID"]
    doi_result: dict[str, Any] | None = None
    if source.get("DOI"):
        doi_result = crossref_lookup(source["DOI"])
        if doi_result.get("status") == "registered":
            score, field, details = best_similarity(source, doi_result.get("title"))
            doi_result.update({"match_score": score, "matched_field": field, "score_details": details})
    fetched = [fetch_url(url) for url in candidate_urls(source)]
    direct = evaluate_direct(source, fetched)

    accepted = False
    evidence: dict[str, Any] = {}
    reason = "No live, title-matched evidence found at supplied URLs."
    if doi_result and doi_result.get("status") == "registered" and doi_result.get("match_score", 0) >= 0.62:
        accepted = True
        evidence = {
            "evidence_type": "crossref_doi",
            "url": doi_result.get("url") or f"https://doi.org/{source['DOI']}",
            "title": doi_result.get("title"),
            "score": doi_result.get("match_score"),
            "matched_field": doi_result.get("matched_field"),
            "score_details": doi_result.get("score_details"),
            "trusted_domain": True,
        }
        reason = "DOI is registered and its bibliographic title matches the supplied record."
    elif direct and direct.get("title_score", 0) >= 0.58 and direct.get("score_details", {}).get("common", 0) >= 3:
        accepted = True
        evidence = direct
        reason = "Supplied URL is live and the page title substantially matches the supplied record."
    elif direct and direct.get("title_score", 0) >= 0.50 and direct.get("trusted_domain") and direct.get("score_details", {}).get("common", 0) >= 4:
        accepted = True
        evidence = direct
        reason = "Trusted supplied URL is live with a strong multi-keyword title match."
    elif direct and direct.get("body_score", 0) >= 0.58 and direct.get("trusted_domain") and direct.get("score_details", {}).get("common", 0) >= 4:
        accepted = True
        evidence = direct
        reason = "Trusted supplied URL is live and its document/body text strongly matches the supplied record."
    return {
        "original_source_id": source_id,
        "title": source.get("Title"),
        "publisher": source.get("Publisher"),
        "input_url": source.get("Canonical_URL") or source.get("URL"),
        "doi": source.get("DOI"),
        "direct_accepted": accepted,
        "verdict": "accepted" if accepted else "pending_search",
        "reason": reason,
        "evidence": evidence,
        "doi_check": doi_result,
        "url_checks": [asdict(item) for item in fetched],
        "search_check": None,
    }


def audit(args: argparse.Namespace) -> None:
    with INPUT.open(encoding="utf-8") as handle:
        new_data = json.load(handle)
    sources = new_data["sources"]
    if args.limit:
        sources = sources[: args.limit]
    log(f"Phase 1/2: direct URL and DOI checks for {len(sources)} records")
    direct_results: dict[str, dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.direct_workers) as pool:
        futures = {pool.submit(audit_one_direct, source): source["Source_ID"] for source in sources}
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            source_id = futures[future]
            try:
                result = future.result()
            except Exception as exc:  # Preserve an auditable failure instead of aborting the batch.
                result = {
                    "original_source_id": source_id,
                    "title": next(s["Title"] for s in sources if s["Source_ID"] == source_id),
                    "verdict": "pending_search",
                    "reason": f"Direct audit error: {type(exc).__name__}: {str(exc)[:300]}",
                    "evidence": {},
                    "doi_check": None,
                    "url_checks": [],
                    "search_check": None,
                }
            direct_results[source_id] = result
            if index % 20 == 0 or index == len(sources):
                accepted = sum(r.get("direct_accepted") for r in direct_results.values())
                log(f"  direct {index}/{len(sources)} complete; {accepted} provisionally accepted")

    pending = [source for source in sources if not direct_results[source["Source_ID"]].get("direct_accepted")]
    log(f"Phase 2/2: independent Yahoo index search for {len(pending)} unresolved records")
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.search_workers) as pool:
        futures = {
            pool.submit(audit_one_search, source, args.max_search_queries, args.search_delay): source
            for source in pending
        }
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            source = futures[future]
            row = direct_results[source["Source_ID"]]
            try:
                search_result = future.result()
                searches = search_result["searches"]
                best = search_result["best"]
            except Exception as exc:
                searches = [{"status": "search_error", "results": [], "error": f"{type(exc).__name__}: {exc}"}]
                best = {}
            row["search_check"] = searches
            row["evidence"] = best or row.get("evidence") or {}
            common = best.get("score_details", {}).get("common", 0)
            # Independent indexed evidence is accepted only with a strong title match.
            if best and best.get("title_score", 0) >= 0.66 and common >= 3 and best.get("trusted_domain"):
                row["verdict"] = "accepted"
                row["reason"] = "Independent search found a trusted, strongly title-matched source page."
            elif best and best.get("title_score", 0) >= 0.74 and common >= 4:
                row["verdict"] = "accepted"
                row["reason"] = "Independent search found a strongly title-matched source page."
            else:
                row["verdict"] = "rejected"
                if (row.get("doi_check") or {}).get("status") == "not_registered":
                    row["reason"] = "Supplied DOI is not registered and no independent matching source was found."
                elif any(check.get("outcome") == "soft_404" for check in row.get("url_checks", [])):
                    row["reason"] = "Supplied page is a soft-404 and no independent matching source was found."
                elif all(check.get("outcome") in {"http_error", "network_error", "invalid_url", "soft_404", "empty"} for check in row.get("url_checks", [])):
                    row["reason"] = "Supplied links are unavailable and no independent matching source was found."
                else:
                    row["reason"] = "Available pages/search results do not substantively match the supplied source title."
            if index % 10 == 0 or index == len(pending):
                accepted_total = sum(r.get("verdict") == "accepted" for r in direct_results.values())
                log(f"  search {index}/{len(pending)} complete; {accepted_total} total accepted")

    ordered = [direct_results[source["Source_ID"]] for source in sources]
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    accepted_count = sum(row["verdict"] == "accepted" for row in ordered)
    payload = {
        "audit": {
            "checked_at_utc": checked_at,
            "input_file": INPUT.name,
            "total_checked": len(ordered),
            "accepted": accepted_count,
            "rejected": len(ordered) - accepted_count,
            "policy": (
                "Conservative verification: accept only registered title-matched DOI, live title-matched page, "
                "or trusted independently indexed page with a strong title match."
            ),
        },
        "results": ordered,
    }
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    log(f"Audit finished: {accepted_count} accepted, {len(ordered) - accepted_count} rejected")
    log(f"Wrote {RESULTS.relative_to(ROOT)}")


def summarize(_: argparse.Namespace) -> None:
    with RESULTS.open(encoding="utf-8") as handle:
        data = json.load(handle)
    rows = data["results"]
    print(json.dumps(data["audit"], ensure_ascii=False, indent=2))
    print("\nAccepted by evidence type:")
    print(Counter(row.get("evidence", {}).get("evidence_type", "none") for row in rows if row["verdict"] == "accepted"))
    print("\nRejected by reason:")
    print(Counter(row["reason"] for row in rows if row["verdict"] == "rejected"))
    print("\nAccepted IDs:")
    print(" ".join(row["original_source_id"] for row in rows if row["verdict"] == "accepted"))


def short_query(title: str, max_chars: int = 170) -> str:
    words = str(title).split()
    result: list[str] = []
    length = 0
    for word in words:
        if result and length + len(word) + 1 > max_chars:
            break
        result.append(word)
        length += len(word) + (1 if result else 0)
    return " ".join(result)


def retry_search(args: argparse.Namespace) -> None:
    with INPUT.open(encoding="utf-8") as handle:
        input_data = json.load(handle)
    source_map = {source["Source_ID"]: source for source in input_data["sources"]}
    with RESULTS.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    rows = payload["results"]
    retry_rows = [
        row
        for row in rows
        if any(search.get("status") == "search_error" for search in (row.get("search_check") or []))
    ]
    if args.max_id is not None:
        retry_rows = [row for row in retry_rows if int(row["original_source_id"][1:]) <= args.max_id]
    log(f"Retrying {len(retry_rows)} failed searches with shortened queries")

    def run(row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        source = source_map[row["original_source_id"]]
        query = short_query(source["Title"], args.max_chars)
        result = yahoo_search(query)
        time.sleep(args.search_delay)
        return row["original_source_id"], result

    row_map = {row["original_source_id"]: row for row in rows}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.search_workers) as pool:
        futures = {pool.submit(run, row): row["original_source_id"] for row in retry_rows}
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            source_id, result = future.result()
            row = row_map[source_id]
            row.setdefault("search_check", []).append(result)
            if index % 20 == 0 or index == len(retry_rows):
                log(f"  retry {index}/{len(retry_rows)} complete")

    for row in rows:
        source = source_map[row["original_source_id"]]
        verdict, reason, evidence = decision_from_evidence(source, row)
        row["verdict"] = verdict
        row["reason"] = reason
        row["evidence"] = evidence
    payload["audit"]["accepted"] = sum(row["verdict"] == "accepted" for row in rows)
    payload["audit"]["rejected"] = sum(row["verdict"] == "rejected" for row in rows)
    payload["audit"]["search_retry_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with RESULTS.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    log(
        f"Retry/review finished: {payload['audit']['accepted']} accepted, "
        f"{payload['audit']['rejected']} rejected"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    audit_parser = sub.add_parser("audit", help="Run the live web audit")
    audit_parser.add_argument("--direct-workers", type=int, default=8)
    audit_parser.add_argument("--search-workers", type=int, default=4)
    audit_parser.add_argument("--search-delay", type=float, default=0.8)
    audit_parser.add_argument("--max-search-queries", type=int, default=1)
    audit_parser.add_argument("--limit", type=int)
    audit_parser.set_defaults(func=audit)
    summary_parser = sub.add_parser("summarize", help="Summarize saved audit results")
    summary_parser.set_defaults(func=summarize)
    retry_parser = sub.add_parser("retry-search", help="Retry failed search-engine requests and re-evaluate all rows")
    retry_parser.add_argument("--search-workers", type=int, default=5)
    retry_parser.add_argument("--search-delay", type=float, default=0.8)
    retry_parser.add_argument("--max-chars", type=int, default=170)
    retry_parser.add_argument("--max-id", type=int)
    retry_parser.set_defaults(func=retry_search)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
