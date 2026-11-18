import json
from typing import Dict, Any, Optional, List
try:
    from .models import AggregatedReport, Severity
except (ImportError, ValueError):
    from models import AggregatedReport, Severity


def generate_notification_summary(
    report: AggregatedReport,
    owners_config: Optional[Dict[str, Any]] = None,
    service_name: str = "backend",
) -> Dict[str, Any]:
    meta = report.metadata
    summary = report.summary
    crit_count = summary.get(Severity.CRITICAL.value, 0)
    high_count = summary.get(Severity.HIGH.value, 0)
    med_count = summary.get(Severity.MEDIUM.value, 0)
    low_count = summary.get(Severity.LOW.value, 0)
    total_unique = len(report.findings)

    # Security gate decision: Block if Critical > 0 or build failed
    gate_passed = (crit_count == 0) and (meta.build_status.upper() in ("PASSED", "SUCCESS"))
    gate_status = "PASSED" if gate_passed else "FAILED"

    # Recipients extraction from owners_config
    service_cfg = {}
    if owners_config and "services" in owners_config:
        service_cfg = owners_config["services"].get(service_name, {})

    service_emails: List[str] = service_cfg.get("email", [])
    service_chat: str = service_cfg.get("chat", "")
    service_devs: List[str] = service_cfg.get("developers", [])

    # If critical, add security and devops team if defined
    escalated_emails = list(service_emails)
    if crit_count > 0 and owners_config and "escalation" in owners_config:
        esc = owners_config["escalation"]
        for e in esc.get("email", []):
            if e not in escalated_emails:
                escalated_emails.append(e)

    # Email Subject
    status_tag = "CRITICAL FAILED" if crit_count > 0 else ("FAILED" if not gate_passed else "PASSED")
    email_subject = f"[{status_tag}] Security Scan {meta.project}-{service_name} | Build #{meta.build_num}"

    # Top critical/high findings preview for notifications
    critical_findings_preview = []
    for f in report.findings:
        if f.severity in (Severity.CRITICAL.value, Severity.HIGH.value):
            loc = f"{f.file}:{f.line}" if f.file and f.line else (f.file or f.package or "N/A")
            critical_findings_preview.append({
                "title": f.title,
                "severity": f.severity,
                "location": loc,
                "detected_by": ", ".join(f.detected_by),
                "remediation": f.remediation or "Review and fix finding."
            })
            if len(critical_findings_preview) >= 5:
                break

    # Construct Plain Text Body for Email / Alert
    findings_text = ""
    for idx, cf in enumerate(critical_findings_preview, 1):
        findings_text += f"{idx}. {cf['title']}\n"
        findings_text += f"   Severity: {cf['severity']}\n"
        findings_text += f"   Location: {cf['location']}\n"
        findings_text += f"   Detected By: {cf['detected_by']}\n"
        findings_text += f"   Remediation: {cf['remediation']}\n\n"

    email_body = f"""Project: {meta.project}
Service: {service_name.capitalize()}
Branch: {meta.branch}
Commit: {meta.commit}
Build: #{meta.build_num}
Triggered By: {meta.triggered_by}
Security Gate: {gate_status}

Security Summary:
Critical: {crit_count}
High:     {high_count}
Medium:   {med_count}
Low:      {low_count}
Total Unique Findings: {total_unique}
Duplicates Removed:    {report.deduplication_summary.get('duplicates_removed', 0)}

{"Key Findings Requiring Attention:" if critical_findings_preview else "No Critical or High findings detected."}
{findings_text}
Links:
Jenkins Build: {meta.jenkins_url or 'N/A'}
SonarQube:     {meta.sonarqube_url or 'N/A'}
DefectDojo:    {meta.defectdojo_url or 'N/A'}

Action Required:
{"Please resolve reported Critical/High findings immediately to proceed with deployment." if not gate_passed else "All security quality gates passed."}
"""

    # Google Chat webhook formatted message
    chat_payload = {
        "text": f"*{email_subject}*\n\n"
                f"• *Service*: `{service_name}`\n"
                f"• *Build*: `#{meta.build_num}` ({meta.branch})\n"
                f"• *Gate Status*: *{gate_status}*\n"
                f"• *Vulnerabilities*: 🚨 Critical: `{crit_count}` | ⚠️ High: `{high_count}` | Medium: `{med_count}` | Low: `{low_count}`\n"
                f"• *DefectDojo*: {meta.defectdojo_url or 'Dashboard'}\n"
                f"• *Jenkins*: {meta.jenkins_url or 'Build link'}"
    }

    return {
        "gate_status": gate_status,
        "gate_passed": gate_passed,
        "critical_count": crit_count,
        "high_count": high_count,
        "medium_count": med_count,
        "low_count": low_count,
        "total_unique": total_unique,
        "duplicates_removed": report.deduplication_summary.get("duplicates_removed", 0),
        "recipients_email": escalated_emails if crit_count > 0 else service_emails,
        "chat_channel": service_chat,
        "email_subject": email_subject,
        "email_body": email_body.strip(),
        "chat_payload": chat_payload,
    }
