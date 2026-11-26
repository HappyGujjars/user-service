import html
import os
from typing import Dict, Any, List
try:
    from .models import AggregatedReport, Severity, Finding
    from .severity import group_findings_by_severity
except (ImportError, ValueError):
    from models import AggregatedReport, Severity, Finding
    from severity import group_findings_by_severity


def render_finding_card(f: Finding) -> str:
    sev = Severity.normalize(f.severity).value
    sev_colors = {
        Severity.CRITICAL.value: ("#ef4444", "#fee2e2", "#991b1b"),
        Severity.HIGH.value: ("#f97316", "#ffedd5", "#9a3412"),
        Severity.MEDIUM.value: ("#eab308", "#fef9c3", "#854d0e"),
        Severity.LOW.value: ("#3b82f6", "#dbeafe", "#1e40af"),
        Severity.INFO.value: ("#6b7280", "#f3f4f6", "#374151"),
    }
    border_col, bg_col, text_col = sev_colors.get(sev, ("#6b7280", "#f3f4f6", "#374151"))

    scanners_badges = "".join(
        f'<span class="badge scanner-badge">{html.escape(s)}</span>'
        for s in f.detected_by
    )

    location_info = ""
    if f.file:
        loc_str = f"{f.file}:{f.line}" if f.line is not None else f.file
        location_info = f'<div class="finding-row"><span class="label">Location:</span> <code>{html.escape(loc_str)}</code></div>'

    pkg_info = ""
    if f.package:
        ver_str = f"{f.package} (installed: {f.installed_version or 'unknown'})"
        if f.fixed_version:
            ver_str += f' ➔ <span class="fixed-ver">fixed in: {f.fixed_version}</span>'
        pkg_info = f'<div class="finding-row"><span class="label">Package:</span> {html.escape(ver_str)}</div>'

    rule_info = ""
    if f.rule_id:
        cve_tag = f" ({f.cve})" if f.cve and f.cve != f.rule_id else ""
        rule_info = f'<div class="finding-row"><span class="label">Rule/CVE:</span> <code>{html.escape(f.rule_id + cve_tag)}</code></div>'

    remediation_info = ""
    if f.remediation:
        remediation_info = f'<div class="finding-remediation"><strong>Remediation:</strong> {html.escape(f.remediation)}</div>'

    ref_link = ""
    if f.url:
        ref_link = f'<div class="finding-row"><span class="label">Reference:</span> <a href="{html.escape(f.url)}" target="_blank" rel="noopener">Advisory Link ↗</a></div>'

    detections_count = f.metadata.get("total_detections", 1)
    dedup_badge = ""
    if detections_count > 1:
        dedup_badge = f'<span class="badge dedup-badge">Merged {detections_count} scanner detections</span>'

    return f"""
    <div class="finding-card" style="border-left: 5px solid {border_col};">
        <div class="finding-header">
            <span class="badge sev-badge" style="background-color: {bg_col}; color: {text_col}; border: 1px solid {border_col};">{sev}</span>
            <span class="finding-category">{html.escape(f.category.upper())}</span>
            {scanners_badges}
            {dedup_badge}
        </div>
        <h4 class="finding-title">{html.escape(f.title)}</h4>
        <p class="finding-desc">{html.escape(f.description)}</p>
        <div class="finding-details">
            {location_info}
            {pkg_info}
            {rule_info}
            {ref_link}
        </div>
        {remediation_info}
    </div>
    """


