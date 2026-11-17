pipeline {
    agent any

    environment {
        // DefectDojo credentials configured in Jenkins Credentials Manager
        DEFECTDOJO_URL   = credentials('dojourl')
        DEFECTDOJO_TOKEN = credentials('dojotoken')
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

        stage('Upload to DefectDojo') {
            steps {
                echo "Pushing Gitleaks report to DefectDojo..."
                sh '''
                    if [ -f "${WORKSPACE}/gitleaks-report.json" ]; then
                        DOJO_BASE_URL="${DEFECTDOJO_URL%/}"
                        echo "Report found, uploading to DefectDojo at ${DOJO_BASE_URL}..."
                        RESPONSE=$(curl -s -w "\\n%{http_code}" -X POST "${DOJO_BASE_URL}/api/v2/import-scan/" \
                            -H "Authorization: Token ${DEFECTDOJO_TOKEN}" \
                            -H "accept: application/json" \
                            -H "Content-Type: multipart/form-data" \
                            -F "scan_type=Gitleaks Scan" \
                            -F "file=@${WORKSPACE}/gitleaks-report.json" \
                            -F "product_name=user-service" \
                            -F "engagement_name=DevSecOps-CI" \
                            -F "auto_create_context=true" \
                            -F "close_old_findings=true")

                        HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
                        BODY=$(echo "$RESPONSE" | sed '$d')

                        echo "DefectDojo Response: $BODY"
                        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
                            echo "✅ Report uploaded to DefectDojo successfully (HTTP $HTTP_CODE)!"
                        else
                            echo "❌ Failed to upload to DefectDojo. HTTP Status: $HTTP_CODE"
                            exit 1
                        fi
                    else
                        echo "⚠️ gitleaks-report.json not found, skipping upload."
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
