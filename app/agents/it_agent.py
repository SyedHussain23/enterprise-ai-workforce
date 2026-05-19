from langsmith import traceable

from app.core.constants import DEPT_CONTACTS
from app.core.logger import get_logger
from app.rag.hybrid_retriever import hybrid_search as search_knowledge_base_raw
from app.rag.utils import clean_rag_output
from app.schemas.agent import AgentResponse
from app.tools.automation_engine import generate_report

logger = get_logger(__name__)

PASSWORD_EXPIRY_DAYS  = 90
TICKET_RESPONSE_HRS   = 4
MFA_METHODS           = "Microsoft Authenticator app, SMS OTP, or hardware token"
VPN_CLIENT            = "Cisco AnyConnect"
ANTIVIRUS_TOOL        = "CrowdStrike Falcon"
IT_HELPDESK_EXT       = "1001"

_CREATE_TICKET_PHRASES = [
    "raise a ticket", "raise ticket", "create a ticket", "create ticket",
    "log a ticket", "log ticket", "log an issue", "report a problem",
    "submit a ticket", "open a ticket", "raise an issue", "i have an issue",
    "report issue", "need support", "request support", "it issue", "technical issue",
    "my computer", "my laptop is", "computer problem", "system not working",
]
_REQUEST_ACCESS_PHRASES = [
    "request access to", "need access to", "grant me access",
    "i need access", "can i get access", "provide access", "system access",
    "access request", "permission to", "need permission",
]
_MFA_PHRASES = [
    "mfa", "multi-factor", "two-factor", "2fa", "authenticator",
    "verification code", "otp", "one time password", "authenticator app",
    "microsoft authenticator", "mfa setup", "enable mfa", "mfa not working",
]
_VPN_PHRASES = [
    "vpn", "remote access", "connect remotely", "cisco anyconnect",
    "vpn not working", "vpn setup", "vpn connection", "vpn configuration",
    "cannot connect to vpn", "vpn issue",
]
_PHISHING_PHRASES = [
    "phishing", "suspicious email", "spam email", "fake email",
    "clicked a link", "suspicious link", "malware", "virus", "ransomware",
    "cyber attack", "hacked", "account compromised", "security threat",
    "suspicious attachment",
]
_BYOD_PHRASES = [
    "byod", "personal device", "personal phone", "personal laptop",
    "my own device", "bring my own device", "use personal", "register device",
]
_CLOUD_PHRASES = [
    "onedrive", "sharepoint", "cloud storage", "google drive", "dropbox",
    "cloud", "file storage", "save to cloud", "sync files",
]
_BACKUP_PHRASES = [
    "backup", "recover file", "deleted file", "lost file", "restore file",
    "file recovery", "version history", "data recovery", "accidentally deleted",
]
_CYBER_PHRASES = [
    "cybersecurity", "security policy", "data protection", "information security",
    "secure", "data breach", "privacy", "security training",
]
_INCIDENT_PHRASES = [
    "security incident", "incident response", "breach", "unauthorized access",
    "report security", "security alert", "compromised", "data leak",
]
_SOFTWARE_PHRASES = [
    "install software", "software request", "need software", "application request",
    "install application", "software installation", "new software",
]
_DEVICE_PHRASES = [
    "laptop not working", "laptop broken", "screen broken", "slow computer",
    "device issue", "hardware problem", "laptop replacement", "computer repair",
]
_PRINTER_PHRASES = [
    "printer", "print", "scanning", "copier", "cannot print", "printer not working",
    "print issue", "scan to email",
]