def generate_html_report(report: AggregatedReport) -> str:
    meta = report.metadata
    summary = report.summary
    grouped = group_findings_by_severity(report.findings)

    crit_count = summary.get(Severity.CRITICAL.value, 0)
    high_count = summary.get(Severity.HIGH.value, 0)
    med_count = summary.get(Severity.MEDIUM.value, 0)
    low_count = summary.get(Severity.LOW.value, 0)
    total_unique = len(report.findings)

    status_class = "status-failed" if (crit_count > 0 or meta.build_status.upper() in ("FAILED", "FAILURE")) else "status-passed"
    status_label = "FAILED (Security Gate Triggered)" if crit_count > 0 else meta.build_status

    # Render finding groups
    crit_cards = "".join(render_finding_card(f) for f in grouped.get(Severity.CRITICAL.value, [])) or '<div class="empty-state">✅ No Critical findings detected.</div>'
    high_cards = "".join(render_finding_card(f) for f in grouped.get(Severity.HIGH.value, [])) or '<div class="empty-state">✅ No High findings detected.</div>'
    med_cards = "".join(render_finding_card(f) for f in grouped.get(Severity.MEDIUM.value, [])) or '<div class="empty-state">No Medium findings detected.</div>'
    low_cards = "".join(render_finding_card(f) for f in grouped.get(Severity.LOW.value, [])) or '<div class="empty-state">No Low findings detected.</div>'

    # Scanner summary list
    scanner_items = "".join(
        f'<li><strong>{html.escape(scanner)}:</strong> {count} findings</li>'
        for scanner, count in report.scanner_summary.items()
    ) or '<li>No scanners reported findings</li>'

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Scan Report - {html.escape(meta.project)} ({html.escape(meta.service)})</title>
    <style>
        :root {{
            --bg: #f8fafc;
            --surface: #ffffff;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --primary: #3b82f6;
            --danger: #ef4444;
            --warning: #f59e0b;
            --success: #10b981;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            padding: 24px;
            line-height: 1.5;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            background: var(--surface);
            padding: 24px 32px;
            border-radius: 12px;
            border: 1px solid var(--border);
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .header-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            padding-bottom: 16px;
            margin-bottom: 16px;
        }}
        .header-title h1 {{ font-size: 24px; font-weight: 700; }}
        .header-title p {{ color: var(--text-muted); font-size: 14px; margin-top: 4px; }}
        .status-badge {{
            padding: 6px 16px;
            border-radius: 9999px;
            font-weight: 700;
            font-size: 14px;
            text-transform: uppercase;
        }}
        .status-passed {{ background: #d1fae5; color: #065f46; border: 1px solid #10b981; }}
        .status-failed {{ background: #fee2e2; color: #991b1b; border: 1px solid #ef4444; }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            font-size: 14px;
        }}
        .meta-item strong {{ color: var(--text-muted); display: block; font-size: 12px; text-transform: uppercase; }}
        
        /* Stats Cards */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: var(--surface);
            padding: 20px;
            border-radius: 12px;
            border: 1px solid var(--border);
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .stat-card .num {{ font-size: 32px; font-weight: 800; line-height: 1; margin-bottom: 8px; }}
        .stat-card .label {{ font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }}
        .stat-crit {{ color: #dc2626; }}
        .stat-high {{ color: #ea580c; }}
        .stat-med {{ color: #d97706; }}
        .stat-low {{ color: #2563eb; }}
        .stat-total {{ color: #0f172a; }}

        /* Section layout */
        .section-box {{
            background: var(--surface);
            border-radius: 12px;
            border: 1px solid var(--border);
            padding: 24px 32px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .section-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid var(--border);
        }}
        .section-title {{ font-size: 18px; font-weight: 700; }}
        
        /* Finding Cards */
        .finding-card {{
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 16px;
        }}
        .finding-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }}
        .finding-title {{ font-size: 16px; font-weight: 600; color: #1e293b; margin-bottom: 6px; }}
        .finding-desc {{ font-size: 14px; color: #475569; margin-bottom: 12px; }}
        .finding-details {{ font-size: 13px; display: grid; gap: 4px; }}
        .finding-row {{ display: flex; gap: 8px; }}
        .finding-row .label {{ font-weight: 600; color: #64748b; min-width: 80px; }}
        .finding-remediation {{
            margin-top: 12px;
            padding: 8px 12px;
            background: #f1f5f9;
            border-radius: 6px;
            font-size: 13px;
            color: #1e293b;
        }}
        .badge {{
            font-size: 11px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
        }}
        .scanner-badge {{ background: #e0e7ff; color: #3730a3; }}
        .dedup-badge {{ background: #fef3c7; color: #92400e; }}
        .finding-category {{ font-size: 12px; font-weight: 600; color: #64748b; }}
        .fixed-ver {{ color: #15803d; font-weight: 600; }}
        .empty-state {{ padding: 24px; text-align: center; color: #64748b; font-size: 14px; }}
        code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 12px; }}
        a {{ color: #2563eb; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        
        .links-grid {{ display: flex; gap: 16px; flex-wrap: wrap; margin-top: 12px; }}
        .btn-link {{
            display: inline-block;
            padding: 8px 16px;
            background: #0f172a;
            color: #ffffff !important;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="header-top">
                <div class="header-title">
                    <h1>Security Intelligence & Compliance Report</h1>
                    <p>Project: <strong>{html.escape(meta.project)}</strong> | Service: <strong>{html.escape(meta.service.upper())}</strong></p>
                </div>
                <div>
                    <span class="status-badge {status_class}">{status_label}</span>
                </div>
            </div>
            <div class="meta-grid">
                <div class="meta-item"><strong>Branch</strong> {html.escape(meta.branch)}</div>
                <div class="meta-item"><strong>Commit</strong> <code>{html.escape(meta.commit[:8] if meta.commit else 'N/A')}</code></div>
                <div class="meta-item"><strong>Build Number</strong> #{html.escape(str(meta.build_num))}</div>
                <div class="meta-item"><strong>Triggered By</strong> {html.escape(meta.triggered_by)}</div>
            </div>
        </div>

        <!-- Summary Statistics -->
        <div class="stats-grid">
            <div class="stat-card stat-crit"><div class="num">{crit_count}</div><div class="label">Critical</div></div>
            <div class="stat-card stat-high"><div class="num">{high_count}</div><div class="label">High</div></div>
            <div class="stat-card stat-med"><div class="num">{med_count}</div><div class="label">Medium</div></div>
            <div class="stat-card stat-low"><div class="num">{low_count}</div><div class="label">Low</div></div>
            <div class="stat-card stat-total"><div class="num">{total_unique}</div><div class="label">Unique Findings</div></div>
        </div>

        <!-- Critical Findings -->
        <div class="section-box">
            <div class="section-header">
                <span class="section-title">🚨 Critical Findings ({crit_count})</span>
            </div>
            {crit_cards}
        </div>

        <!-- High Findings -->
        <div class="section-box">
            <div class="section-header">
                <span class="section-title">⚠️ High Severity Findings ({high_count})</span>
            </div>
            {high_cards}
        </div>

        <!-- Medium Findings -->
        <div class="section-box">
            <div class="section-header">
                <span class="section-title">Medium Severity Findings ({med_count})</span>
            </div>
            {med_cards}
        </div>

        <!-- Low Findings -->
        <div class="section-box">
            <div class="section-header">
                <span class="section-title">Low & Informational Findings ({low_count})</span>
            </div>
            {low_cards}
        </div>

        <!-- Deduplication and Scanners Summary -->
        <div class="section-box">
            <div class="section-header">
                <span class="section-title">Scanner & Deduplication Summary</span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
                <div>
                    <h5 style="margin-bottom: 8px;">Deduplication Metrics</h5>
                    <p>Total Raw Detections: <strong>{report.deduplication_summary.get('total_raw', total_unique)}</strong></p>
                    <p>Unique Normalized Findings: <strong>{total_unique}</strong></p>
                    <p>Cross-Scanner Duplicates Removed: <strong>{report.deduplication_summary.get('duplicates_removed', 0)}</strong></p>
                </div>
                <div>
                    <h5 style="margin-bottom: 8px;">Detections by Scanner</h5>
                    <ul style="padding-left: 20px;">
                        {scanner_items}
                    </ul>
                </div>
            </div>
        </div>

        <!-- Quick Links -->
        <div class="section-box">
            <div class="section-header">
                <span class="section-title">Platform & Evidence Links</span>
            </div>
            <div class="links-grid">
                {f'<a class="btn-link" href="{html.escape(meta.jenkins_url)}" target="_blank">Jenkins Build</a>' if meta.jenkins_url else ''}
                {f'<a class="btn-link" href="{html.escape(meta.sonarqube_url)}" target="_blank">SonarQube Dashboard</a>' if meta.sonarqube_url else ''}
                {f'<a class="btn-link" href="{html.escape(meta.defectdojo_url)}" target="_blank">DefectDojo Vulnerabilities</a>' if meta.defectdojo_url else ''}
            </div>
        </div>
    </div>
</body>
</html>
"""
    return html_content
