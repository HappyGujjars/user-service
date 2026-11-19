"""
notification_summary.py

Builds:
  - notification summary JSON (gate status, counts, recipients)
  - Rich Google Chat Cards v2 payload (developer-safe, NO internal tool URLs)
  - Plain-text email body
"""

from typing import Dict, Any, Optional, List

try:
    from .models import AggregatedReport, Severity
except (ImportError, ValueError):
    from models import AggregatedReport, Severity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sev_icon(sev: str) -> str:
    return {
        "CRITICAL": "🔴",
        "HIGH":     "🟠",
        "MEDIUM":   "🟡",
        "LOW":      "⚪",
        "INFO":     "🔵",
    }.get(sev.upper(), "⚪")


def _category_label(category: str) -> str:
    return {
        "secret":           "Secret / Credential Leak",
        "dependency":       "Dependency Vulnerability",
        "code":             "Code Vulnerability",
        "misconfiguration": "Misconfiguration",
        "security_hotspot": "Security Hotspot",
    }.get(category.lower(), "Finding")


def _scanner_label(scanners: List[str]) -> str:
    labels = {
        "gitleaks":    "Gitleaks",
        "sonarqube":   "SonarQube",
        "trivy-fs":    "Trivy (Filesystem)",
        "trivy-image": "Trivy (Image)",
    }
    return ", ".join(labels.get(s.lower(), s.capitalize()) for s in scanners)


# ---------------------------------------------------------------------------
# Google Chat Cards v2 builder
# ---------------------------------------------------------------------------

