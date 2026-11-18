pipeline {
    agent any

    environment {
        // DefectDojo credentials configured in Jenkins Credentials Manager
        DEFECTDOJO_URL   = credentials('dojourl')
        DEFECTDOJO_TOKEN = credentials('dojotoken')

        // SonarQube credentials configured in Jenkins Credentials Manager
        SONAR_URL        = credentials('sonarurl')
        SONAR_TOKEN      = credentials('sonartoken')
    }

    stages {

        stage('show') {
            steps {
                echo 'Working fine'
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
                        --report-path="${WORKSPACE}/gitleaks-report.json" \
                        --report-format=json \
                        --verbose \
                        --no-git || true
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'gitleaks-report.json', allowEmptyArchive: true
                }
            }
        }

        stage('SonarQube SAST Scan') {
            steps {
                echo "Running SonarQube code analysis..."
                sh '''
                    SONAR_BASE_URL="${SONAR_URL%/}"
                    docker run --rm \
                        --volumes-from jenkins \
                        -e SONAR_HOST_URL="${SONAR_BASE_URL}" \
                        -e SONAR_TOKEN="${SONAR_TOKEN}" \
                        sonarsource/sonar-scanner-cli \
                        -Dsonar.host.url="${SONAR_BASE_URL}" \
                        -Dsonar.token="${SONAR_TOKEN}" \
                        -Dsonar.projectKey=vulnerability \
                        -Dsonar.projectName=vulnerability \
                        -Dsonar.projectBaseDir="${WORKSPACE}" \
                        -Dsonar.sources=src \
                        -Dsonar.exclusions="**/node_modules/**,**/*.spec.ts,dist/**"

                    # Wait for SonarQube Compute Engine to process findings
                    sleep 5
                    echo "Fetching SonarQube issues report for DefectDojo..."
                    AUTH_HEADER=$(printf "%s:" "${SONAR_TOKEN}" | base64 | tr -d '\n')
                    curl -s -H "Authorization: Basic ${AUTH_HEADER}" \
                        "${SONAR_BASE_URL}/api/issues/search?componentKeys=vulnerability&resolved=false&ps=500" \
                        -o "${WORKSPACE}/sonar-report.json"
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'sonar-report.json', allowEmptyArchive: true
                }
            }
        }

        stage('Upload to DefectDojo') {
            steps {
                echo "Pushing scan reports to DefectDojo..."
                sh '''
                    DOJO_BASE_URL="${DEFECTDOJO_URL%/}"

                    # 1. Upload Gitleaks Report
                    if [ -f "${WORKSPACE}/gitleaks-report.json" ]; then
                        echo "Report found, uploading Gitleaks to DefectDojo at ${DOJO_BASE_URL}..."
                        GITLEAKS_RES=$(curl -s -w "\\n%{http_code}" -X POST "${DOJO_BASE_URL}/api/v2/import-scan/" \
                            -H "Authorization: Token ${DEFECTDOJO_TOKEN}" \
                            -H "accept: application/json" \
                            -H "Content-Type: multipart/form-data" \
                            -F "scan_type=Gitleaks Scan" \
                            -F "file=@${WORKSPACE}/gitleaks-report.json" \
                            -F "product_name=vulnerability" \
                            -F "engagement_name=DevSecOps-CI" \
                            -F "auto_create_context=true" \
                            -F "close_old_findings=true" \
                            -F "product_type_name=Research and Development")

                        GITLEAKS_CODE=$(echo "$GITLEAKS_RES" | tail -n1)
                        GITLEAKS_BODY=$(echo "$GITLEAKS_RES" | sed '$d')

                        echo "DefectDojo Gitleaks Response: $GITLEAKS_BODY"
                        if [ "$GITLEAKS_CODE" = "200" ] || [ "$GITLEAKS_CODE" = "201" ]; then
                            echo "✅ Gitleaks report uploaded to DefectDojo successfully (HTTP $GITLEAKS_CODE)!"
                        else
                            echo "❌ Failed to upload Gitleaks report. HTTP Status: $GITLEAKS_CODE"
                            exit 1
                        fi
                    else
                        echo "⚠️ gitleaks-report.json not found, skipping upload."
                    fi

                    # 2. Upload SonarQube Report
                    if [ -f "${WORKSPACE}/sonar-report.json" ]; then
                        echo "Report found, uploading SonarQube to DefectDojo at ${DOJO_BASE_URL}..."
                        SONAR_RES=$(curl -s -w "\\n%{http_code}" -X POST "${DOJO_BASE_URL}/api/v2/import-scan/" \
                            -H "Authorization: Token ${DEFECTDOJO_TOKEN}" \
                            -H "accept: application/json" \
                            -H "Content-Type: multipart/form-data" \
                            -F "scan_type=SonarQube Scan" \
                            -F "file=@${WORKSPACE}/sonar-report.json" \
                            -F "product_name=vulnerability" \
                            -F "engagement_name=DevSecOps-CI" \
                            -F "auto_create_context=true" \
                            -F "close_old_findings=true" \
                            -F "product_type_name=Research and Development")

                        SONAR_CODE=$(echo "$SONAR_RES" | tail -n1)
                        SONAR_BODY=$(echo "$SONAR_RES" | sed '$d')

                        echo "DefectDojo SonarQube Response: $SONAR_BODY"
                        if [ "$SONAR_CODE" = "200" ] || [ "$SONAR_CODE" = "201" ]; then
                            echo "✅ SonarQube report uploaded to DefectDojo successfully (HTTP $SONAR_CODE)!"
                        else
                            echo "❌ Failed to upload SonarQube report. HTTP Status: $SONAR_CODE"
                            exit 1
                        fi
                    else
                        echo "⚠️ sonar-report.json not found, skipping upload."
                    fi
                '''
            }
        }

    }

    post {
        success {
            echo "Deployment Successful"
        }

        failure {
            echo "Deployment Failed"
        }
    }
}
