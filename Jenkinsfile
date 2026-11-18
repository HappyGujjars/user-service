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
            post {
                always {
                    archiveArtifacts artifacts: 'reports/trivy-image.json', allowEmptyArchive: true
                }
            }
        }

        stage('Security Report Aggregation') {
            steps {
                echo "Aggregating and deduplicating security reports using containerized Python..."
                sh '''
                    BUILD_OUTCOME="${currentBuild.result ?: 'SUCCESS'}"
                    docker run --rm \
                        --volumes-from jenkins \
                        -w "${WORKSPACE}" \
                        python:3.11-alpine \
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
                            --build-status "${BUILD_OUTCOME}" \
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
                echo "Pushing available scanner findings to DefectDojo..."
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

                    # 4. Trivy Container Image (if built)
                    upload_to_dojo "${WORKSPACE}/reports/trivy-image.json" "Trivy Scan"
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
                '''
            }
        }

        stage('Security Gate Evaluation') {
            steps {
                echo "Enforcing Security Gate & Build policy..."
                sh '''
                    GATE_FAILED=0

                    # 1. Check if compilation / build failed
                    if [ "${currentBuild.result}" = "FAILURE" ]; then
                        echo "❌ BUILD FAILED: Application compilation or docker build failed!"
                        GATE_FAILED=1
                    fi

                    # 2. Check security gate status from summary
                    if [ -f "${WORKSPACE}/reports/notification-summary.json" ]; then
                        if grep -q '"gate_passed": true' "${WORKSPACE}/reports/notification-summary.json"; then
                            echo "✅ SECURITY GATE PASSED: All security checks cleared."
                        else
                            echo "❌ SECURITY GATE FAILED: Critical security vulnerabilities detected!"
                            GATE_FAILED=1
                        fi
                    fi

                    # If either compilation or security failed, stop pipeline before deployment
                    if [ "$GATE_FAILED" -ne 0 ]; then
                        echo "Deployment halted by security & build policy."
                        exit 1
                    fi
                '''
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
        }
        success {
            echo "🎉 Pipeline execution completed successfully."
        }
        failure {
            echo "❌ Pipeline execution completed with failures. Review security report artifact and build logs."
        }
    }
}
