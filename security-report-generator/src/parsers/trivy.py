from typing import List, Dict, Any, Optional
try:
    from ..models import Finding, Severity, Category
    from ..fingerprint import (
        generate_dependency_fingerprint,
        generate_misconfig_fingerprint,
        generate_secret_fingerprint,
        normalize_file_path,
    )
except (ImportError, ValueError):
    from models import Finding, Severity, Category
    from fingerprint import (
        generate_dependency_fingerprint,
        generate_misconfig_fingerprint,
        generate_secret_fingerprint,
        normalize_file_path,
    )


def parse_trivy_report(data: Any, scan_context: str = "trivy") -> List[Finding]:
    findings: List[Finding] = []
    if not data or not isinstance(data, dict):
        return findings

    artifact_name = data.get("ArtifactName", "")
    results = data.get("Results", [])
    if not isinstance(results, list):
        return findings

    for target_res in results:
        if not isinstance(target_res, dict):
            continue

        target = normalize_file_path(target_res.get("Target") or artifact_name)

        # 1. Parse Vulnerabilities (Dependencies & OS packages)
        vulns = target_res.get("Vulnerabilities", [])
        if isinstance(vulns, list):
            for v in vulns:
                if not isinstance(v, dict):
                    continue
                cve_id = v.get("VulnerabilityID", "CVE-UNKNOWN")
                pkg_name = v.get("PkgName", "unknown-pkg")
                installed_ver = v.get("InstalledVersion", "unknown")
                fixed_ver = v.get("FixedVersion")
                raw_sev = v.get("Severity", "UNKNOWN")
                norm_sev = Severity.normalize(raw_sev)

                title = v.get("Title") or f"{cve_id} in {pkg_name}"
                description = v.get("Description") or f"Vulnerability {cve_id} detected in {pkg_name} ({installed_ver})"
                ref_url = v.get("PrimaryURL") or (v.get("References")[0] if v.get("References") else None)

                fingerprint = generate_dependency_fingerprint(
                    cve=cve_id,
                    package=pkg_name,
                    installed_version=installed_ver
                )

                remediation = f"Upgrade {pkg_name} to {fixed_ver}." if fixed_ver else "No fix version currently available. Review upstream advisories."

                f = Finding(
                    fingerprint=fingerprint,
                    scanner=scan_context,
                    category=Category.DEPENDENCY.value,
                    severity=norm_sev.value,
                    title=f"Vulnerable Dependency: {pkg_name} ({cve_id})",
                    description=description,
                    file=target,
                    line=None,
                    rule_id=cve_id,
                    cve=cve_id,
                    package=pkg_name,
                    installed_version=installed_ver,
                    fixed_version=fixed_ver,
                    url=ref_url,
                    remediation=remediation,
                    status="OPEN",
                    detected_by=[scan_context],
                    metadata={
                        "artifact": artifact_name,
                        "class": target_res.get("Class"),
                        "type": target_res.get("Type"),
                        "cvss": v.get("CVSS"),
                    }
                )
                findings.append(f)

        # 2. Parse Misconfigurations (e.g., Dockerfile misconfigs)
        misconfigs = target_res.get("Misconfigurations", [])
        if isinstance(misconfigs, list):
            for m in misconfigs:
                if not isinstance(m, dict):
                    continue
                rule_id = m.get("ID", "MISCONFIG")
                title = m.get("Title") or f"Misconfiguration {rule_id}"
                desc = m.get("Description") or m.get("Message") or title
                raw_sev = m.get("Severity", "MEDIUM")
                norm_sev = Severity.normalize(raw_sev)
                resolution = m.get("Resolution")
                ref_url = m.get("PrimaryURL")

                start_line = None
                lines_info = m.get("CauseMetadata", {}).get("Code", {}).get("Lines")
                if lines_info and isinstance(lines_info, list) and len(lines_info) > 0:
                    start_line = lines_info[0].get("Number")

                fingerprint = generate_misconfig_fingerprint(
                    rule_id=rule_id,
                    resource=m.get("Namespace") or target,
                    file_path=target
                )

                f = Finding(
                    fingerprint=fingerprint,
                    scanner=scan_context,
                    category=Category.MISCONFIG.value,
                    severity=norm_sev.value,
                    title=f"Misconfiguration: {title}",
                    description=desc,
                    file=target,
                    line=start_line,
                    rule_id=rule_id,
                    url=ref_url,
                    remediation=resolution or "Review and correct configuration according to policy.",
                    status="OPEN",
                    detected_by=[scan_context],
                    metadata={"target": target}
                )
                findings.append(f)

        # 3. Parse Secrets if Trivy secret scanning was enabled
        secrets = target_res.get("Secrets", [])
        if isinstance(secrets, list):
            for s in secrets:
                if not isinstance(s, dict):
                    continue
                rule_id = s.get("RuleID", "trivy-secret")
                title = s.get("Title") or "Hardcoded Secret"
                file_path = target
                start_line = s.get("StartLine")
                raw_sev = s.get("Severity", "CRITICAL")
                norm_sev = Severity.normalize(raw_sev)

                fingerprint = generate_secret_fingerprint(
                    rule_id=rule_id,
                    file_path=file_path,
                    secret_value=None
                )

                f = Finding(
                    fingerprint=fingerprint,
                    scanner=scan_context,
                    category=Category.SECRET.value,
                    severity=norm_sev.value,
                    title=f"Secret Detected: {title}",
                    description=f"Trivy detected hardcoded secret in {file_path}",
                    file=file_path,
                    line=start_line,
                    rule_id=rule_id,
                    remediation="Immediately revoke and rotate the secret.",
                    status="OPEN",
                    detected_by=[scan_context],
                )
                findings.append(f)

    return findings
