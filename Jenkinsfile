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
                        --verbose \
                        --no-git
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
