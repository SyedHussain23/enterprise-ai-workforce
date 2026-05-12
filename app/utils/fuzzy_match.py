# app/utils/fuzzy_match.py

# Maps common typos / misspellings → correct keyword
TYPO_MAP = {
    # HR
    "leavy":       "leave",
    "leav":        "leave",
    "levae":       "leave",
    "leve":        "leave",
    "anual":       "annual",
    "annaul":      "annual",
    "vacaton":     "vacation",
    "vaccation":   "vacation",
    "onbording":   "onboarding",
    "onbaording":  "onboarding",
    "resignaton":  "resignation",
    "employe":     "employee",
    "emploees":    "employee",
    # IT
    "pasword":     "password",
    "passowrd":    "password",
    "passsword":   "password",
    "passward":    "password",
    "resset":      "reset",
    "lognin":      "login",
    "lapttop":     "laptop",
    "labtop":      "laptop",
    # Finance
    "salery":      "salary",
    "sallary":     "salary",
    "expence":     "expense",
    "expens":      "expense",
    "reimburse":   "reimbursement",
    "reimbursment":"reimbursement",
    "bonis":       "bonus",
    "bonnus":      "bonus",
    "payrol":      "payroll",
}


def normalize_query(query: str) -> str:
    """
    Replace typos in query with correct words.
    Works word by word — preserves rest of sentence.
    """
    words  = query.lower().split()
    fixed  = [TYPO_MAP.get(w, w) for w in words]
    result = " ".join(fixed)

    if result != query.lower():
        print(f"[FUZZY] Normalized: '{query}' → '{result}'")

    return result