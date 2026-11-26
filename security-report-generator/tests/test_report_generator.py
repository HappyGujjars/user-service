import unittest
from src.models import Finding, ReportMetadata, AggregatedReport, Severity, Category
from src.report_generator import generate_html_report
from src.notification_summary import generate_notification_summary


class TestReportGenerator(unittest.TestCase):
    def setUp(self):
        self.meta = ReportMetadata(
            project="critical",
            service="backend",
            branch="feature/payment",
            commit="a8f92c1",
            build_num="184",
            triggered_by="backendDevA",
            build_status="PASSED",
        )
        self.f1 = Finding(
            fingerprint="fp1",
            scanner="gitleaks",
            category=Category.SECRET.value,
            severity=Severity.CRITICAL.value,
            title="Hardcoded AWS Credential",
            description="Found AWS Token",
            file="src/config.ts",
            line=12,
            detected_by=["gitleaks", "sonarqube", "trivy"],
        )
        self.f2 = Finding(
            fingerprint="fp2",
            scanner="trivy",
            category=Category.DEPENDENCY.value,
            severity=Severity.HIGH.value,
            title="Vulnerable Dependency: lodash",
            description="ReDoS vulnerability",
            file="package-lock.json",
            cve="CVE-2021-23337",
            package="lodash",
            installed_version="4.17.20",
            fixed_version="4.17.21",
            detected_by=["trivy"],
        )
        self.report = AggregatedReport(
            metadata=self.meta,
            findings=[self.f1, self.f2],
            summary={Severity.CRITICAL.value: 1, Severity.HIGH.value: 1},
            scanner_summary={"gitleaks": 1, "sonarqube": 1, "trivy": 2},
            deduplication_summary={"total_raw": 4, "total_unique": 2, "duplicates_removed": 2},
        )

    def test_generate_html_report(self):
        html_out = generate_html_report(self.report)
        self.assertIn("critical", html_out)
        self.assertIn("feature/payment", html_out)
        self.assertIn("Hardcoded AWS Credential", html_out)
        self.assertIn("lodash", html_out)
        self.assertIn("CRITICAL", html_out)
        self.assertIn("HIGH", html_out)

    def test_notification_summary(self):
        owners = {
            "services": {
                "backend": {
                    "developers": ["backendDevA", "backendDevB"],
                    "email": ["backendDevA@company.com"],
                    "chat": "backend-team-chat",
                }
            },
            "escalation": {
                "email": ["security-lead@company.com"]
            }
        }
        notif = generate_notification_summary(self.report, owners_config=owners, service_name="backend")
        self.assertEqual(notif["critical_count"], 1)
        self.assertEqual(notif["gate_status"], "FAILED")
        self.assertIn("backendDevA@company.com", notif["recipients_email"])
        self.assertIn("security-lead@company.com", notif["recipients_email"])
        self.assertIn("[CRITICAL FAILED]", notif["email_subject"])


if __name__ == "__main__":
    unittest.main()
