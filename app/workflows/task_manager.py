def determine_workflow(user_input: str):

    text = user_input.lower()

    if "onboarding" in text:
        return ["HR", "IT", "Finance"]

    if "employee setup" in text:
        return ["HR", "IT"]

    if "expense reimbursement" in text:
        return ["Finance"]

    return []