pipeline {
    agent any

    
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
                        --no-git
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'gitleaks-report.json', allowEmptyArchive: true
                }
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
