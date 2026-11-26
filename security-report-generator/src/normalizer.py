from typing import List, Dict, Any, Optional
try:
    from .models import Finding, ReportMetadata, AggregatedReport
    from .parsers.gitleaks import parse_gitleaks_report
    from .parsers.trivy import parse_trivy_report
    from .parsers.sonar import parse_sonar_report
    from .deduplicator import deduplicate_findings
    from .severity import (
        sort_findings_by_severity,
        count_findings_by_severity,
        count_findings_by_scanner,
    )
except (ImportError, ValueError):
    from models import Finding, ReportMetadata, AggregatedReport
    from parsers.gitleaks import parse_gitleaks_report
    from parsers.trivy import parse_trivy_report
    from parsers.sonar import parse_sonar_report
    from deduplicator import deduplicate_findings
    from severity import (
        sort_findings_by_severity,
        count_findings_by_severity,
        count_findings_by_scanner,
    )


def normalize_all_scans(
    gitleaks_data: Optional[Any] = None,
    trivy_fs_data: Optional[Any] = None,
    trivy_image_data: Optional[Any] = None,
    sonar_data: Optional[Any] = None,
    metadata: Optional[ReportMetadata] = None,
    sonarqube_base_url: Optional[str] = None,
) -> AggregatedReport:
    raw_findings: List[Finding] = []

    if gitleaks_data:
        raw_findings.extend(parse_gitleaks_report(gitleaks_data))

    if trivy_fs_data:
        raw_findings.extend(parse_trivy_report(trivy_fs_data, scan_context="trivy-fs"))

    if trivy_image_data:
        raw_findings.extend(parse_trivy_report(trivy_image_data, scan_context="trivy-image"))

    if sonar_data:
        raw_findings.extend(parse_sonar_report(sonar_data, sonarqube_base_url=sonarqube_base_url))

    # Deduplicate findings
    deduped_findings, dedup_stats = deduplicate_findings(raw_findings)

    # Sort findings by severity
    sorted_findings = sort_findings_by_severity(deduped_findings)

    # Calculate summaries
    severity_counts = count_findings_by_severity(sorted_findings)
    scanner_counts = count_findings_by_scanner(sorted_findings)

    meta = metadata or ReportMetadata()

    return AggregatedReport(
        metadata=meta,
        findings=sorted_findings,
        summary=severity_counts,
        scanner_summary=scanner_counts,
        deduplication_summary=dedup_stats,
    )
