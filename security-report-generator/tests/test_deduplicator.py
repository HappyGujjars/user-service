import unittest
from src.models import Finding, Severity, Category
from src.deduplicator import deduplicate_findings


class TestDeduplicator(unittest.TestCase):
    def test_cross_scanner_secret_deduplication(self):
        f_gitleaks = Finding(
            fingerprint="fp1",
            scanner="gitleaks",
            category=Category.SECRET.value,
            severity=Severity.CRITICAL.value,
            title="AWS Access Key",
            description="Exposed AWS Token",
            file="src/config.ts",
            line=12,
            detected_by=["gitleaks"],
        )
        f_sonar = Finding(
            fingerprint="fp2",
            scanner="sonarqube",
            category=Category.SECRET.value,
            severity=Severity.HIGH.value,
            title="Hardcoded credential",
            description="Hardcoded secret detected",
            file="src/config.ts",
            line=12,
            detected_by=["sonarqube"],
        )
        f_trivy = Finding(
            fingerprint="fp3",
            scanner="trivy-fs",
            category=Category.SECRET.value,
            severity=Severity.CRITICAL.value,
            title="Secret detected",
            description="Found AWS secret token",
            file="src/config.ts",
            line=12,
            detected_by=["trivy-fs"],
        )

        deduped, stats = deduplicate_findings([f_gitleaks, f_sonar, f_trivy])
        self.assertEqual(len(deduped), 1)
        self.assertEqual(stats["total_raw"], 3)
        self.assertEqual(stats["total_unique"], 1)
        self.assertEqual(stats["duplicates_removed"], 2)

        merged = deduped[0]
        self.assertEqual(merged.severity, Severity.CRITICAL.value)
        self.assertIn("gitleaks", merged.detected_by)
        self.assertIn("sonarqube", merged.detected_by)
        self.assertIn("trivy-fs", merged.detected_by)
        self.assertEqual(merged.metadata["total_detections"], 3)

    def test_cross_scanner_dependency_deduplication(self):
        f_fs = Finding(
            fingerprint="fp_dep1",
            scanner="trivy-fs",
            category=Category.DEPENDENCY.value,
            severity=Severity.HIGH.value,
            title="Vulnerability in lodash",
            description="ReDoS",
            cve="CVE-2021-23337",
            package="lodash",
            installed_version="4.17.20",
            detected_by=["trivy-fs"],
        )
        f_image = Finding(
            fingerprint="fp_dep2",
            scanner="trivy-image",
            category=Category.DEPENDENCY.value,
            severity=Severity.HIGH.value,
            title="Vulnerability in lodash",
            description="ReDoS",
            cve="CVE-2021-23337",
            package="lodash",
            installed_version="4.17.20",
            detected_by=["trivy-image"],
        )

        deduped, stats = deduplicate_findings([f_fs, f_image])
        self.assertEqual(len(deduped), 1)
        self.assertEqual(stats["duplicates_removed"], 1)
        self.assertIn("trivy-fs", deduped[0].detected_by)
        self.assertIn("trivy-image", deduped[0].detected_by)


if __name__ == "__main__":
    unittest.main()
