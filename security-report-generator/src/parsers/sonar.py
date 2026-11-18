from typing import List, Dict, Any, Optional
try:
    from ..models import Finding, Severity, Category
    from ..fingerprint import generate_sonar_fingerprint, normalize_file_path
except (ImportError, ValueError):
    from models import Finding, Severity, Category
    from fingerprint import generate_sonar_fingerprint, normalize_file_path


def parse_sonar_report(data: Any, sonarqube_base_url: Optional[str] = None) -> List[Finding]:
    findings: List[Finding] = []
    if not data or not isinstance(data, dict):
        return findings

    issues = data.get("issues", [])
    if not isinstance(issues, list):
        return findings

    for issue in issues:
        if not isinstance(issue, dict):
            continue

        rule_id = issue.get("rule", "sonar-rule")
        message = issue.get("message", "SonarQube code finding")
        raw_sev = issue.get("severity", "MAJOR")
        norm_sev = Severity.normalize(raw_sev)
        issue_type = issue.get("type", "CODE_SMELL").upper()

        # Component in SonarQube is typically "projectKey:path/to/file.ts"
        raw_component = issue.get("component", "")
        file_path = raw_component.split(":", 1)[-1] if ":" in raw_component else raw_component
        file_path = normalize_file_path(file_path)

        line_num = issue.get("line")
        try:
            line = int(line_num) if line_num is not None else None
        except (ValueError, TypeError):
            line = None

        if issue_type == "SECURITY_HOTSPOT":
            category = Category.HOTSPOT.value
        elif issue_type == "VULNERABILITY":
            category = Category.CODE.value
        elif "SECRET" in rule_id.upper() or "CREDENTIAL" in message.upper():
            category = Category.SECRET.value
        else:
            category = Category.CODE.value

        fingerprint = generate_sonar_fingerprint(
            rule_id=rule_id,
            component=file_path,
            line=line
        )

        sonar_link = None
        if sonarqube_base_url:
            base = sonarqube_base_url.rstrip("/")
            project_key = issue.get("project", "")
            sonar_link = f"{base}/project/issues?id={project_key}&issues={issue.get('key')}&open={issue.get('key')}"

        f = Finding(
            fingerprint=fingerprint,
            scanner="sonarqube",
            category=category,
            severity=norm_sev.value,
            title=f"SonarQube {issue_type}: {message}",
            description=f"Rule {rule_id}: {message} at {file_path}:{line or 1}",
            file=file_path,
            line=line,
            rule_id=rule_id,
            url=sonar_link,
            remediation="Inspect issue in SonarQube dashboard, address the flagged code pattern or request security review.",
            status=issue.get("status", "OPEN"),
            detected_by=["sonarqube"],
            metadata={
                "issue_key": issue.get("key"),
                "type": issue_type,
                "debt": issue.get("debt"),
                "tags": issue.get("tags", []),
                "project": issue.get("project"),
            }
        )
        findings.append(f)

    return findings