def _build_chat_card(
    meta,
    gate_passed: bool,
    gate_status: str,
    crit_count: int,
    high_count: int,
    med_count: int,
    low_count: int,
    total_unique: int,
    duplicates_removed: int,
    critical_findings: list,
    high_findings: list,
    service_name: str,
) -> Dict[str, Any]:
    """
    Build a rich Google Chat Cards v2 payload.
    Developer-safe: NO internal Jenkins / SonarQube / DefectDojo URLs exposed.
    """

    gate_icon  = "🔴" if not gate_passed else "✅"
    gate_color = "#B71C1C" if not gate_passed else "#1B5E20"
    header_subtitle = (
        f"{meta.project.capitalize()} › {service_name.capitalize()} › Branch: {meta.branch} › Build #{meta.build_num}"
    )

    # ── Header ──────────────────────────────────────────────────────────────
    header = {
        "title":    f"{gate_icon}  Security Gate {gate_status} — {meta.project.upper()}",
        "subtitle": header_subtitle,
        "imageUrl": "https://raw.githubusercontent.com/devicons/devicon/master/icons/linux/linux-original.svg",
        "imageType": "CIRCLE",
    }

    sections: List[Dict] = []

    # ── Section 1: Build Info ────────────────────────────────────────────────
    commit_short = meta.commit[:12] if meta.commit else "N/A"
    sections.append({
        "header": "📦 Build Information",
        "widgets": [
            {"decoratedText": {"topLabel": "Project",      "text": f"<b>{meta.project.capitalize()}</b>"}},
            {"decoratedText": {"topLabel": "Service",      "text": service_name.capitalize()}},
            {"decoratedText": {"topLabel": "Branch",       "text": f"<b>{meta.branch}</b>"}},
            {"decoratedText": {"topLabel": "Build",        "text": f"#{meta.build_num}"}},
            {"decoratedText": {"topLabel": "Commit",       "text": f"<font color='#555'><i>{commit_short}</i></font>"}},
            {"decoratedText": {"topLabel": "Triggered By", "text": meta.triggered_by or "CI"}},
        ]
    })

    # ── Section 2: Security Summary ──────────────────────────────────────────
    deploy_status = (
        "<b><font color='#B71C1C'>⛔ Blocked</font></b> — resolve Critical/High findings first."
        if not gate_passed
        else "<b><font color='#1B5E20'>✅ Cleared</font></b> — ready for deployment."
    )

    sections.append({
        "header": "🛡️ Security Summary",
        "widgets": [
            {"decoratedText": {"topLabel": "🔴 Critical", "text": f"<b><font color='#B71C1C'>{crit_count} findings</font></b>"}},
            {"decoratedText": {"topLabel": "🟠 High",     "text": f"<b><font color='#E65100'>{high_count} findings</font></b>"}},
            {"decoratedText": {"topLabel": "🟡 Medium",   "text": f"{med_count} findings"}},
            {"decoratedText": {"topLabel": "⚪ Low",      "text": f"{low_count} findings"}},
            {"decoratedText": {"topLabel": "Total Unique",       "text": f"<b>{total_unique}</b>"}},
            {"decoratedText": {"topLabel": "Duplicates Removed", "text": str(duplicates_removed)}},
            {"divider": {}},
            {"decoratedText": {"topLabel": "Deployment Status", "text": deploy_status}},
        ]
    })

    # ── Section 3: Critical Findings ────────────────────────────────────────
    if critical_findings:
        crit_widgets = []
        for idx, f in enumerate(critical_findings, 1):
            icon    = _sev_icon(f["severity"])
            scanner = _scanner_label(f["detected_by"])
            cat     = _category_label(f["category"])
            loc     = f["location"] or "N/A"
            detail_lines = [
                f"<b>{icon} #{idx}. {f['title']}</b>",
                f"<font color='#555'>Scanner:</font> {scanner}",
                f"<font color='#555'>Type:</font> {cat}",
                f"<font color='#555'>Location:</font> <i>{loc}</i>",
                f"<font color='#555'>Issue:</font> {f['description']}",
                f"<font color='#1B5E20'><b>Fix:</b></font> {f['remediation']}",
            ]
            if f.get("cve"):
                detail_lines.insert(4, f"<font color='#555'>CVE:</font> <b>{f['cve']}</b>")
            crit_widgets.append({
                "textParagraph": {"text": "<br>".join(detail_lines)}
            })
            if idx < len(critical_findings):
                crit_widgets.append({"divider": {}})

        sections.append({
            "header": f"🔴 Critical Findings ({len(critical_findings)})",
            "collapsible": False,
            "widgets": crit_widgets,
        })

    # ── Section 4: High Findings ─────────────────────────────────────────────
    if high_findings:
        high_widgets = []
        for idx, f in enumerate(high_findings, 1):
            scanner = _scanner_label(f["detected_by"])
            cat     = _category_label(f["category"])
            loc     = f["location"] or "N/A"
            detail_lines = [
                f"<b>🟠 #{idx}. {f['title']}</b>",
                f"<font color='#555'>Scanner:</font> {scanner}",
                f"<font color='#555'>Type:</font> {cat}",
                f"<font color='#555'>Location:</font> <i>{loc}</i>",
                f"<font color='#555'>Issue:</font> {f['description']}",
                f"<font color='#1B5E20'><b>Fix:</b></font> {f['remediation']}",
            ]
            high_widgets.append({
                "textParagraph": {"text": "<br>".join(detail_lines)}
            })
            if idx < len(high_findings):
                high_widgets.append({"divider": {}})

        sections.append({
            "header": f"🟠 High Findings — Top {len(high_findings)} Shown",
            "collapsible": True,
            "uncollapsibleWidgetsCount": 1,
            "widgets": high_widgets,
        })

    # ── Section 5: Required Actions ──────────────────────────────────────────
    if not gate_passed:
        actions_text = (
            "1. Resolve <b>all Critical</b> findings immediately.<br>"
            "2. Review and resolve <b>all High</b> severity findings.<br>"
            "3. Upgrade any vulnerable dependencies flagged by Trivy.<br>"
            "4. Plan remediation for Medium and Low findings.<br>"
            "5. Re-run the pipeline — deployment will auto-unblock when the Security Gate passes."
        )
    else:
        actions_text = "✅ All configured security gate requirements are satisfied. Deployment is cleared."

    sections.append({
        "header": "📋 Required Actions",
        "widgets": [{"textParagraph": {"text": actions_text}}]
    })

    # ── Card assembly ─────────────────────────────────────────────────────────
    return {
        "cardsV2": [{
            "cardId": f"sec-report-{meta.build_num}",
            "card": {
                "header": header,
                "sections": sections,
            }
        }]
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_notification_summary(
    report: AggregatedReport,
    owners_config: Optional[Dict[str, Any]] = None,
    service_name: str = "backend",
) -> Dict[str, Any]:
    meta = report.metadata
    summary = report.summary

    crit_count = summary.get(Severity.CRITICAL.value, 0)
    high_count = summary.get(Severity.HIGH.value,     0)
    med_count  = summary.get(Severity.MEDIUM.value,   0)
    low_count  = summary.get(Severity.LOW.value,      0)
    total_unique = len(report.findings)
    duplicates_removed = report.deduplication_summary.get("duplicates_removed", 0)

    # Gate decision
    gate_passed = (crit_count == 0) and (meta.build_status.upper() in ("PASSED", "SUCCESS"))
    gate_status = "PASSED" if gate_passed else "FAILED"

    # Recipients from owners config
    service_cfg: Dict = {}
    if owners_config and "services" in owners_config:
        service_cfg = owners_config["services"].get(service_name, {})

    service_emails: List[str] = service_cfg.get("email", [])
    service_chat:   str       = service_cfg.get("chat", "")

    escalated_emails = list(service_emails)
    if crit_count > 0 and owners_config and "escalation" in owners_config:
        for e in owners_config["escalation"].get("email", []):
            if e not in escalated_emails:
                escalated_emails.append(e)

    # Email subject
    status_tag    = "CRITICAL FAILED" if crit_count > 0 else ("FAILED" if not gate_passed else "PASSED")
    email_subject = f"[{status_tag}] Security Scan {meta.project}-{service_name} | Build #{meta.build_num}"

    # Collect critical/high findings for chat card and email
    critical_findings: list = []
    high_findings:     list = []
    for f in report.findings:
        loc = f"{f.file}:{f.line}" if f.file and f.line else (f.file or f.package or "N/A")
        entry = {
            "title":       f.title,
            "severity":    f.severity,
            "category":    f.category,
            "location":    loc,
            "description": f.description,
            "detected_by": f.detected_by,
            "remediation": f.remediation or "Review and fix the finding.",
            "cve":         f.cve,
        }
        if f.severity == Severity.CRITICAL.value and len(critical_findings) < 5:
            critical_findings.append(entry)
        elif f.severity == Severity.HIGH.value and len(high_findings) < 5:
            high_findings.append(entry)

    # ── Plain-text email body ─────────────────────────────────────────────────
    findings_text = ""
    for idx, f in enumerate(critical_findings + high_findings, 1):
        icon = _sev_icon(f["severity"])
        findings_text += (
            f"{idx}. {icon} {f['title']}\n"
            f"   Severity:    {f['severity']}\n"
            f"   Scanner:     {_scanner_label(f['detected_by'])}\n"
            f"   Type:        {_category_label(f['category'])}\n"
            f"   Location:    {f['location']}\n"
            f"   Issue:       {f['description']}\n"
            f"   Remediation: {f['remediation']}\n\n"
        )

    commit_short = meta.commit[:12] if meta.commit else "N/A"
    deploy_str = "⛔ BLOCKED — resolve Critical/High findings first." if not gate_passed else "✅ CLEARED — deployment approved."
    heading_str = "Key Findings Requiring Immediate Attention" if findings_text else "No Critical or High findings detected."
    if not gate_passed:
        actions_str = "1. Resolve ALL Critical findings immediately.\n2. Review and fix High severity findings.\n3. Upgrade vulnerable dependencies flagged above.\n4. Re-run the pipeline to unblock deployment."
    else:
        actions_str = "All security gate requirements satisfied. Deployment cleared."
    sep = "=" * 60

    email_body = f"""{sep}
🚨 Security Gate {gate_status} — {meta.project.upper()} / {service_name.capitalize()}
{sep}

Project:      {meta.project}
Service:      {service_name.capitalize()}
Branch:       {meta.branch}
Build:        #{meta.build_num}
Commit:       {commit_short}
Triggered By: {meta.triggered_by or 'CI'}
Gate Status:  {gate_status}

──────────────────────────────
Security Summary
──────────────────────────────
  🔴 Critical : {crit_count}
  🟠 High     : {high_count}
  🟡 Medium   : {med_count}
  ⚪ Low      : {low_count}
  Total Unique: {total_unique}

Deployment:   {deploy_str}

──────────────────────────────
{heading_str}
──────────────────────────────
{findings_text}
──────────────────────────────
Required Actions
──────────────────────────────
{actions_str}
{sep}
""".strip()

    # ── Google Chat Cards v2 payload ──────────────────────────────────────────
    chat_payload = _build_chat_card(
        meta=meta,
        gate_passed=gate_passed,
        gate_status=gate_status,
        crit_count=crit_count,
        high_count=high_count,
        med_count=med_count,
        low_count=low_count,
        total_unique=total_unique,
        duplicates_removed=duplicates_removed,
        critical_findings=critical_findings,
        high_findings=high_findings,
        service_name=service_name,
    )

    return {
        "gate_status":        gate_status,
        "gate_passed":        gate_passed,
        "critical_count":     crit_count,
        "high_count":         high_count,
        "medium_count":       med_count,
        "low_count":          low_count,
        "total_unique":       total_unique,
        "duplicates_removed": duplicates_removed,
        "recipients_email":   escalated_emails if crit_count > 0 else service_emails,
        "chat_channel":       service_chat,
        "email_subject":      email_subject,
        "email_body":         email_body,
        "chat_payload":       chat_payload,
    }
