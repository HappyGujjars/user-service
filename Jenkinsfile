pipeline {
    agent any

    
    stages {

        stage('show') {
            steps {
                echo 'Working fine'
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
