import unittest
from src.parsers.trivy import parse_trivy_report
from src.models import Severity, Category


class TestTrivyParser(unittest.TestCase):
    def test_parse_trivy_vulnerability(self):
        sample = {
            "ArtifactName": "package-lock.json",
            "Results": [
                {
                    "Target": "package-lock.json",
                    "Class": "lang-pkgs",
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2021-23337",
                            "PkgName": "lodash",
                            "InstalledVersion": "4.17.20",
                            "FixedVersion": "4.17.21",
                            "Severity": "HIGH",
                            "Title": "Command Injection in lodash",
                            "PrimaryURL": "https://avd.aquasec.com/nvd/cve-2021-23337",
                        }
                    ]
                }
            ]
        }
        findings = parse_trivy_report(sample, scan_context="trivy-fs")
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f.scanner, "trivy-fs")
        self.assertEqual(f.severity, Severity.HIGH.value)
        self.assertEqual(f.category, Category.DEPENDENCY.value)
        self.assertEqual(f.cve, "CVE-2021-23337")
        self.assertEqual(f.package, "lodash")
        self.assertEqual(f.installed_version, "4.17.20")
        self.assertEqual(f.fixed_version, "4.17.21")

    def test_parse_trivy_misconfig(self):
        sample = {
            "ArtifactName": "Dockerfile",
            "Results": [
                {
                    "Target": "Dockerfile",
                    "Class": "config",
                    "Misconfigurations": [
                        {
                            "ID": "DS002",
                            "Title": "Image user should not be root",
                            "Severity": "MEDIUM",
                            "Resolution": "Add USER nonroot to Dockerfile",
                        }
                    ]
                }
            ]
        }
        findings = parse_trivy_report(sample, scan_context="trivy-fs")
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f.category, Category.MISCONFIG.value)
        self.assertEqual(f.severity, Severity.MEDIUM.value)


if __name__ == "__main__":
    unittest.main()
