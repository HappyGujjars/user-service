from typing import List, Dict, Any
try:
    from ..models import Finding, Severity, Category
    from ..fingerprint import generate_secret_fingerprint, normalize_file_path
except (ImportError, ValueError):
    from models import Finding, Severity, Category
    from fingerprint import generate_secret_fingerprint, normalize_file_path


def parse_gitleaks_report(data: Any) -> List[Finding]:
    findings: List[Finding] = []
    if not data or not isinstance(data, list):
        return findings

    for item in data:
        if not isinstance(item, dict):
            continue

        rule_id = item.get("RuleID", "gitleaks-secret")
        desc = item.get("Description") or item.get("RuleID") or "Detected Secret Leak"
        file_path = normalize_file_path(item.get("File"))
        start_line = item.get("StartLine")
        try:
            line_num = int(start_line) if start_line is not None else None
        except (ValueError, TypeError):
            line_num = None

        secret_val = item.get("Secret", "")
        # Crucial security rule: NEVER expose raw secret
        masked_secret = f"{secret_val[:2]}****{secret_val[-2:]}" if len(secret_val) > 4 else "******"

        fingerprint = generate_secret_fingerprint(
            rule_id=rule_id,
            file_path=file_path,
            secret_value=secret_val
        )

        title = f"Secret Detected: {desc}"
        description = (
            f"Gitleaks detected a potential secret matching rule '{rule_id}' "
            f"in file '{file_path}'. Secret pattern matches: {masked_secret}"
        )

        f = Finding(
            fingerprint=fingerprint,
            scanner="gitleaks",
            category=Category.SECRET.value,
            severity=Severity.CRITICAL.value,  # Per policy: treat secrets as CRITICAL
            title=title,
            description=description,
            file=file_path,
            line=line_num,
            rule_id=rule_id,
            remediation="Immediately revoke and rotate the exposed credential. Remove all occurrences from git history.",
            url="https://github.com/gitleaks/gitleaks",
            status="OPEN",
            detected_by=["gitleaks"],
            metadata={
                "commit": item.get("Commit"),
                "author": item.get("Author"),
                "date": item.get("Date"),
                "entropy": item.get("Entropy"),
            }
        )
        findings.append(f)

    return findings
