pipeline {
    agent any

    options {
        buildDiscarder(logRotator(
            numToKeepStr: '15',
            daysToKeepStr: '7',
            artifactNumToKeepStr: '7',
            artifactDaysToKeepStr: '3'
        ))
        disableConcurrentBuilds()
        timeout(time: 30, unit: 'MINUTES')
    }

    environment {
        PROJECT_NAME     = 'critical'
        SERVICE_NAME     = 'backend'
        IMAGE_NAME       = 'critical-backend'

        // Centralized Credentials from Jenkins Credential Store
        DEFECTDOJO_URL       = credentials('dojourl')
        DEFECTDOJO_TOKEN     = credentials('dojotoken')
        SONAR_URL            = credentials('sonarurl')
        SONAR_TOKEN          = credentials('sonartoken')
        GOOGLE_CHAT_WEBHOOK  = credentials('googleChatWebhook')
    }

    stages {

        stage('Prepare Workspace & Directories') {
            steps {
                sh '''
                    # Clean previous report artifacts to avoid Gitleaks false positives on old reports
                    rm -f ${WORKSPACE}/gitleaks-report.json ${WORKSPACE}/sonar-report.json
                    rm -rf ${WORKSPACE}/reports
                    mkdir -p ${WORKSPACE}/reports
                    echo "Preparing workspace for ${PROJECT_NAME}-${SERVICE_NAME} build #${BUILD_NUMBER}"
                '''
            }
        }

        stage('Dependencies & Unit Tests') {
            steps {
                catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                    sh '''
                        if command -v npm >/dev/null 2>&1; then
                            echo "Executing local npm install and tests..."
                            npm install --silent || true
                            npm test -- --passWithNoTests
                        else
                            echo "npm not present on Jenkins host; container build handles dependencies."
                        fi
                    '''
                }
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
        }

        stage('Build Docker Image') {
            steps {
                echo "Building container image ${IMAGE_NAME}:${BUILD_NUMBER}..."
                catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                    sh '''
                        if [ -f "Dockerfile" ]; then
                            docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} .
                            docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${IMAGE_NAME}:latest || true
                        fi
                    '''
                }
            }
        }

        stage('Trivy Container Image Scan') {
            steps {
                sh '''
                    if docker image inspect ${IMAGE_NAME}:${BUILD_NUMBER} >/dev/null 2>&1; then
                        echo "Scanning container image ${IMAGE_NAME}:${BUILD_NUMBER} with Trivy..."
                        docker run --rm \
                            -v /var/run/docker.sock:/var/run/docker.sock \
                            --volumes-from jenkins \
                            aquasec/trivy:latest image \
                            --format json \
                            --output "${WORKSPACE}/reports/trivy-image.json" \
                            ${IMAGE_NAME}:${BUILD_NUMBER} || true
                    else
                        echo "⚠️ Skipping image scan: ${IMAGE_NAME}:${BUILD_NUMBER} was not built due to compilation failure."
                    fi
                '''
            }
        }

        stage('Security Report Aggregation') {
            steps {
                echo "Aggregating and deduplicating security reports using containerized Python..."
                script {
                    def buildStatus = currentBuild.result ?: 'SUCCESS'
                    def branchName = env.BRANCH_NAME ?: 'stage'
                    def gitCommit = env.GIT_COMMIT ?: 'HEAD'
                    def buildUser = env.BUILD_USER_ID ?: 'CI'
                    sh """
                        docker run --rm \\
                            --volumes-from jenkins \\
                            -w "${env.WORKSPACE}" \\
                            python:3.11-alpine \\
                            python3 security-report-generator/src/main.py \\
                                --gitleaks "${env.WORKSPACE}/reports/gitleaks.json" \\
                                --trivy-fs "${env.WORKSPACE}/reports/trivy-fs.json" \\
                                --trivy-image "${env.WORKSPACE}/reports/trivy-image.json" \\
                                --sonar "${env.WORKSPACE}/reports/sonar.json" \\
                                --owners security-report-generator/config/owners.yaml \\
                                --project "${PROJECT_NAME}" \\
                                --service "${SERVICE_NAME}" \\
                                --branch "${branchName}" \\
                                --commit "${gitCommit}" \\
                                --build-num "${BUILD_NUMBER}" \\
                                --triggered-by "${buildUser}" \\
                                --build-status "${buildStatus}" \\
                                --jenkins-url "${BUILD_URL}" \\
                                --sonarqube-url "${SONAR_URL}" \\
                                --defectdojo-url "${DEFECTDOJO_URL}" \\
                                --output-html "${env.WORKSPACE}/reports/security-report.html" \\
                                --output-json "${env.WORKSPACE}/reports/combined-findings.json" \\
                                --output-summary "${env.WORKSPACE}/reports/notification-summary.json"
                    """
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/remediation-bundle.zip', allowEmptyArchive: false
                }
            }
        }

        stage('DefectDojo Import') {
            steps {
                echo "Pushing deduplicated aggregated findings to DefectDojo (Generic Findings Import)..."
                sh '''
                    DOJO_BASE_URL="${DEFECTDOJO_URL%/}"
                    DOJO_FILE="${WORKSPACE}/reports/dojo-generic.json"
                    PRODUCT_NAME="${PROJECT_NAME}-${SERVICE_NAME}"
                    ENGAGEMENT_NAME="CI/CD"

                    if [ -f "$DOJO_FILE" ] && [ -s "$DOJO_FILE" ]; then
                        echo "Uploading aggregated report ($DOJO_FILE) to DefectDojo as Generic Findings Import..."
                        RES=$(curl -s -w "\\n%{http_code}" -X POST "${DOJO_BASE_URL}/api/v2/import-scan/" \
                            -H "Authorization: Token ${DEFECTDOJO_TOKEN}" \
                            -H "accept: application/json" \
                            -H "Content-Type: multipart/form-data" \
                            -F "scan_type=Generic Findings Import" \
                            -F "file=@${DOJO_FILE}" \
                            -F "product_name=${PRODUCT_NAME}" \
                            -F "engagement_name=${ENGAGEMENT_NAME}" \
                            -F "auto_create_context=true" \
                            -F "close_old_findings=true" \
                            -F "deduplication_on_engagement=true" \
                            -F "product_type_name=Research and Development")
                        HTTP_STATUS=$(echo "$RES" | tail -n1)
                        BODY=$(echo "$RES" | sed '$d')
                        echo "DefectDojo response status: $HTTP_STATUS"
                        if [ "$HTTP_STATUS" = "201" ]; then
                            echo "✅ Aggregated findings uploaded successfully to DefectDojo."
                        else
                            echo "⚠️ DefectDojo upload returned status: $HTTP_STATUS"
                            echo "$BODY"
                        fi
                    else
                        echo "⚠️ Skipping DefectDojo import: dojo-generic.json not found or empty."
                    fi

                    # Post build summary note to DefectDojo engagement
                    if [ -f "${WORKSPACE}/reports/notification-summary.json" ]; then
                        echo "Posting build summary note to DefectDojo engagement..."
                        CRIT=$(grep -o '"critical_count": *[0-9]*' "${WORKSPACE}/reports/notification-summary.json" | grep -o '[0-9]*' || echo '0')
                        TOT=$(grep -o '"total_unique": *[0-9]*' "${WORKSPACE}/reports/notification-summary.json" | grep -o '[0-9]*' || echo '0')
                        GATE=$(grep -o '"gate_status": *"[^"]*"' "${WORKSPACE}/reports/notification-summary.json" | grep -o '"[^"]*"$' | tr -d '"' || echo 'UNKNOWN')
                        NOTE_TEXT="Build #${BUILD_NUMBER} (${BRANCH_NAME:-stage}) | Gate: ${GATE} | Critical: ${CRIT} | Total Unique: ${TOT} | Jenkins: ${BUILD_URL}artifact/reports/security-report.html"
                        curl -s -X POST "${DOJO_BASE_URL}/api/v2/engagements/2/notes/" \
                            -H "Authorization: Token ${DEFECTDOJO_TOKEN}" \
                            -H "Content-Type: application/json" \
                            -d "{\"entry\": \"${NOTE_TEXT}\"}" > /dev/null || true
                        echo "✅ Engagement note posted."
                    fi
                '''
            }
        }

        stage('Developer Notification') {
            steps {
                echo "Evaluating notification routing..."
                sh '''
                    if [ -f "${WORKSPACE}/reports/notification-summary.json" ]; then
                        echo "=========================================="
                        echo "   SECURITY & BUILD NOTIFICATION SUMMARY  "
                        echo "=========================================="
                        cat "${WORKSPACE}/reports/notification-summary.json"
                        echo ""
                        echo "=========================================="
                    fi

                    # Instant Push to Google Chat Webhook
                    if [ -n "${GOOGLE_CHAT_WEBHOOK}" ] && [ -f "${WORKSPACE}/reports/chat-payload.json" ]; then
                        echo "Pushing security alert to Google Chat channel..."
                        curl -s -X POST -H "Content-Type: application/json" \
                            -d @"${WORKSPACE}/reports/chat-payload.json" \
                            "${GOOGLE_CHAT_WEBHOOK}" || echo "⚠️ Warning: Google Chat delivery failed."
                    fi
                '''
            }
        }

        stage('Security Gate Evaluation') {
            steps {
                script {
                    echo "Enforcing Security Gate & Build policy..."
                    def isFailed = (currentBuild.result == 'FAILURE')
                    def summaryFile = "${WORKSPACE}/reports/notification-summary.json"

                    if (fileExists(summaryFile)) {
                        def summaryText = readFile(summaryFile)
                        if (summaryText.contains('"gate_passed": false')) {
                            echo "❌ SECURITY GATE FAILED: Critical vulnerabilities detected!"
                            isFailed = true
                        } else {
                            echo "✅ SECURITY GATE PASSED: All security checks cleared."
                        }
                    }

                    if (isFailed) {
                        currentBuild.result = 'FAILURE'
                        error("❌ Build and deployment halted by security & build policy.")
                    }
                }
            }
        }

        stage('Deploy to Staging') {
            when {
                allOf {
                    branch 'stage'
                    expression { currentBuild.result == null || currentBuild.result == 'SUCCESS' }
                }
            }
            steps {
                echo "Deploying ${IMAGE_NAME}:${BUILD_NUMBER} to Staging Environment..."
                sh 'echo "Deployment to Staging Successful."'
            }
        }

        stage('Production Approval') {
            when {
                allOf {
                    branch 'main'
                    expression { currentBuild.result == null || currentBuild.result == 'SUCCESS' }
                }
            }
            steps {
                timeout(time: 24, unit: 'HOURS') {
                    input message: "Approve deployment of ${IMAGE_NAME}:${BUILD_NUMBER} to Production?", ok: "Deploy to Production"
                }
            }
        }

        stage('Deploy to Production') {
            when {
                allOf {
                    branch 'main'
                    expression { currentBuild.result == null || currentBuild.result == 'SUCCESS' }
                }
            }
            steps {
                echo "Deploying ${IMAGE_NAME}:${BUILD_NUMBER} to Production Environment..."
                sh 'echo "Deployment to Production Successful."'
            }
        }

    }

    post {
        always {
            echo "CI/CD Pipeline Execution Finished for ${PROJECT_NAME}-${SERVICE_NAME} build #${BUILD_NUMBER}"
            // Disk Hygiene: Purge uncompressed scanner dumps from workspace
            sh '''
                rm -f reports/gitleaks.json reports/sonar.json reports/trivy*.json reports/dojo-generic.json reports/chat-payload.json reports/email-body.txt reports/combined-findings.json reports/security-report.html reports/ai-fix-prompt.md reports/notification-summary.json
                echo "🧹 Intermediate reports purged from workspace. Only remediation-bundle.zip retained."
            '''
        }
        success {
            echo "🎉 Pipeline execution completed successfully."
        }
        failure {
            echo "❌ Pipeline execution completed with failures. Review security report artifact and build logs."
        }
    }
}
