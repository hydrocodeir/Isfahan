#!/usr/bin/env python3
"""Verify every link added by the deep-literature merge."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "deep_literature_link_verification.json"
UA = "HydroCodeIR-link-verification/1.0"


def check(record: dict) -> dict:
    url = record.get("Canonical_URL") or record.get("URL")
    try:
        response = requests.get(
            url,
            headers={"User-Agent": UA, "Accept": "text/html,application/pdf,*/*;q=0.8"},
            allow_redirects=True,
            stream=True,
            timeout=(7, 22),
        )
        result = {
            "source_id": record["Source_ID"], "title": record["Title"], "doi": record.get("DOI"),
            "requested_url": url, "http_status": response.status_code, "final_url": response.url,
            "status": "live" if response.status_code < 400 else "http_error",
        }
        response.close()
        if result["status"] == "live":
            result["verification_basis"] = "live landing page"
            result["verified"] = True
            return result
        return verify_registry(record, result)
    except requests.RequestException as exc:
        result = {
            "source_id": record["Source_ID"], "title": record["Title"], "doi": record.get("DOI"),
            "requested_url": url, "status": "network_error", "error": f"{type(exc).__name__}: {str(exc)[:300]}",
        }
        return verify_registry(record, result)


def verify_registry(record: dict, result: dict) -> dict:
    """Use authoritative registry metadata when a publisher blocks automation."""
    doi = record.get("DOI")
    document_id = record.get("Document_ID") or ""
    try:
        if doi:
            response = requests.get(
                f"https://doi.org/doiRA/{doi}", headers={"User-Agent": UA}, timeout=(7, 22)
            )
            payload = response.json()[0] if response.status_code == 200 else {}
            result["registry"] = payload.get("RA")
            result["registry_status"] = payload.get("status")
            result["verified"] = bool(payload.get("RA"))
            result["verification_basis"] = (
                f"registered DOI ({payload['RA']})" if payload.get("RA") else "DOI not registered"
            )
            return result
        if document_id.startswith("DOAJ:"):
            doaj_id = document_id.split(":", 1)[1]
            response = requests.get(
                f"https://doaj.org/api/articles/{doaj_id}", headers={"User-Agent": UA}, timeout=(7, 22)
            )
            result["doaj_api_status"] = response.status_code
            result["verified"] = response.status_code == 200
            result["verification_basis"] = "DOAJ registry record" if result["verified"] else "DOAJ record unavailable"
            return result
    except (requests.RequestException, ValueError, KeyError) as exc:
        result["registry_error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    result["verified"] = False
    result["verification_basis"] = "no live link or authoritative registry record"
    return result


def main() -> None:
    data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    records = [item for item in data["sources"] if "مرور عمیق ادبیات" in (item.get("Notes") or "")]
    with ThreadPoolExecutor(max_workers=16) as executor:
        results = list(executor.map(check, records))
    payload = {
        "checked": len(results),
        "live": sum(x["status"] == "live" for x in results),
        "http_error": sum(x["status"] == "http_error" for x in results),
        "network_error": sum(x["status"] == "network_error" for x in results),
        "verified": sum(bool(x.get("verified")) for x in results),
        "unverified": sum(not x.get("verified") for x in results),
        "results": results,
    }
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("checked", "live", "http_error", "network_error")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
