from typing import List, Dict
try:
    from .models import Finding, Severity
except (ImportError, ValueError):
    from models import Finding, Severity


def sort_findings_by_severity(findings: List[Finding]) -> List[Finding]:
    def sort_key(f: Finding):
        sev_rank = Severity.normalize(f.severity).rank
        return (-sev_rank, f.category, f.file or "", f.line or 0, f.title)

    return sorted(findings, key=sort_key)


def group_findings_by_severity(findings: List[Finding]) -> Dict[str, List[Finding]]:
    grouped: Dict[str, List[Finding]] = {
        Severity.CRITICAL.value: [],
        Severity.HIGH.value: [],
        Severity.MEDIUM.value: [],
        Severity.LOW.value: [],
        Severity.INFO.value: [],
    }
    for f in findings:
        sev = Severity.normalize(f.severity).value
        if sev not in grouped:
            grouped[sev] = []
        grouped[sev].append(f)
    return grouped


def count_findings_by_severity(findings: List[Finding]) -> Dict[str, int]:
    counts: Dict[str, int] = {
        Severity.CRITICAL.value: 0,
        Severity.HIGH.value: 0,
        Severity.MEDIUM.value: 0,
        Severity.LOW.value: 0,
        Severity.INFO.value: 0,
    }
    for f in findings:
        sev = Severity.normalize(f.severity).value
        counts[sev] = counts.get(sev, 0) + 1
    return counts


def count_findings_by_scanner(findings: List[Finding]) -> Dict[str, int]:
    scanner_counts: Dict[str, int] = {}
    for f in findings:
        for sc in f.detected_by:
            scanner_counts[sc] = scanner_counts.get(sc, 0) + 1
    return scanner_counts
