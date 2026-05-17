import os

# -----------------------------
# DEFINE UNIQUE CONTENT
# -----------------------------

hr_topics = [
    ("Leave Policy", "Employees are entitled to 21 days annual leave and 12 sick leave."),
    ("Attendance", "Employees must work 9 hours daily."),
    ("Onboarding", "New hires complete onboarding within 5 days."),
    ("Exit Policy", "Employees must serve 60 days notice period."),
    ("Payroll", "Salary processed on last working day."),
    ("Promotion", "Promotions are performance based."),
    ("Transfer", "Internal transfer allowed after 1 year."),
    ("Leave Approval", "Manager approval required for leave."),
    ("Work From Home", "WFH allowed based on manager approval."),
    ("Grievance", "Employees can report issues to HR."),
    ("Training", "Employees undergo quarterly training."),
    ("Appraisal", "Annual performance review conducted."),
    ("Overtime", "Overtime paid based on policy."),
    ("Code of Conduct", "Employees must maintain discipline."),
    ("Holiday Policy", "Public holidays are company defined."),
    ("Maternity Leave", "6 months paid leave."),
    ("Paternity Leave", "10 days leave."),
    ("Probation", "Probation period is 6 months."),
    ("Resignation", "Resignation must be submitted formally."),
    ("Documentation", "Employee documents stored securely."),
    ("Attendance Tracking", "Attendance tracked via system."),
    ("Remote Policy", "Remote work needs approval."),
    ("Dress Code", "Formal attire required."),
    ("Leave Carry Forward", "Max 10 days carry forward."),
    ("HR Support", "HR support available 24/7."),
]

finance_topics = [
    ("Salary", "Salary paid on last working day."),
    ("Bonus", "Annual performance bonus given."),
    ("Tax", "TDS deducted as per rules."),
    ("Expense", "Travel expenses reimbursed."),
    ("Invoice", "Invoices processed within 10 days."),
    ("Budget", "Budget approved by finance head."),
    ("Audit", "Annual financial audit conducted."),
    ("Reimbursement", "Claims settled within 7 days."),
    ("Payroll", "Payroll managed monthly."),
    ("Deductions", "Deductions applied as per policy."),
    ("Allowance", "Employees receive travel allowance."),
    ("Investment", "Company invests in growth sectors."),
    ("Financial Reporting", "Quarterly reports generated."),
    ("Procurement", "Procurement follows approval flow."),
    ("Vendor Payment", "Vendor payments within 15 days."),
    ("Compliance", "Financial compliance mandatory."),
    ("Tax Filing", "Tax filing done yearly."),
    ("Cash Flow", "Cash flow monitored weekly."),
    ("Profit Analysis", "Profit analyzed quarterly."),
    ("Cost Control", "Cost optimization practiced."),
    ("Revenue Tracking", "Revenue tracked monthly."),
    ("Financial Planning", "Annual planning done."),
    ("Assets", "Company assets monitored."),
    ("Liabilities", "Liabilities tracked."),
    ("Accounting", "Accounts maintained daily."),
]

it_topics = [
    ("Password", "Passwords must change every 90 days."),
    ("VPN", "VPN required for remote access."),
    ("Laptop", "Laptop provided on joining."),
    ("Security", "Do not share credentials."),
    ("Access Control", "Role-based access control."),
    ("Network", "Secure network maintained."),
    ("Backup", "Data backup done daily."),
    ("Software Install", "Install via IT approval."),
    ("Firewall", "Firewall protects system."),
    ("Monitoring", "System monitored 24/7."),
    ("Email", "Official email usage only."),
    ("Antivirus", "Antivirus mandatory."),
    ("Data Protection", "Data must be encrypted."),
    ("Cloud", "Cloud storage used."),
    ("IT Support", "IT helpdesk available."),
    ("System Update", "Regular updates required."),
    ("Device Policy", "Devices monitored."),
    ("Login", "Login via secure system."),
    ("Authentication", "2FA enabled."),
    ("Incident Response", "Security incidents tracked."),
    ("Server", "Servers monitored."),
    ("Storage", "Data stored securely."),
    ("Compliance", "IT compliance enforced."),
    ("Ticketing", "IT issues via tickets."),
    ("Remote Access", "Secure remote access only."),
]

company_topics = [
    ("Work Hours", "9 AM to 6 PM working hours."),
    ("Dress Code", "Business casual required."),
    ("Remote Work", "Allowed with approval."),
    ("Conduct", "Professional behavior required."),
    ("Holiday", "Company holidays predefined."),
    ("Culture", "Positive work culture maintained."),
    ("Meetings", "Weekly team meetings."),
    ("Communication", "Official communication channels."),
    ("Performance", "Performance tracked."),
    ("Team Work", "Collaboration encouraged."),
    ("Ethics", "Ethical work mandatory."),
    ("Diversity", "Diversity supported."),
    ("Inclusion", "Inclusive workplace."),
    ("Safety", "Workplace safety ensured."),
    ("Facilities", "Office facilities provided."),
    ("Events", "Company events organized."),
    ("Recognition", "Employee recognition programs."),
    ("Growth", "Career growth supported."),
    ("Training", "Learning programs available."),
    ("Feedback", "Regular feedback collected."),
    ("Leadership", "Leadership programs available."),
    ("Policies", "Company policies enforced."),
    ("Compliance", "Legal compliance followed."),
    ("Vision", "Company vision shared."),
    ("Mission", "Mission driven work."),
]

data_map = {
    "HR": hr_topics,
    "Finance": finance_topics,
    "IT": it_topics,
    "Company": company_topics
}

# -----------------------------
# GENERATE FILES (safe — skips existing files)
# WARNING: This script generates minimal stub content only.
# The production data/ KB files were hand-crafted with full
# UAE Labour Law detail and MUST NOT be overwritten.
# Run with --force only to reset to stubs (development only).
# -----------------------------
import sys
force = "--force" in sys.argv

created = 0
skipped = 0

for folder, topics in data_map.items():

    os.makedirs(f"data/{folder}", exist_ok=True)

    for i, (topic, content) in enumerate(topics):

        file_path = f"data/{folder}/{folder.lower()}_{i+1}.txt"

        if os.path.exists(file_path) and not force:
            skipped += 1
            continue

        with open(file_path, "w") as f:
            f.write(f"""{folder} Policy Document

Topic: {topic}

Details:
{content}

Document ID: {folder}_{i+1}
Keywords: {topic.lower()}, {folder.lower()} policy
""")
        created += 1

if skipped:
    print(f"⚠️  Skipped {skipped} existing files (use --force to overwrite).")
print(f"✅ {created} stub documents created. Run with --force to overwrite existing files.")