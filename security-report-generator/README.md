# Security Report Aggregator

A lightweight, scanner-independent Python application that aggregates, normalizes, deduplicates, and reports findings from **Gitleaks**, **SonarQube**, and **Trivy** in Jenkins CI/CD pipelines.

## 🚀 Key Features

- **Common Schema Normalization**: Converts diverse scanner formats into a unified `Finding` model.
- **Stable Fingerprints**: Category-specific SHA-256 fingerprints ensuring findings are tracked consistently across builds without storing raw secrets.
- **Build-Level Cross-Scanner Deduplication**: Merges duplicate detections from multiple scanners in the same build (e.g. Gitleaks + SonarQube + Trivy detecting the same secret).
- **Unified HTML Report**: Generates an interactive, responsive HTML report with severity breakdown and remediation details.
- **Service Ownership Routing**: Reads `config/owners.yaml` to route findings and emails to the correct service developers (Frontend vs Backend).
- **Security Policy Enforcement**: CLI flag `--enforce-gate` to block deployment when Critical vulnerabilities exist.

## 🛠️ Usage

```bash
python3 security-report-generator/src/main.py \
  --gitleaks reports/gitleaks.json \
  --trivy-fs reports/trivy-fs.json \
  --trivy-image reports/trivy-image.json \
  --sonar reports/sonar.json \
  --owners security-report-generator/config/owners.yaml \
  --project critical \
  --service backend \
  --branch "${GIT_BRANCH}" \
  --commit "${GIT_COMMIT}" \
  --build-num "${BUILD_NUMBER}" \
  --triggered-by "${BUILD_USER_ID}" \
  --build-status "PASSED" \
  --jenkins-url "${BUILD_URL}" \
  --sonarqube-url "${SONAR_URL}" \
  --defectdojo-url "${DEFECTDOJO_URL}" \
  --output-html reports/security-report.html \
  --output-json reports/combined-findings.json \
  --output-summary reports/notification-summary.json \
  --enforce-gate
```

## 🧪 Testing

Run test suite:
```bash
python3 -m unittest discover tests
```
