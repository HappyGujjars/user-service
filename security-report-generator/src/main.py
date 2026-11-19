#!/usr/bin/env python3
import argparse
import sys
import os
from datetime import datetime, timezone

# Ensure both current directory and parent directory are on sys.path for direct execution
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from .models import ReportMetadata
    from .utils.file_reader import (
        read_json_file,
        read_yaml_file,
        write_json_file,
        write_text_file,
    )
    from .utils.logger import setup_logger
    from .normalizer import normalize_all_scans
    from .report_generator import generate_html_report
    from .notification_summary import generate_notification_summary
    from .dojo_exporter import export_dojo_generic
except (ImportError, ValueError):
    from models import ReportMetadata
    from utils.file_reader import (
        read_json_file,
        read_yaml_file,
        write_json_file,
        write_text_file,
    )
    from utils.logger import setup_logger
    from normalizer import normalize_all_scans
    from report_generator import generate_html_report
    from notification_summary import generate_notification_summary
    from dojo_exporter import export_dojo_generic


def parse_args():
    parser = argparse.ArgumentParser(
        description="Unified DevSecOps Security Report Aggregator & Normalizer"
    )
    # Scanners input paths
    parser.add_argument("--gitleaks", help="Path to Gitleaks JSON report")
    parser.add_argument("--trivy-fs", help="Path to Trivy filesystem JSON report")
    parser.add_argument("--trivy-image", help="Path to Trivy container image JSON report")
    parser.add_argument("--sonar", help="Path to SonarQube issues JSON report")
    
    # Metadata
    parser.add_argument("--project", default="critical", help="Project identifier (default: critical)")
    parser.add_argument("--service", default="backend", choices=["frontend", "backend"], help="Service name")
    parser.add_argument("--branch", default="main", help="Git branch")
    parser.add_argument("--commit", default="HEAD", help="Git commit SHA")
    parser.add_argument("--build-num", default="1", help="Jenkins build number")
    parser.add_argument("--triggered-by", default="CI", help="Triggering developer or branch event")
    parser.add_argument("--build-status", default="PASSED", help="Current build status (PASSED/FAILED)")
    
    # Links
    parser.add_argument("--jenkins-url", help="Jenkins Build URL")
    parser.add_argument("--sonarqube-url", help="SonarQube Dashboard URL")
    parser.add_argument("--defectdojo-url", help="DefectDojo URL")
    
    # Config
    parser.add_argument("--owners", help="Path to owners.yaml configuration")

    # Outputs
    parser.add_argument("--output-html", default="reports/security-report.html", help="Destination path for HTML report")
    parser.add_argument("--output-json", default="reports/combined-findings.json", help="Destination path for combined findings JSON")
    parser.add_argument("--output-summary", default="reports/notification-summary.json", help="Destination path for notification summary JSON")
    
    # Policy Gate
    parser.add_argument("--enforce-gate", action="store_true", help="Exit with code 1 if Critical findings exist")

    return parser.parse_args()


def main():
    logger = setup_logger()
    args = parse_args()

    logger.info("Initializing Security Report Aggregator...")
    logger.info(f"Target: Project={args.project}, Service={args.service}, Build=#{args.build_num}")

    # Read scan reports safely
    gitleaks_data = read_json_file(args.gitleaks) if args.gitleaks else None
    trivy_fs_data = read_json_file(args.trivy_fs) if args.trivy_fs else None
    trivy_image_data = read_json_file(args.trivy_image) if args.trivy_image else None
    sonar_data = read_json_file(args.sonar) if args.sonar else None

    owners_config = read_yaml_file(args.owners) if args.owners else None

    # Construct metadata
    meta = ReportMetadata(
        project=args.project,
        service=args.service,
        branch=args.branch,
        commit=args.commit,
        build_num=str(args.build_num),
        triggered_by=args.triggered_by,
        build_status=args.build_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        jenkins_url=args.jenkins_url,
        sonarqube_url=args.sonarqube_url,
        defectdojo_url=args.defectdojo_url,
    )

    # Normalize and deduplicate findings across scanners
    aggregated_report = normalize_all_scans(
        gitleaks_data=gitleaks_data,
        trivy_fs_data=trivy_fs_data,
        trivy_image_data=trivy_image_data,
        sonar_data=sonar_data,
        metadata=meta,
        sonarqube_base_url=args.sonarqube_url,
    )

    # Generate Notification Summary
    notification_data = generate_notification_summary(
        report=aggregated_report,
        owners_config=owners_config,
        service_name=args.service,
    )

    # Render HTML Report
    html_report_str = generate_html_report(aggregated_report)

    # Export DefectDojo Generic Findings Import format (deduplicated, normalized)
    dojo_generic = export_dojo_generic(aggregated_report)

    # Write Outputs
    write_text_file(args.output_html, html_report_str)
    write_json_file(args.output_json, aggregated_report.to_dict())
    write_json_file(args.output_summary, notification_data)

    # Write DefectDojo aggregated export
    summary_dir = os.path.dirname(os.path.abspath(args.output_summary))
    dojo_export_path = os.path.join(summary_dir, "dojo-generic.json")
    write_json_file(dojo_export_path, dojo_generic)

    # Write separate chat payload and email body for pipeline integrations
    if "chat_payload" in notification_data:
        write_json_file(os.path.join(summary_dir, "chat-payload.json"), notification_data["chat_payload"])
    if "email_body" in notification_data:
        write_text_file(os.path.join(summary_dir, "email-body.txt"), notification_data["email_body"])

    logger.info(f"Generated unified HTML report at: {args.output_html}")
    logger.info(f"Generated combined JSON report at: {args.output_json}")
    logger.info(f"Generated DefectDojo Generic export at: {dojo_export_path}")
    logger.info(f"Generated notification summary at: {args.output_summary}")
    logger.info(f"Generated chat payload at: {os.path.join(summary_dir, 'chat-payload.json')}")

    summary = aggregated_report.summary
    logger.info("=" * 60)
    logger.info("SECURITY GATE SUMMARY:")
    logger.info(f"  Critical: {summary.get('CRITICAL', 0)}")
    logger.info(f"  High:     {summary.get('HIGH', 0)}")
    logger.info(f"  Medium:   {summary.get('MEDIUM', 0)}")
    logger.info(f"  Low:      {summary.get('LOW', 0)}")
    logger.info(f"  Unique:   {len(aggregated_report.findings)}")
    logger.info(f"  Merged:   {aggregated_report.deduplication_summary.get('duplicates_removed', 0)}")
    logger.info(f"  Gate:     {notification_data['gate_status']}")
    logger.info("=" * 60)

    # Check policy gate enforcement
    if args.enforce_gate:
        if not notification_data["gate_passed"]:
            logger.error("❌ Security Gate Failed: Critical vulnerabilities detected or build failed!")
            sys.exit(1)

    logger.info("Security Report Aggregator completed successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()
