import unittest
from src.parsers.sonar import parse_sonar_report
from src.models import Severity, Category


class TestSonarParser(unittest.TestCase):
    def test_parse_sonar_vulnerabilities(self):
        sample = {
            "total": 1,
            "issues": [
                {
                    "key": "AY12345",
                    "rule": "typescript:S2076",
                    "severity": "CRITICAL",
                    "component": "vulnerability:src/app.service.ts",
                    "project": "vulnerability",
                    "line": 15,
                    "message": "OS commands should not be vulnerable to command injection",
                    "type": "VULNERABILITY",
                    "status": "OPEN",
                }
            ]
        }
        findings = parse_sonar_report(sample, sonarqube_base_url="http://localhost:9000")
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f.scanner, "sonarqube")
        self.assertEqual(f.severity, Severity.CRITICAL.value)
        self.assertEqual(f.category, Category.CODE.value)
        self.assertEqual(f.file, "src/app.service.ts")
        self.assertEqual(f.line, 15)
        self.assertEqual(f.rule_id, "typescript:S2076")
        self.assertIn("http://localhost:9000", f.url)


if __name__ == "__main__":
    unittest.main()
