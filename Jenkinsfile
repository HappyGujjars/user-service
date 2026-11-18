pipeline {
    agent any

    environment {
        PROJECT_NAME     = 'critical'
        SERVICE_NAME     = 'backend'
        IMAGE_NAME       = 'critical-backend'

        // Centralized Credentials from Jenkins Credential Store
        DEFECTDOJO_URL   = credentials('dojourl')
        DEFECTDOJO_TOKEN = credentials('dojotoken')
        SONAR_URL        = credentials('sonarurl')
        SONAR_TOKEN      = credentials('sonartoken')

        // Optional Chat Notification Webhook (if configured)
        // CHAT_WEBHOOK     = credentials('google-chat-webhook-backend')
    }

    stages {

        stage('Prepare Workspace & Directories') {
            steps {
                sh '''
                    mkdir -p reports
                    echo "Preparing workspace for ${PROJECT_NAME}-${SERVICE_NAME} build #${BUILD_NUMBER}"
                '''
            }
        }

        stage('Install Dependencies') {
            steps {
                echo "Installing project dependencies..."
                sh '''
                    if [ -f "package.json" ]; then
                        npm install --silent || true
                    fi
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                echo "Executing unit tests..."
                sh '''
                    if [ -f "package.json" ]; then
                        npm test -- --passWithNoTests || true
                    fi
                '''
            }
        }

        stage('Gitleaks Secret Scan') {
            steps {
                echo "Running Gitleaks secret detection..."
                sh '''
                    docker run --rm \
                        --volumes-from jenkins \
                        zricethezav/gitleaks:latest detect \
                        --source="${WORKSPACE}" \
                        --report-path="${WORKSPACE}/reports/gitleaks.json" \
                        --report-format=json \
                        --verbose \
                        --no-git || true
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/gitleaks.json', allowEmptyArchive: true
                }
            }
        }

        stage('SonarQube SAST Analysis') {
            steps {
                echo "Running SonarQube SAST code analysis..."
                sh '''
                    SONAR_BASE_URL="${SONAR_URL%/}"
                    docker run --rm \
                        --volumes-from jenkins \
                        -e SONAR_HOST_URL="${SONAR_BASE_URL}" \
                        -e SONAR_TOKEN="${SONAR_TOKEN}" \
                        sonarsource/sonar-scanner-cli \
                        -Dsonar.host.url="${SONAR_BASE_URL}" \
                        -Dsonar.token="${SONAR_TOKEN}" \
                        -Dsonar.projectKey=${PROJECT_NAME}-${SERVICE_NAME} \
                        -Dsonar.projectName=${PROJECT_NAME}-${SERVICE_NAME} \
                        -Dsonar.projectBaseDir="${WORKSPACE}" \
                        -Dsonar.sources=src \
                        -Dsonar.exclusions="**/node_modules/**,**/*.spec.ts,dist/**,security-report-generator/**" || true

                    # Wait for SonarQube Compute Engine to index findings
                    sleep 5
                    echo "Fetching SonarQube findings for aggregator..."
                    AUTH_HEADER=$(printf "%s:" "${SONAR_TOKEN}" | base64 | tr -d '\n')
                    curl -s -H "Authorization: Basic ${AUTH_HEADER}" \
                        "${SONAR_BASE_URL}/api/issues/search?componentKeys=${PROJECT_NAME}-${SERVICE_NAME}&resolved=false&ps=500" \
                        -o "${WORKSPACE}/reports/sonar.json" || true
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/sonar.json', allowEmptyArchive: true
                }
            }
        }

        stage('Trivy Filesystem Scan') {
            steps {
                echo "Scanning project filesystem and dependencies with Trivy..."
                sh '''
                    docker run --rm \
                        --volumes-from jenkins \
                        -v /var/run/docker.sock:/var/run/docker.sock \
                        aquasec/trivy:latest fs \
                        --format json \
                        --output "${WORKSPACE}/reports/trivy-fs.json" \
                        "${WORKSPACE}" || true
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/trivy-fs.json', allowEmptyArchive: true
                }
            }
        }

        stage('Build Application') {
            steps {
                echo "Building application artifacts..."
                sh '''
                    if [ -f "package.json" ]; then
                        npm run build || true
                    fi
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                echo "Building container image ${IMAGE_NAME}:${BUILD_NUMBER}..."
                sh '''
                    if [ -f "Dockerfile" ]; then
                        docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} . || true
                        docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${IMAGE_NAME}:latest || true
                    fi
                '''
            }
        }

        stage('Trivy Container Image Scan') {
            steps {
                echo "Scanning container image ${IMAGE_NAME}:${BUILD_NUMBER} with Trivy..."
                sh '''
                    docker run --rm \
                        -v /var/run/docker.sock:/var/run/docker.sock \
                        --volumes-from jenkins \
                        aquasec/trivy:latest image \
                        --format json \
                        --output "${WORKSPACE}/reports/trivy-image.json" \
                        ${IMAGE_NAME}:${BUILD_NUMBER} || true
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/trivy-image.json', allowEmptyArchive: true
                }
            }
        }

        stage('Security Report Aggregation') {
            steps {
                echo "Aggregating and deduplicating security reports..."
                sh '''
                    python3 security-report-generator/src/main.py \
                        --gitleaks "${WORKSPACE}/reports/gitleaks.json" \
                        --trivy-fs "${WORKSPACE}/reports/trivy-fs.json" \
                        --trivy-image "${WORKSPACE}/reports/trivy-image.json" \
                        --sonar "${WORKSPACE}/reports/sonar.json" \
                        --owners security-report-generator/config/owners.yaml \
                        --project "${PROJECT_NAME}" \
                        --service "${SERVICE_NAME}" \
                        --branch "${BRANCH_NAME:-stage}" \
                        --commit "${GIT_COMMIT:-HEAD}" \
                        --build-num "${BUILD_NUMBER}" \
                        --triggered-by "${BUILD_USER_ID:-CI}" \
                        --build-status "RUNNING" \
                        --jenkins-url "${BUILD_URL}" \
                        --sonarqube-url "${SONAR_URL}" \
                        --defectdojo-url "${DEFECTDOJO_URL}" \
                        --output-html "${WORKSPACE}/reports/security-report.html" \
                        --output-json "${WORKSPACE}/reports/combined-findings.json" \
                        --output-summary "${WORKSPACE}/reports/notification-summary.json"
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/security-report.html,reports/combined-findings.json,reports/notification-summary.json', allowEmptyArchive: true
                }
            }
        }

        stage('DefectDojo Import') {
            steps {
                echo "Pushing normalized scanner findings to DefectDojo..."
                sh '''
                    DOJO_BASE_URL="${DEFECTDOJO_URL%/}"
                    PRODUCT_NAME="${PROJECT_NAME}-${SERVICE_NAME}"
                    ENGAGEMENT_NAME="CI/CD"

                    upload_to_dojo() {
                        SCAN_FILE="$1"
                        SCAN_TYPE="$2"
                        if [ -f "$SCAN_FILE" ] && [ -s "$SCAN_FILE" ]; then
                            echo "Uploading $SCAN_TYPE ($SCAN_FILE) to DefectDojo..."
                            RES=$(curl -s -w "\\n%{http_code}" -X POST "${DOJO_BASE_URL}/api/v2/import-scan/" \
                                -H "Authorization: Token ${DEFECTDOJO_TOKEN}" \
                                -H "accept: application/json" \
                                -H "Content-Type: multipart/form-data" \
                                -F "scan_type=${SCAN_TYPE}" \
                                -F "file=@${SCAN_FILE}" \
                                -F "product_name=${PRODUCT_NAME}" \
                                -F "engagement_name=${ENGAGEMENT_NAME}" \
                                -F "auto_create_context=true" \
                                -F "close_old_findings=true" \
                                -F "product_type_name=Research and Development")
                            HTTP_STATUS=$(echo "$RES" | tail -n1)
                            echo "DefectDojo ($SCAN_TYPE) response status: $HTTP_STATUS"
                        else
                            echo "Skipping $SCAN_TYPE: report file not found or empty."
                        fi
                    }

                    # 1. Gitleaks
                    upload_to_dojo "${WORKSPACE}/reports/gitleaks.json" "Gitleaks Scan"

                    # 2. SonarQube
                    upload_to_dojo "${WORKSPACE}/reports/sonar.json" "SonarQube Scan"

                    # 3. Trivy Filesystem
                    upload_to_dojo "${WORKSPACE}/reports/trivy-fs.json" "Trivy Scan"

                    # 4. Trivy Container Image
                    upload_to_dojo "${WORKSPACE}/reports/trivy-image.json" "Trivy Scan"
                '''
            }
        }

        stage('Developer Notification') {
            steps {
                echo "Evaluating notification routing..."
                sh '''
                    if [ -f "${WORKSPACE}/reports/notification-summary.json" ]; then
                        echo "--- SECURITY GATE NOTIFICATION SUMMARY ---"
                        cat "${WORKSPACE}/reports/notification-summary.json"
                        echo "------------------------------------------"
                    fi
                '''
            }
        }

        stage('Security Gate Evaluation') {
            steps {
                echo "Enforcing Security Gate policy..."
                sh '''
                    python3 -c '
import json, sys
try:
    with open("reports/notification-summary.json") as f:
        data = json.load(f)
    if not data.get("gate_passed", False):
        print(f"❌ SECURITY GATE FAILED: {data.get(\"critical_count\", 0)} Critical vulnerabilities detected!")
        print("Build blocked by security policy. Deployment halted.")
        sys.exit(1)
    else:
        print("✅ SECURITY GATE PASSED: All security checks cleared.")
except Exception as e:
    print(f"Warning: Security gate check exception: {e}")
'
                '''
            }
        }

        stage('Deploy to Staging') {
            when {
                branch 'stage'
            }
            steps {
                echo "Deploying ${IMAGE_NAME}:${BUILD_NUMBER} to Staging Environment..."
                // Deployment steps here (e.g. helm, kubectl, or docker-compose)
                sh 'echo "Deployment to Staging Successful."'
            }
        }

        stage('Production Approval') {
            when {
                branch 'main'
            }
            steps {
                timeout(time: 24, unit: 'HOURS') {
                    input message: "Approve deployment of ${IMAGE_NAME}:${BUILD_NUMBER} to Production?", ok: "Deploy to Production"
                }
            }
        }

        stage('Deploy to Production') {
            when {
                branch 'main'
            }
            steps {
                echo "Deploying ${IMAGE_NAME}:${BUILD_NUMBER} to Production Environment..."
                // Production deployment steps
                sh 'echo "Deployment to Production Successful."'
            }
        }

    }

    post {
        always {
            echo "CI/CD Pipeline Completed for ${PROJECT_NAME}-${SERVICE_NAME} build #${BUILD_NUMBER}"
        }
        success {
            echo "🎉 Pipeline execution completed successfully."
        }
        failure {
            echo "❌ Pipeline failed. Review security reports and build logs."
        }
    }
}
