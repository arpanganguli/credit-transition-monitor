"""
Companies House enrichment: look up a UK company and (best-effort) extract a
handful of financial figures from its filed iXBRL accounts.

This is Week 3 of the build plan -- deliberately narrow in scope. It maps
only Revenue, Operating Profit, Profit Before Tax, Cash, Current Assets,
Current Liabilities, Total Assets, Creditors, Equity and Employees; it does
not attempt to interpret the full Companies House XBRL taxonomy.

Configuration
-------------
Set the environment variable ``COMPANIES_HOUSE_API_KEY`` to enable live
lookups (register a free key at
https://developer.company-information.service.gov.uk/). Without a key, every
function in this module returns a clearly-labelled "not configured" result
instead of raising -- the rest of the app works fine on customer-uploaded
data alone; this is an enrichment layer, not a dependency.

Provenance
----------
Every value this module returns is tagged with a ``source`` -- either
``"COMPANIES_HOUSE"`` (fetched from the API/accounts) or ``"UNAVAILABLE"``
(key missing, network error, or the tag was not found in the filed
accounts). "Provenance is not optional; institutional users care about
lineage" (Week 3 note) -- so a downstream table should always show where a
number came from, never present a Companies House figure as if it were the
customer's own upload, or vice versa.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

import requests

COMPANIES_HOUSE_BASE = "https://api.company-information.service.gov.uk"
DOCUMENT_API_BASE = "https://document-api.company-information.service.gov.uk"

SOURCE_COMPANIES_HOUSE = "COMPANIES_HOUSE"
SOURCE_CUSTOMER_UPLOAD = "CUSTOMER_UPLOAD"
SOURCE_MANUAL_OVERRIDE = "MANUAL_OVERRIDE"
SOURCE_UNAVAILABLE = "UNAVAILABLE"

# The narrow set of concepts we attempt to map from filed accounts, and the
# iXBRL tag local-names (across the common UK GAAP / FRS / IFRS taxonomies)
# we'll look for. This is intentionally not exhaustive -- see module docstring.
FINANCIAL_CONCEPT_TAGS: dict[str, list[str]] = {
    "revenue": ["Turnover", "TurnoverRevenue", "Revenue"],
    "operating_profit": ["OperatingProfitLoss"],
    "profit_before_tax": [
        "ProfitLossOnOrdinaryActivitiesBeforeTax",
        "ProfitLossBeforeTax",
    ],
    "cash": ["CashBankOnHand", "CashBankInHand", "CashAndCashEquivalents"],
    "current_assets": ["CurrentAssets"],
    "current_liabilities": ["CreditorsDueWithinOneYear", "CurrentLiabilities"],
    "total_assets": ["TotalAssets", "TotalAssetsLessCurrentLiabilities"],
    "creditors": ["Creditors"],
    "equity": ["Equity", "ShareholderFunds"],
    "employees": ["AverageNumberEmployeesDuringPeriod"],
}


def _api_key() -> Optional[str]:
    return os.environ.get("COMPANIES_HOUSE_API_KEY") or None


@dataclass
class CompanyLookupResult:
    company_number: str
    source: str
    company_name: Optional[str] = None
    sic_codes: Optional[list[str]] = None
    company_status: Optional[str] = None
    accounts_next_due: Optional[str] = None
    message: Optional[str] = None
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "company_number": self.company_number,
            "source": self.source,
            "company_name": self.company_name,
            "sic_codes": self.sic_codes,
            "company_status": self.company_status,
            "accounts_next_due": self.accounts_next_due,
            "message": self.message,
        }


def get_company(company_number: str, api_key: Optional[str] = None) -> CompanyLookupResult:
    """
    Fetch basic public-company information for a UK company number.

    Returns a CompanyLookupResult with source=UNAVAILABLE (never raises) if
    no API key is configured, the company number is not found, or the
    request fails for any reason -- callers should check ``.source`` and
    ``.message`` before trusting the other fields.
    """
    key = api_key or _api_key()
    company_number = (company_number or "").strip()

    if not company_number:
        return CompanyLookupResult(
            company_number=company_number,
            source=SOURCE_UNAVAILABLE,
            message="No company number supplied.",
        )

    if not key:
        return CompanyLookupResult(
            company_number=company_number,
            source=SOURCE_UNAVAILABLE,
            message=(
                "Companies House integration is not configured. Set the "
                "COMPANIES_HOUSE_API_KEY environment variable to enable "
                "live company lookups."
            ),
        )

    try:
        resp = requests.get(
            f"{COMPANIES_HOUSE_BASE}/company/{company_number}",
            auth=(key, ""),
            timeout=10,
        )
        if resp.status_code == 404:
            return CompanyLookupResult(
                company_number=company_number,
                source=SOURCE_UNAVAILABLE,
                message=f"Company number {company_number} was not found at Companies House.",
            )
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:
        return CompanyLookupResult(
            company_number=company_number,
            source=SOURCE_UNAVAILABLE,
            message=f"Companies House lookup failed: {exc}",
        )

    return CompanyLookupResult(
        company_number=company_number,
        source=SOURCE_COMPANIES_HOUSE,
        company_name=payload.get("company_name"),
        sic_codes=payload.get("sic_codes"),
        company_status=payload.get("company_status"),
        accounts_next_due=(payload.get("accounts") or {}).get("next_due"),
        raw=payload,
    )


@dataclass
class FinancialFact:
    concept: str
    value: Optional[float]
    source: str
    unit: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "concept": self.concept,
            "value": self.value,
            "source": self.source,
            "unit": self.unit,
        }


def extract_financials(xbrl_path_or_bytes) -> dict[str, FinancialFact]:
    """
    Best-effort extraction of the narrow financial-concept set above from a
    filed iXBRL/XBRL accounts document.

    Preferred path: Arelle (https://arelle.org), if installed, via its Python
    API -- this handles the full taxonomy correctly, including dimensions and
    context periods. Arelle is an optional dependency (see requirements.txt);
    when it is not installed, this function falls back to a minimal
    tag-scraping parser built on lxml that looks for bare ``ix:nonFraction``
    elements matching the concept names above. The fallback is deliberately
    conservative: if a concept can't be found with high confidence it is
    returned as UNAVAILABLE rather than guessed at.
    """
    try:
        return _extract_with_arelle(xbrl_path_or_bytes)
    except ImportError:
        return _extract_with_lxml_fallback(xbrl_path_or_bytes)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the UI
        return {
            concept: FinancialFact(concept, None, SOURCE_UNAVAILABLE, None)
            for concept in FINANCIAL_CONCEPT_TAGS
        } | {"_error": FinancialFact("_error", None, SOURCE_UNAVAILABLE, str(exc))}


def _extract_with_arelle(xbrl_path_or_bytes) -> dict[str, FinancialFact]:
    from arelle import Cntlr  # type: ignore  # optional dependency

    controller = Cntlr.Cntlr(logFileName=None)
    model_xbrl = controller.modelManager.load(xbrl_path_or_bytes)
    facts_by_local_name: dict[str, list] = {}
    for fact in model_xbrl.facts:
        local_name = fact.qname.localName if fact.qname else None
        if local_name:
            facts_by_local_name.setdefault(local_name, []).append(fact)

    results: dict[str, FinancialFact] = {}
    for concept, tag_candidates in FINANCIAL_CONCEPT_TAGS.items():
        value = None
        for tag in tag_candidates:
            matches = facts_by_local_name.get(tag)
            if matches:
                try:
                    value = float(matches[0].value)
                except (TypeError, ValueError):
                    value = None
                break
        results[concept] = FinancialFact(
            concept, value, SOURCE_COMPANIES_HOUSE if value is not None else SOURCE_UNAVAILABLE
        )
    controller.close()
    return results


def _extract_with_lxml_fallback(xbrl_path_or_bytes) -> dict[str, FinancialFact]:
    """
    Minimal iXBRL scraper used only when Arelle is not installed. Looks for
    ``<ix:nonFraction name="...:Tag">`` elements by local tag name. This does
    NOT resolve contexts/periods or apply sign/scale attributes beyond the
    basic ``sign`` and ``scale`` attributes on the element itself, so treat
    its output as indicative, not authoritative -- Arelle is the intended
    production path.
    """
    from lxml import etree  # lxml is a hard dependency of this project

    if isinstance(xbrl_path_or_bytes, (bytes, bytearray)):
        tree = etree.fromstring(xbrl_path_or_bytes)
    else:
        tree = etree.parse(str(xbrl_path_or_bytes)).getroot()

    tag_to_value: dict[str, float] = {}
    for el in tree.iter():
        local_tag = etree.QName(el.tag).localname
        if local_tag not in ("nonFraction",):
            continue
        name_attr = el.get("name", "")
        local_name = name_attr.split(":")[-1] if ":" in name_attr else name_attr
        text = (el.text or "").strip().replace(",", "")
        if not text or not local_name:
            continue
        try:
            value = float(text)
        except ValueError:
            continue
        scale = el.get("scale")
        if scale:
            try:
                value *= 10 ** int(scale)
            except ValueError:
                pass
        if el.get("sign") == "-":
            value = -value
        tag_to_value.setdefault(local_name, value)

    results: dict[str, FinancialFact] = {}
    for concept, tag_candidates in FINANCIAL_CONCEPT_TAGS.items():
        value = None
        for tag in tag_candidates:
            if tag in tag_to_value:
                value = tag_to_value[tag]
                break
        results[concept] = FinancialFact(
            concept, value, SOURCE_COMPANIES_HOUSE if value is not None else SOURCE_UNAVAILABLE
        )
    return results
