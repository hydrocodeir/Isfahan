#!/usr/bin/env python3
"""Repair canonical links for retained target-basin literature records."""

from __future__ import annotations

import json
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
TODAY = "2026-09-13"

# Publisher pages for these DOAJ records no longer respond reliably.  Their
# DOAJ article pages and API records are stable, independently verifiable links.
DOAJ_LINK_REPAIRS = {
    "S518": "0de9a7a4d0d545e48983cba4cc59bfda",
    "S521": "336b71fbf76a4463bf761865bf7afe52",
    "S523": "54229da2e09a46e18b952d7b35f0a868",
    "S524": "59bef24f72f04c039a9838397bbe7af1",
    "S535": "9b4132cb1e9344c1a0c26f5e90a74a79",
    "S547": "fc82daed2927467fa3b89ef12b93a07c",
    "S552": "2c760e31687146f596cbf591774c951d",
    "S567": "ae1bc583fbe84fc79f9d842029e20ba6",
    "S574": "25c80557c69d4a2b8ddf23274b81f142",
    "S606": "17d49f20f280406693fe69188a41a8bd",
    "S622": "26aaa47ecd4a4f21aa94282a6fb2ccff",
    "S623": "92e2bb7238024157bb79a07def192c54",
    "S629": "3372f089bef94800a1a9205681c96c6b",
    "S671": "c4c2257831df48bbb6b35679fef2e3c2",
}

# These DOI strings are displayed by the journals/DOAJ but doi.org's official
# DOI Registration Agency endpoint reports that they are not registered.
UNREGISTERED_DOI_REPAIRS = {
    "S644": ("b175dc6e964e40f1b096f2422fca78f6", "10.22034/jccj.2024.450807.1532"),
    "S676": ("f76d5c56394a4408b149dfc61e405f65", "10.22059/jwim.2023.358580.1071"),
}

CORRECT_DOI = {
    "S567": "10.22074/cellj.2015.6",
}


def update_excel(records: dict[str, dict]) -> None:
    path = ROOT / "Data.xlsx"
    wb = load_workbook(path)
    for sheet_name in ("ALL_SOURCES", "ACADEMIC", "NEW_SOURCES"):
        ws = wb[sheet_name]
        headers = {cell.value: cell.column for cell in ws[1]}
        for row in range(2, ws.max_row + 1):
            source_id = ws.cell(row, 1).value
            record = records.get(source_id)
            if not record:
                continue
            for field in ("URL", "Canonical_URL", "Archive_URL", "DOI", "Document_ID", "Notes"):
                if field in headers:
                    ws.cell(row, headers[field]).value = record.get(field)
    for sheet_name in (
        "ALL_SOURCES", "TIMELINE", "ACADEMIC", "THESES", "OFFICIAL_LEGAL",
        "PARLIAMENT", "NEWS_MEDIA", "SOCIAL_MEDIA", "PDF_INDEX", "NEW_SOURCES",
    ):
        ws = wb[sheet_name]
        while ws.max_row > 1 and ws.cell(ws.max_row, 1).value is None:
            ws.delete_rows(ws.max_row, 1)
    for sheet_name in ("ALL_SOURCES", "ACADEMIC", "NEW_SOURCES"):
        ws = wb[sheet_name]
        for table in ws.tables.values():
            table.ref = f"A1:AK{ws.max_row}"
    change_log = wb["CHANGE_LOG"]
    existing_changes = {change_log.cell(row, 1).value for row in range(2, change_log.max_row + 1)}
    if "C034" not in existing_changes:
        change_log.append([
            "C034", TODAY, "SCOPED LINK REPAIR", "16 retained academic records",
            "Replace dead publisher links and distinguish reported-but-unregistered DOI strings",
            "14 records linked to stable DOAJ pages; 2 unregistered DOI fields cleared; 1 missing DOI restored from PubMed.",
        ])
    wb.save(path)


def update_offline(data: dict) -> None:
    path = ROOT / "app.js"
    text = path.read_text(encoding="utf-8")
    marker = "const OFFLINE_FALLBACK = "
    start = text.index(marker) + len(marker)
    end = text.index(";\n\nconst $", start)
    packed = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text[:start] + packed + text[end:], encoding="utf-8", newline="\n")


def main() -> None:
    data_path = ROOT / "data.json"
    data = json.loads(data_path.read_text(encoding="utf-8"))
    records = {item["Source_ID"]: item for item in data["sources"]}

    for source_id, doaj_id in DOAJ_LINK_REPAIRS.items():
        record = records[source_id]
        record["Canonical_URL"] = f"https://doaj.org/article/{doaj_id}"
        record["Archive_URL"] = f"https://doaj.org/api/articles/{doaj_id}"
        record["Document_ID"] = f"DOAJ:{doaj_id}"
        note = "لینک مرجع به صفحه پایدار DOAJ اصلاح شد."
        if note not in (record.get("Notes") or ""):
            record["Notes"] = f"{record.get('Notes') or ''} {note}".strip()

    for source_id, (doaj_id, reported_doi) in UNREGISTERED_DOI_REPAIRS.items():
        record = records[source_id]
        record["DOI"] = None
        record["Document_ID"] = f"DOAJ:{doaj_id}"
        record["Canonical_URL"] = f"https://doaj.org/article/{doaj_id}"
        record["Archive_URL"] = f"https://doaj.org/api/articles/{doaj_id}"
        record["URL"] = record.get("PDF_URL") or record["Canonical_URL"]
        note = (
            f"DOI اعلام‌شده توسط مجله ({reported_doi}) در استعلام رسمی doi.org در {TODAY} "
            "ثبت‌شده نبود؛ منبع با رکورد معتبر DOAJ نگه‌داری شد."
        )
        if note not in (record.get("Notes") or ""):
            record["Notes"] = f"{record.get('Notes') or ''} {note}".strip()

    for source_id, doi in CORRECT_DOI.items():
        record = records[source_id]
        record["DOI"] = doi
        record["Document_ID"] = f"DOI:{doi}"
        record["Canonical_URL"] = f"https://doi.org/{doi}"
        record["Archive_URL"] = "https://pubmed.ncbi.nlm.nih.gov/26464816/"
        note = "DOI و پیوند PubMed پس از تطبیق عنوان و نویسندگان تکمیل شد."
        if note not in (record.get("Notes") or ""):
            record["Notes"] = f"{record.get('Notes') or ''} {note}".strip()

    if not any(row.get("Change_ID") == "C034" for row in data["changeLog"]):
        data["changeLog"].append({
            "Change_ID": "C034",
            "Date": TODAY,
            "Action": "SCOPED LINK REPAIR",
            "Source_ID / Item": "16 retained academic records",
            "Reason": "Replace dead publisher links and distinguish reported-but-unregistered DOI strings",
            "Details": "14 records linked to stable DOAJ pages; 2 unregistered DOI fields cleared; 1 missing DOI restored from PubMed.",
        })
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    update_excel(records)
    update_offline(data)
    print("Repaired 16 retained records; synchronized data.json, Data.xlsx, and app.js.")


if __name__ == "__main__":
    main()
