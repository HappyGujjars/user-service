import unittest
from src.fingerprint import (
    generate_secret_fingerprint,
    generate_dependency_fingerprint,
    generate_sonar_fingerprint,
    generate_misconfig_fingerprint,
    normalize_file_path,
)


class TestFingerprints(unittest.TestCase):
    def test_normalize_file_path(self):
        self.assertEqual(normalize_file_path("./src/app.ts"), "src/app.ts")
        self.assertEqual(normalize_file_path("/var/jenkins_home/workspace/job/src/app.ts"), "src/app.ts")
        self.assertEqual(normalize_file_path("src\\app.ts"), "src/app.ts")

    def test_secret_fingerprint_stability(self):
        fp1 = generate_secret_fingerprint("aws-key", "src/config.ts", "AKIA1234567890EXAMPLE")
        fp2 = generate_secret_fingerprint("aws-key", "./src/config.ts", "AKIA1234567890EXAMPLE")
        self.assertEqual(fp1, fp2)
        self.assertTrue(fp1.startswith("sha256:"))
        # Ensure raw secret is not in the fingerprint
        self.assertNotIn("AKIA1234567890EXAMPLE", fp1)

    def test_dependency_fingerprint(self):
        fp1 = generate_dependency_fingerprint("CVE-2023-1234", "lodash", "4.17.20")
        fp2 = generate_dependency_fingerprint("cve-2023-1234", "LODASH", "4.17.20")
        self.assertEqual(fp1, fp2)

    def test_sonar_fingerprint(self):
        fp1 = generate_sonar_fingerprint("typescript:S2076", "src/app.service.ts", 15)
        fp2 = generate_sonar_fingerprint("typescript:S2076", "src/app.service.ts", 15)
        self.assertEqual(fp1, fp2)


if __name__ == "__main__":
    unittest.main()
