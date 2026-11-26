"""
dojo_exporter.py
Converts the aggregated, deduplicated findings into DefectDojo's
"Generic Findings Import" JSON format.

Schema reference:
  https://defectdojo.github.io/django-DefectDojo/integrations/parsers/file/generic/

DefectDojo expects: { "findings": [ { ...per-finding fields... } ] }
"""

from typing import List, Dict, Any
try:
    from .models import AggregatedReport, Severity, Finding
except (ImportError, ValueError):
    from models import AggregatedReport, Severity, Finding

# Map internal severity values → DefectDojo severity strings
_SEVERITY_MAP: Dict[str, str] = {
    "CRITICAL": "Critical",
    "HIGH":     "High",
    "MEDIUM":   "Medium",
    "LOW":      "Low",
    "INFO":     "Informational",
}

# Category → CWE hint (best-effort defaults)
_CATEGORY_CWE: Dict[str, int] = {
    "secret":           798,   # Hard-coded credentials
    "dependency":       937,   # Using components with known vulnerabilities
    "code":             20,    # Improper input validation (generic code)
    "misconfiguration": 16,    # Configuration
    "security_hotspot": 693,   # Protection mechanism failure
    "other":            0,
}


def _build_dojo_finding(f: Finding) -> Dict[str, Any]:
    """Convert a single internal Finding → one DefectDojo Generic Finding dict."""

    sev_str = _SEVERITY_MAP.get(f.severity.upper(), "Medium")

    # Build a rich description
    desc_parts = [f.description or f.title]
    if f.detected_by:
        desc_parts.append(f"Detected by: {', '.join(f.detected_by)}")
    if f.package and f.installed_version:
        desc_parts.append(f"Package: {f.package} @ {f.installed_version}")
    if f.fixed_version:
        desc_parts.append(f"Fixed in: {f.fixed_version}")
    if f.cve and f.cve != f.rule_id:
        desc_parts.append(f"CVE: {f.cve}")
    description = "\n".join(desc_parts)

    # file_path + line
    file_path = f.file or ""
    line = f.line if f.line is not None else None

    # CWE — try to extract from rule_id (e.g. "CWE-327", "cwe327", "S2245")
    cwe = _CATEGORY_CWE.get(f.category, 0)
    if f.rule_id:
        import re
        m = re.search(r'[Cc][Ww][Ee][-_]?(\d+)', f.rule_id)
        if m:
            cwe = int(m.group(1))

    # Build the dict
    finding: Dict[str, Any] = {
        "title":                f.title,
        "severity":             sev_str,
        "description":          description,
        "active":               True,
        "verified":             False,
        "unique_id_from_tool":  f.fingerprint,
    }

    if file_path:
        finding["file_path"] = file_path
    if line:
        finding["line"] = line
    if cwe:
        finding["cwe"] = cwe
    if f.remediation:
        finding["mitigation"] = f.remediation
    if f.url:
        finding["references"] = f.url

    return finding


def export_dojo_generic(report: AggregatedReport) -> Dict[str, Any]:
    """
    Convert an AggregatedReport into DefectDojo Generic Findings Import format.
    Returns a dict ready to be JSON-serialised and uploaded.
    """
    return {
        "findings": [_build_dojo_finding(f) for f in report.findings]
    }
