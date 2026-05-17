# app/utils/fuzzy_match.py
from __future__ import annotations

from app.core.logger import get_logger

logger = get_logger(__name__)

# Maps common typos / misspellings → correct keyword
TYPO_MAP: dict[str, str] = {
    # ── HR — Leave & Time ────────────────────────────────────────────────────
    "leavy":          "leave",
    "leav":           "leave",
    "levae":          "leave",
    "leve":           "leave",
    "anual":          "annual",
    "annaul":         "annual",
    "vacaton":        "vacation",
    "vaccation":      "vacation",
    "onbording":      "onboarding",
    "onbaording":     "onboarding",
    "onboardng":      "onboarding",
    "resignaton":     "resignation",
    "resigntion":     "resignation",
    "employe":        "employee",
    "emploees":       "employee",
    "probaton":       "probation",
    "probtion":       "probation",
    "termiantion":    "termination",
    "terminaton":     "termination",
    "matarnity":      "maternity",
    "maternty":       "maternity",
    "paternty":       "paternity",
    "attendence":     "attendance",
    "atendance":      "attendance",
    # ── HR — Compensation & Benefits ─────────────────────────────────────────
    "gratuty":        "gratuity",
    "gratuiti":       "gratuity",
    "grautity":       "gratuity",
    "eosb":           "gratuity",       # End of Service Benefit alias
    "eos":            "gratuity",
    "insurnce":       "insurance",
    "insurence":      "insurance",
    "permormance":    "performance",
    "performence":    "performance",
    "appraisel":      "appraisal",
    "appraissal":     "appraisal",
    "emiratisation":  "emiratization",  # British vs US spelling
    "emiratizaton":   "emiratization",
    # ── IT — Authentication & Access ─────────────────────────────────────────
    "pasword":        "password",
    "passowrd":       "password",
    "passsword":      "password",
    "passward":       "password",
    "resset":         "reset",
    "lognin":         "login",
    "logon":          "login",
    "lapttop":        "laptop",
    "labtop":         "laptop",
    "latop":          "laptop",
    "mfa":            "multi-factor authentication",
    "2fa":            "two-factor authentication",
    "authenticaton":  "authentication",
    "autentication":  "authentication",
    "vpn":            "VPN",            # ensure consistent casing lookup
    "wps":            "WPS",            # Wage Protection System
    "byod":           "BYOD",
    "rbac":           "access control",
    "tickt":          "ticket",
    "tiket":          "ticket",
    "sofware":        "software",
    "softwere":       "software",
    "antivrus":       "antivirus",
    "antiviruss":     "antivirus",
    # ── Finance ───────────────────────────────────────────────────────────────
    "salery":         "salary",
    "sallary":        "salary",
    "expence":        "expense",
    "expens":         "expense",
    "reimburse":      "reimbursement",
    "reimbursment":   "reimbursement",
    "rembursement":   "reimbursement",
    "bonis":          "bonus",
    "bonnus":         "bonus",
    "payrol":         "payroll",
    "payrole":        "payroll",
    "invoce":         "invoice",
    "invocie":        "invoice",
    "vat":            "VAT",            # Value Added Tax alias normalisation
    "procurment":     "procurement",
    "procuremnt":     "procurement",
    "budegt":         "budget",
    "buget":          "budget",
    "allowence":      "allowance",
    "allownce":       "allowance",
    "advnace":        "advance",
    "advanc":         "advance",
    "trevelling":     "travel",
    "travlling":      "travel",
    "travling":       "travel",
}


def normalize_query(query: str) -> str:
    """
    Replace typos in query with correct words, word-by-word.
    Preserves the rest of the sentence structure.
    """
    words  = query.lower().split()
    fixed  = [TYPO_MAP.get(w, w) for w in words]
    result = " ".join(fixed)

    if result != query.lower():
        logger.debug("fuzzy.normalized", original=query, result=result)

    return result
