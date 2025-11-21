pipeline {
    agent any

    environment {
        // contoh: beda ENV untuk app
        APP_ENV = "${env.BRANCH_NAME == 'main' ? 'production' : 'staging'}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build & Test') {
            steps {
                sh 'echo "Build & test untuk ${APP_ENV}"'
                // mvn test / go test / npm test dll
            }
        }

        stage('Security Scan') {
            steps {
                sh 'echo "Jalankan Semgrep / Sonar di ${APP_ENV}"'
            }
        }

        stage('Deploy to STAGING') {
            when {
                branch 'staging'
            }
            steps {
                sh '''
                  echo "Deploy ke STAGING"
                  # contoh:
                  # kubectl --context=staging apply -f k8s/
                '''
            }
        }

        stage('Deploy to PRODUCTION') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                  echo "Deploy ke PRODUCTION"
                  # kubectl --context=production apply -f k8s/
                '''
            }
        }
    }
}