@traceable
def it_agent(query: str) -> AgentResponse:
    q = query.lower().strip()

    # ── Action: Create IT Ticket ──────────────────────────────────────────────
    if any(phrase in q for phrase in _CREATE_TICKET_PHRASES):
        return AgentResponse(
            answer=(
                "✅ **IT Support Ticket Created**\n\n"
                "Your support ticket has been raised successfully.\n\n"
                "**Response Times:**\n"
                f"- Critical (system down): 30 min response | 4hr resolution\n"
                f"- High (major issue): 1hr response | 8hr resolution\n"
                f"- Medium: 4hr response | 2 business days\n"
                f"- Low: 1 business day response\n\n"
                "**What happens next:**\n"
                f"1. IT team notified immediately\n"
                "2. Ticket reference number sent to your email\n"
                "3. Track progress: IT Portal → My Tickets\n\n"
                "**Contact IT Helpdesk:**\n"
                f"- Internal: Ext. {IT_HELPDESK_EXT}\n"
                f"- Email: it-support@company.com\n"
                f"- Walk-in: Building A, Ground Floor, Room G-04"
            ),
            confidence=95,
            source="it_action",
            keyword_match=True,
            action_triggered=True,
            action_type="create_ticket",
            action_payload={"raw_request": query, "department": "IT", "priority": "normal"},
        )

    # ── Action: Request Access ────────────────────────────────────────────────
    if any(phrase in q for phrase in _REQUEST_ACCESS_PHRASES):
        return AgentResponse(
            answer=(
                "✅ **Access Request Submitted**\n\n"
                "Your access request has been logged and sent for approval.\n\n"
                "**What happens next:**\n"
                "1. Your manager receives an approval request\n"
                "2. IT Security reviews the access request\n"
                "3. Access provisioned within 1 business day of approval\n"
                "4. Credentials sent to your company email\n\n"
                "**Standard Access (Day 1):**\n"
                "- Company email, HR Portal, Teams — auto-provisioned\n"
                "- Department apps — provisioned based on role profile\n\n"
                "**Additional Access:**\n"
                "IT Portal → Access Management → Request Access\n"
                "Include: System name, reason, duration needed\n\n"
                f"Questions: {DEPT_CONTACTS['IT']}"
            ),
            confidence=92,
            source="it_action",
            keyword_match=True,
            action_triggered=True,
            action_type="request_access",
            action_payload={"raw_request": query, "department": "IT"},
        )

    # ── MFA / Two-Factor Authentication ───────────────────────────────────────
    if any(phrase in q for phrase in _MFA_PHRASES):
        return AgentResponse(
            answer=(
                "**Multi-Factor Authentication (MFA) Guide**\n\n"
                "MFA is **mandatory** for all company accounts. It adds a second layer of security.\n\n"
                "**Supported MFA Methods:**\n"
                f"- ✅ Microsoft Authenticator app (recommended — fastest)\n"
                f"- ✅ SMS OTP (backup method)\n"
                f"- ✅ Hardware token (for frequent travelers)\n\n"
                "**Setup Steps:**\n"
                "1. Download Microsoft Authenticator on your phone\n"
                "2. Go to: https://aka.ms/mfasetup\n"
                "3. Add account → Work or School Account\n"
                "4. Scan QR code with Authenticator app\n"
                "5. Test with a push notification\n\n"
                "**MFA Not Working?**\n"
                "- Check phone has internet connection\n"
                "- Enable notifications for Authenticator app\n"
                "- Use the 6-digit code instead of push notification\n\n"
                "**Lost Phone / New Phone:**\n"
                "Contact IT immediately — we provide emergency bypass code.\n"
                f"IT Helpdesk: Ext. {IT_HELPDESK_EXT} | it-support@company.com\n\n"
                "⚠️ Never approve an MFA request you did not initiate — report it immediately!"
            ),
            confidence=92,
            source="it_policy",
            keyword_match=True,
        )

    # ── VPN ───────────────────────────────────────────────────────────────────
    if any(phrase in q for phrase in _VPN_PHRASES):
        return AgentResponse(
            answer=(
                "**VPN and Remote Access Guide**\n\n"
                f"**VPN Client:** {VPN_CLIENT} Secure Mobility Client\n"
                "**VPN is mandatory** for all remote work (no exceptions).\n\n"
                "**VPN Setup:**\n"
                "1. Download from IT Portal → Downloads → VPN Client\n"
                "2. Server address: vpn.company.com\n"
                "3. Enter company email + password\n"
                "4. Complete MFA verification\n\n"
                "**Troubleshooting VPN Issues:**\n"
                "- Check internet connection first\n"
                "- Update Cisco AnyConnect (IT Portal → Downloads)\n"
                "- Ensure MFA is working (phone charged, internet on phone)\n"
                "- Restart the Cisco AnyConnect service\n"
                "- Disconnect and reconnect if connected but no access\n\n"
                "**Important Rules:**\n"
                "- Do NOT use public Wi-Fi without VPN\n"
                "- Split tunneling is disabled (all traffic routes through company)\n"
                "- Personal devices must be registered before VPN access\n\n"
                f"Still not working? IT Helpdesk: Ext. {IT_HELPDESK_EXT}"
            ),
            confidence=92,
            source="it_policy",
            keyword_match=True,
        )

    # ── Phishing / Cybersecurity ──────────────────────────────────────────────
    if any(phrase in q for phrase in _PHISHING_PHRASES):
        return AgentResponse(
            answer=(
                "⚠️ **Cybersecurity Alert — Act Immediately**\n\n"
                "If you clicked a suspicious link or opened a suspicious attachment:\n\n"
                "**Immediate Steps:**\n"
                "1. **STOP** — do not click anything else\n"
                "2. **Disconnect** — unplug network cable or turn off Wi-Fi\n"
                "3. **Do NOT turn off** your computer (preserves evidence)\n"
                f"4. **Call IT Security NOW:** Ext. {IT_HELPDESK_EXT} (24/7 emergency)\n"
                "5. **Report email:** Forward to security@company.com\n\n"
                "**Spotting Phishing Emails — Red Flags:**\n"
                "- Urgent language: 'Immediate action required'\n"
                "- Wrong email domain: supp0rt@c0mpany.com\n"
                "- Generic greeting: 'Dear Employee'\n"
                "- Requests for password or login credentials via email\n"
                "- Suspicious links (hover to see real URL before clicking)\n\n"
                "**Remember:**\n"
                "- IT will NEVER ask for your password via email or phone\n"
                "- When in doubt — do not click. Report to security@company.com\n"
                "- Monthly phishing simulations help train your instincts\n\n"
                f"Security team: security@company.com | Ext. {IT_HELPDESK_EXT}"
            ),
            confidence=92,
            source="it_policy",
            keyword_match=True,
        )

    # ── BYOD ─────────────────────────────────────────────────────────────────
    if any(phrase in q for phrase in _BYOD_PHRASES):
        return AgentResponse(
            answer=(
                "**BYOD (Bring Your Own Device) Policy**\n\n"
                "You can use personal devices to access company resources with proper registration.\n\n"
                "**Eligibility:**\n"
                "- Personal phones: All employees (for email and Teams)\n"
                "- Personal laptops: Grade 3+ with IT approval\n\n"
                "**Registration Process:**\n"
                "1. IT Portal → BYOD → Register Device\n"
                "2. Provide: Device make, model, OS version\n"
                "3. Device assessed (must be updated, not jailbroken)\n"
                "4. IT installs Microsoft Intune app (work data only)\n"
                "5. Registration completed in 3 business days\n\n"
                "**What Intune Manages:**\n"
                "- ONLY your work email, Teams, OneDrive\n"
                "- Does NOT access personal photos, messages, or apps\n"
                "- On leaving company: Only work data wiped (personal data kept)\n\n"
                "**Security Requirements for Personal Devices:**\n"
                "- Screen lock (6-digit PIN minimum)\n"
                "- Auto-lock within 5 minutes\n"
                "- Latest OS version\n"
                "- Not jailbroken/rooted\n\n"
                f"Register now: IT Portal | Questions: {DEPT_CONTACTS['IT']}"
            ),
            confidence=90,
            source="it_policy",
            keyword_match=True,
        )

    # ── Cloud Storage / OneDrive ──────────────────────────────────────────────
    if any(phrase in q for phrase in _CLOUD_PHRASES):
        return AgentResponse(
            answer=(
                "**Cloud Storage and File Management**\n\n"
                "**Approved Company Cloud Services:**\n"
                "- **OneDrive:** Personal work files (1 TB per employee)\n"
                "- **SharePoint:** Team and department shared files\n"
                "- **Teams:** File sharing in chat and channels\n\n"
                "**IMPORTANT — Never use for work files:**\n"
                "- ❌ Personal Google Drive, Dropbox, iCloud, Box\n"
                "- ❌ WeTransfer, personal email attachments\n"
                "- ❌ USB drives for transferring confidential data\n\n"
                "**AI Tools (ChatGPT, Copilot):**\n"
                "- Microsoft Copilot: Approved (integrated with M365)\n"
                "- ChatGPT: Allowed with restrictions — DO NOT input:\n"
                "  Client data, employee info, salary data, source code\n\n"
                "**Setting Up OneDrive:**\n"
                "1. Open OneDrive app on laptop\n"
                "2. Sign in with company email\n"
                "3. Choose folders to sync\n"
                "4. All files automatically backed up to cloud\n\n"
                "⚠️ Files saved ONLY to local Desktop/Downloads are NOT backed up!\n\n"
                f"Help: IT Portal or {DEPT_CONTACTS['IT']}"
            ),
            confidence=90,
            source="it_policy",
            keyword_match=True,
        )

    # ── File Recovery / Backup ────────────────────────────────────────────────
    if any(phrase in q for phrase in _BACKUP_PHRASES):
        return AgentResponse(
            answer=(
                "**File Recovery and Backup**\n\n"
                "**Quick Recovery (OneDrive Recycle Bin):**\n"
                "1. Go to OneDrive → Recycle Bin\n"
                "2. Find deleted file → Right-click → Restore\n"
                "3. Files recoverable up to **30 days** after deletion\n\n"
                "**Recover Earlier Version of a File:**\n"
                "1. Right-click file in OneDrive → Version History\n"
                "2. Select the version you need\n"
                "3. Up to **90 versions** of any file stored\n\n"
                "**Server/Network Drive File Recovery:**\n"
                "1. IT Portal → Data Recovery → Request File Recovery\n"
                "2. Provide: File path, approximate deletion date, reason\n"
                "3. IT restores within 2 business days\n"
                "4. Urgent (same day): Call IT Ext. 1001\n\n"
                "**⚠️ IMPORTANT:**\n"
                "Only files saved to OneDrive/SharePoint are backed up by company.\n"
                "Files saved ONLY to local C: drive/Desktop: NOT backed up — may be unrecoverable!\n\n"
                "Always save work to OneDrive or SharePoint.\n"
                f"Help: {DEPT_CONTACTS['IT']}"
            ),
            confidence=90,
            source="it_policy",
            keyword_match=True,
        )

    # ── Security Incident ─────────────────────────────────────────────────────
    if any(phrase in q for phrase in _INCIDENT_PHRASES):
        return AgentResponse(
            answer=(
                "**Security Incident Response**\n\n"
                "If you suspect a security breach or incident:\n\n"
                "**Immediate Actions:**\n"
                "1. Stay calm — do not delete or alter anything\n"
                "2. Disconnect device from network (unplug cable or turn off Wi-Fi)\n"
                "3. Do NOT turn off your computer\n"
                f"4. Call IT Security immediately: Ext. {IT_HELPDESK_EXT} (24/7)\n"
                "5. After-hours critical: +971-55-XXX-XXXX\n\n"
                "**What to Report:**\n"
                "- Unusual pop-ups or system behavior\n"
                "- Unexpected account lockouts or password changes\n"
                "- Files being encrypted or disappearing\n"
                "- Unauthorized logins to your account\n"
                "- Suspected phishing that you clicked\n"
                "- Lost or stolen company device\n\n"
                "**Anonymous Reporting:**\n"
                "IT Portal → Security → Report Incident (no login required)\n\n"
                "**Do NOT:**\n"
                "- Try to investigate or fix it yourself\n"
                "- Tell others beyond your manager\n"
                "- Pay any ransom demands\n\n"
                f"Security: security@company.com | Ext. {IT_HELPDESK_EXT}"
            ),
            confidence=92,
            source="it_policy",
            keyword_match=True,
        )

    # ── Software Request ──────────────────────────────────────────────────────
    if any(phrase in q for phrase in _SOFTWARE_PHRASES):
        return AgentResponse(
            answer=(
                "**Software Installation Policy**\n\n"
                "**Standard Pre-installed Software:**\n"
                "Microsoft 365 (Word, Excel, PowerPoint, Teams, OneDrive)\n"
                "Cisco AnyConnect VPN | CrowdStrike Falcon | Zoom | Chrome | Edge\n\n"
                "**Requesting New Software:**\n"
                "1. Check IT Portal → Software Catalog (no approval if already listed)\n"
                "2. If not in catalog: IT Portal → Software → New Software Request\n"
                "3. Include: Software name, vendor, purpose, cost estimate\n"
                "4. IT evaluates security + license compliance\n"
                "5. Approval: Manager (free software) + Finance (paid >AED 500)\n"
                "6. Approved software added to catalog within 5 business days\n\n"
                "**⛔ Prohibited:**\n"
                "- Downloading software directly from internet without IT approval\n"
                "- Cracked, pirated, or unlicensed software\n"
                "- Browser extensions without IT approval\n"
                "- Personal software on company device\n\n"
                "Why? Unknown software = malware risk + legal/audit liability\n\n"
                f"Requests: IT Portal | Help: {DEPT_CONTACTS['IT']}"
            ),
            confidence=90,
            source="it_policy",
            keyword_match=True,
        )

    # ── Device / Hardware ─────────────────────────────────────────────────────
    if any(phrase in q for phrase in _DEVICE_PHRASES):
        return AgentResponse(
            answer=(
                "**Device and Equipment Support**\n\n"
                "**Immediate help for device issues:**\n"
                f"- IT Helpdesk: Ext. {IT_HELPDESK_EXT}\n"
                "- Email: it-support@company.com\n"
                "- IT Portal → Raise Ticket → Category: Hardware\n\n"
                "**Quick Fixes to Try First:**\n"
                "- Computer slow: Restart the computer\n"
                "- Screen issues: Check cable connections\n"
                "- Wi-Fi problems: Forget network and reconnect\n"
                "- Black screen: Hold power button 10 seconds to force restart\n\n"
                "**Damaged / Broken Device:**\n"
                "- Report to IT immediately (even minor damage)\n"
                "- Do NOT attempt to open or repair device yourself\n"
                "- Loaner devices available from IT for critical cases\n\n"
                "**Lost or Stolen Device:**\n"
                "1. Report to IT within 1 hour of discovery\n"
                "2. IT remotely wipes device to protect data\n"
                "3. File police report if stolen\n"
                "4. Replacement device issued for first incident\n\n"
                "Device refresh: Laptops replaced every 3 years.\n"
                f"Support: {DEPT_CONTACTS['IT']}"
            ),
            confidence=90,
            source="it_policy",
            keyword_match=True,
        )

    # ── Printer ───────────────────────────────────────────────────────────────
    if any(phrase in q for phrase in _PRINTER_PHRASES):
        return AgentResponse(
            answer=(
                "**Printing and Scanning Guide**\n\n"
                "**Printer Setup:**\n"
                "- Printers auto-configure on company devices at first login\n"
                "- If not showing: IT Portal → Printer Setup → Auto-Add\n\n"
                "**Secure Printing (for confidential documents):**\n"
                "1. Select 'Secure Print' in print dialog\n"
                "2. Set your 4-digit PIN\n"
                "3. Walk to printer, swipe badge or enter PIN\n"
                "4. Print job held for 4 hours then auto-deleted\n\n"
                "**Scanning:**\n"
                "- Scan to email: Press Scan → Email → Enter your company email\n"
                "- Scan to SharePoint: Scan → SharePoint → Select folder\n\n"
                "**Cannot Print?**\n"
                "- Check printer is selected (not 'Microsoft Print to PDF')\n"
                "- Restart Print Spooler: Services.msc → Print Spooler → Restart\n"
                "- Check printer is online (not showing error light)\n"
                "- IT Ticket for persistent issues\n\n"
                "🌱 Please print double-sided and in black & white to reduce waste.\n\n"
                f"Support: IT Ext. {IT_HELPDESK_EXT}"
            ),
            confidence=88,
            source="it_policy",
            keyword_match=True,
        )

    # ── Password Policy ───────────────────────────────────────────────────────
    if any(kw in q for kw in ["password", "reset", "forgot", "credentials", "locked out", "account locked"]):
        return AgentResponse(
            answer=(
                "**Password Policy and Reset**\n\n"
                "**Password Requirements:**\n"
                "- Minimum **12 characters** (16+ recommended)\n"
                "- Must include: Uppercase, lowercase, number, special character\n"
                "- Cannot be same as last 12 passwords\n"
                f"- Expires every **{PASSWORD_EXPIRY_DAYS} days**\n\n"
                "**Reset Your Password:**\n"
                "Method 1: Ctrl+Alt+Del → Change Password (Windows)\n"
                "Method 2: https://passwordreset.company.internal\n"
                "  - Enter company email → verify via mobile OTP → set new password\n\n"
                "**Locked Out?**\n"
                f"Call IT Helpdesk: Ext. {IT_HELPDESK_EXT}\n"
                "Video verification required — have your employee ID ready.\n\n"
                "**MFA Setup (Mandatory):**\n"
                f"- Required for all accounts: {MFA_METHODS}\n"
                "- Setup: IT Portal → My Account → Enable MFA\n\n"
                "**⚠️ Security Reminder:**\n"
                "- IT will NEVER ask for your password\n"
                "- Never share passwords — even with managers\n"
                "- Use Microsoft Authenticator or similar password manager\n\n"
                f"Help: IT Ext. {IT_HELPDESK_EXT} | it-support@company.com"
            ),
            confidence=92,
            source="it_policy",
            keyword_match=True,
        )

    # ── Email / Account ───────────────────────────────────────────────────────
    if any(kw in q for kw in ["email", "account", "outlook", "office 365", "microsoft teams", "teams"]):
        return AgentResponse(
            answer=(
                "**Email Account and Microsoft 365 Guide**\n\n"
                "**Your company email:** firstname.lastname@company.com\n\n"
                "**Access Methods:**\n"
                "- Laptop: Outlook desktop app (pre-installed)\n"
                "- Browser: https://outlook.company.com\n"
                "- Mobile: Outlook app (iOS/Android) + register device\n\n"
                "**Microsoft 365 Apps Included:**\n"
                "Word, Excel, PowerPoint, Teams, OneDrive, SharePoint, OneNote\n\n"
                "**Teams Quick Start:**\n"
                "- Chat: Search colleague by name → message icon\n"
                "- Channels: Organized team/project communication\n"
                "@Mention to notify: @firstname\n"
                "- File sharing: Drag and drop in chat\n\n"
                "**Email Not Working?**\n"
                "- Restart Outlook (close completely, reopen)\n"
                "- Safe mode: Hold Ctrl while clicking Outlook icon\n"
                "- Web backup: outlook.company.com\n"
                "- Check MFA is working on your phone\n\n"
                "**New Device Setup:**\n"
                "Open Outlook → Add Account → Enter company email → Sign in\n\n"
                f"IT Support: Ext. {IT_HELPDESK_EXT}"
            ),
            confidence=88,
            source="it_policy",
            keyword_match=True,
        )

    # ── General IT security / laptop ─────────────────────────────────────────
    if any(kw in q for kw in ["laptop", "device", "computer", "equipment", "hardware", "monitor"]):
        return AgentResponse(
            answer=(
                "**Device and Equipment Policy**\n\n"
                "**Provided on Day 1:**\n"
                "- Company laptop (configured and ready with all software)\n"
                "- Access badge, office desk setup\n"
                "- Mobile phone (Grade 4+ only)\n\n"
                "**Device Configuration:**\n"
                f"- {ANTIVIRUS_TOOL} (security) — do not disable\n"
                "- Full disk encryption (BitLocker/FileVault)\n"
                "- MDM managed (Intune) — security policies enforced\n"
                "- VPN client pre-installed\n\n"
                "**Usage Rules:**\n"
                "- Business use only (limited personal use during breaks)\n"
                "- Do not allow others to use your company device\n"
                "- Do not disable security software\n"
                "- Screen lock: Always when leaving desk (Win+L)\n\n"
                "**Device Refresh:** Laptops replaced every 3 years\n"
                "**Accessories:** Request monitor, keyboard, headset via IT Portal\n\n"
                f"Issues: IT Portal → Raise Ticket | Ext. {IT_HELPDESK_EXT}"
            ),
            confidence=90,
            source="it_policy",
            keyword_match=True,
        )

    # ── IT policy summary (informational — not an approval action) ───────────────
    if "system report" in q or "it report" in q or "it summary" in q:
        return AgentResponse(
            answer=(
                "**IT Environment Summary**\n\n"
                f"- **Endpoint Protection:** {ANTIVIRUS_TOOL}\n"
                f"- **Ticket SLA:** {TICKET_RESPONSE_HRS}hr first response, 24hr resolution\n"
                "- **VPN:** Cisco AnyConnect — IT Portal → VPN → Download\n"
                "- **Cloud Storage:** OneDrive (1TB) / SharePoint\n"
                "- **Email/Collaboration:** Microsoft 365 (Teams, Outlook)\n"
                "- **Security patches:** Applied monthly during maintenance window\n\n"
                f"Raise a ticket: IT Portal → New Ticket | Ext. {IT_HELPDESK_EXT}"
            ),
            confidence=88,
            source="it_policy",
            keyword_match=True,
        )

    # ── RAG fallback ──────────────────────────────────────────────────────────
    rag = search_knowledge_base_raw(query)
    source = rag.get("source") or "it_kb"

    if source and not any(s in source.lower() for s in ["it_", "it1", "it_policy", "it_kb"]):
        logger.warning("it_agent.source_filtered", source=source)
        source = "it_kb"
        rag["context"] = ""

    formatted = clean_rag_output(rag.get("context", ""), department="IT")

    if not formatted:
        return AgentResponse(
            answer=(
                f"I couldn't find specific information for your IT query. "
                f"Please contact IT Support directly:\n\n"
                f"📧 {DEPT_CONTACTS['IT']}\n"
                f"📞 Internal: Ext. {IT_HELPDESK_EXT}\n"
                f"🌐 IT Portal: it.company.internal\n\n"
                f"Or try asking about: password reset, VPN, MFA, phishing, software "
                f"requests, device issues, or cloud storage."
            ),
            confidence=30,
            source="it_kb",
        )

    return AgentResponse(
        answer=formatted,
        confidence=rag.get("confidence", 50),
        source=source,
        rag_used=True,
    )
