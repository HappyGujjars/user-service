import unittest
from src.parsers.gitleaks import parse_gitleaks_report
from src.models import Severity, Category


class TestGitleaksParser(unittest.TestCase):
    def test_parse_valid_gitleaks(self):
        sample = [
            {
                "Description": "AWS Access Key",
                "StartLine": 12,
                "File": "src/config.ts",
                "Secret": "AKIAIOSFODNN7EXAMPLE",
                "RuleID": "aws-access-token",
                "Commit": "abc1234",
                "Author": "dev",
            }
        ]
        findings = parse_gitleaks_report(sample)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f.scanner, "gitleaks")
        self.assertEqual(f.severity, Severity.CRITICAL.value)
        self.assertEqual(f.category, Category.SECRET.value)
        self.assertEqual(f.file, "src/config.ts")
        self.assertEqual(f.line, 12)
        # Verify raw secret is never included in title or description
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", f.description)
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", f.title)

    def test_parse_empty_gitleaks(self):
        findings = parse_gitleaks_report([])
        self.assertEqual(len(findings), 0)


if __name__ == "__main__":
    unittest.main()
