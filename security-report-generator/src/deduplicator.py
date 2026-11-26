from typing import List, Dict, Any, Tuple
try:
    from .models import Finding, Severity, Category
except (ImportError, ValueError):
    from models import Finding, Severity, Category


def deduplicate_findings(findings: List[Finding]) -> Tuple[List[Finding], Dict[str, Any]]:
    """
    Implements Level 1 Build-Level Deduplication across scanners.
    Deduplicates:
    1. Exact fingerprint matches.
    2. Cross-scanner secret leaks on the same file and line.
    3. Cross-scanner dependency CVEs on the same package and version.
    """
    total_raw = len(findings)
    if not findings:
        return [], {"total_raw": 0, "total_unique": 0, "duplicates_removed": 0}

    unique_map: Dict[str, Finding] = {}
    total_detections_map: Dict[str, int] = {}

    for f in findings:
        if f.category == Category.DEPENDENCY.value and f.cve and f.package:
            cve_clean = f.cve.strip().upper()
            pkg_clean = f.package.strip().lower()
            key = f"dep:{cve_clean}:{pkg_clean}"
        elif f.category == Category.SECRET.value and f.file and f.line is not None:
            key = f"secret:{f.file}:{f.line}"
        else:
            key = f.fingerprint

        if key in unique_map:
            existing = unique_map[key]
            total_detections_map[key] += 1

            for s in f.detected_by:
                if s not in existing.detected_by:
                    existing.detected_by.append(s)

            existing_sev = Severity.normalize(existing.severity)
            incoming_sev = Severity.normalize(f.severity)
            if incoming_sev.rank > existing_sev.rank:
                existing.severity = incoming_sev.value

            if not existing.url and f.url:
                existing.url = f.url
            if not existing.remediation and f.remediation:
                existing.remediation = f.remediation

            existing.metadata["total_detections"] = total_detections_map[key]
        else:
            unique_map[key] = f
            total_detections_map[key] = 1
            f.metadata["total_detections"] = 1

    unique_list = list(unique_map.values())
    total_unique = len(unique_list)
    duplicates_removed = total_raw - total_unique

    stats = {
        "total_raw": total_raw,
        "total_unique": total_unique,
        "duplicates_removed": duplicates_removed,
    }
    return unique_list, stats
