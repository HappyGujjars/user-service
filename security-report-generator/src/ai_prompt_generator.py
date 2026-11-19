"""
ai_prompt_generator.py

Generates an AI-optimized markdown prompt (ai-fix-prompt.md) designed for
direct consumption by LLMs and AI coding assistants (Cursor, GitHub Copilot,
Claude Code, Gemini CLI, ChatGPT).

It organizes findings by file and severity, providing exact line references,
CWE descriptions, and targeted fix instructions.
"""

from typing import List, Dict, Any
from collections import defaultdict

try:
    from .models import AggregatedReport, Severity, Finding
except (ImportError, ValueError):
    from models import AggregatedReport, Severity, Finding


def generate_ai_prompt(report: AggregatedReport) -> str:
    """
    Produce a complete, self-contained Markdown prompt that an engineer can
    copy-paste directly into an AI coding assistant to auto-remediate findings.
    """
    meta = report.metadata
    summary = report.summary
    total_findings = len(report.findings)

    # Group findings by file path
    findings_by_file: Dict[str, List[Finding]] = defaultdict(list)
    general_findings: List[Finding] = []

    for f in report.findings:
        if f.file:
            findings_by_file[f.file].append(f)
        else:
            general_findings.append(f)

    # Sort files by highest severity finding first
    def file_max_rank(file_findings: List[Finding]) -> int:
        return max(Severity.normalize(f.severity).rank for f in file_findings)

    sorted_files = sorted(
        findings_by_file.keys(),
        key=lambda fp: file_max_rank(findings_by_file[fp]),
        reverse=True
    )

    md = []
    md.append(f"# 🛡️ AI Security Remediation Request — {meta.project.upper()} ({meta.service})")
    md.append("")
    md.append("## 1. Context & Metadata")
    md.append(f"- **Project**: `{meta.project}`")
    md.append(f"- **Service**: `{meta.service}`")
    md.append(f"- **Branch**: `{meta.branch}`")
    md.append(f"- **Build**: `#{meta.build_num}`")
    md.append(f"- **Total Security Issues Detected**: `{total_findings}`")
    md.append(f"  - 🔴 Critical: `{summary.get('CRITICAL', 0)}`")
    md.append(f"  - 🟠 High:     `{summary.get('HIGH', 0)}`")
    md.append(f"  - 🟡 Medium:   `{summary.get('MEDIUM', 0)}`")
    md.append(f"  - ⚪ Low:      `{summary.get('LOW', 0)}`")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 2. Instructions for AI Assistant")
    md.append("You are acting as a Senior Security Engineer and Full-Stack Developer.")
    md.append("Please perform the following tasks:")
    md.append("1. **Analyze** each reported vulnerability and explain why the existing code is flawed.")
    md.append("2. **Provide the exact secure replacement code** for the affected functions or dependency declarations.")
    md.append("3. **Ensure Zero Regressions**: The replacement code must strictly preserve the business logic, function signatures, and TypeScript types.")
    md.append("4. **Follow Best Practices**: Use industry-standard libraries (e.g. `crypto`, modern ES6 APIs, parameterized queries, bcrypt/argon2 where appropriate).")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 3. Vulnerability Breakdown by File")
    md.append("")

    item_idx = 1
    for file_path in sorted_files:
        file_items = findings_by_file[file_path]
        # Sort items inside file: Critical -> High -> Medium -> Low
        file_items.sort(key=lambda x: Severity.normalize(x.severity).rank, reverse=True)

        md.append(f"### 📁 File: `{file_path}` ({len(file_items)} findings)")
        md.append("")

        for f in file_items:
            sev_badge = f"[{f.severity}]"
            loc = f"Line {f.line}" if f.line is not None else "General"
            scanners = ", ".join(f.detected_by) if f.detected_by else f.scanner

            md.append(f"#### #{item_idx}. {sev_badge} {f.title}")
            md.append(f"- **Location**: `{file_path}:{f.line or 1}` ({loc})")
            md.append(f"- **Category**: `{f.category.upper()}`")
            md.append(f"- **Scanners**: `{scanners}`")
            if f.rule_id:
                md.append(f"- **Rule ID / CWE**: `{f.rule_id}`")
            if f.cve:
                md.append(f"- **CVE Reference**: `{f.cve}`")
            md.append(f"- **Description**: {f.description}")
            if f.remediation:
                md.append(f"- **Recommended Fix**: {f.remediation}")
            md.append("")
            item_idx += 1

        md.append("---")
        md.append("")

    # General / Infrastructure / Package findings (e.g. Trivy image CVEs)
    if general_findings:
        md.append(f"### 📦 Container & Dependency Findings ({len(general_findings)} findings)")
        md.append("")
        for f in general_findings:
            sev_badge = f"[{f.severity}]"
            md.append(f"#### #{item_idx}. {sev_badge} {f.title}")
            if f.package:
                ver_info = f"Package `{f.package}` (installed: `{f.installed_version or 'unknown'}`"
                if f.fixed_version:
                    ver_info += f" -> fixed in: `{f.fixed_version}`)"
                else:
                    ver_info += ")"
                md.append(f"- **Package Details**: {ver_info}")
            if f.cve:
                md.append(f"- **CVE**: `{f.cve}`")
            md.append(f"- **Description**: {f.description}")
            if f.remediation:
                md.append(f"- **Recommended Fix**: {f.remediation}")
            md.append("")
            item_idx += 1

    md.append("## 4. Expected Output Format")
    md.append("Please output the fixes file-by-file with a clear before/after diff or full updated functions ready to be applied.")
    md.append("")

    return "\n".join(md)
