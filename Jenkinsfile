pipeline {
    agent any

    environment {
        APP_ENV = "${env.BRANCH_NAME == 'main' ? 'production' : 'staging'}"
        
        DB_HOST = "172.17.0.1"
        DB_NAME = "hasan_testing_db"

        // PATH untuk semgrep (pipx)
        PATH = "/var/jenkins_home/.local/bin:${env.PATH}"
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build & Test') {
            steps {
                script {
                    IMAGE_TAG = "${env.BRANCH_NAME}-${env.BUILD_NUMBER}"
                    echo "Building Docker image: vuln-flask-app:${IMAGE_TAG}"

                    sh """
                    docker build -t vuln-flask-app:${IMAGE_TAG} .
                    """
                }
            }
        }

        /* ============================================================
           SONARQUBE
        ============================================================ */
        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('SonarCube_Testing') {
                    script {
                        def scannerHome = tool 'SonarCube_Scanner_Testing'
                        sh """
                            "${scannerHome}/bin/sonar-scanner" \
                                -Dsonar.projectKey=testing-python \
                                -Dsonar.sources=. \
                                -Dsonar.python.version=3
                        """
                    }
                }
            }
        }

        stage('SonarQube Quality Gate') {
            steps {
                timeout(time: 2, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: false
                }
            }
        }

        /* ============================================================
           SEMGREP
        ============================================================ */
        stage('Semgrep - Generate SARIF') {
            steps {
                sh '''
                  mkdir -p reports
                  semgrep scan \
                    --config p/security-audit \
                    --config p/owasp-top-ten \
                    --config p/secrets \
                    --sarif --output reports/semgrep.sarif \
                    --metrics=off \
                    . || true
                '''
            }
        }

        stage('Semgrep - Enforce Medium/High') {
            steps {
                sh '''
                  semgrep scan \
                    --config p/security-audit \
                    --config p/owasp-top-ten \
                    --config p/secrets \
                    --severity WARNING \
                    --severity ERROR \
                    --error \
                    --metrics=off \
                    .
                '''
            }
        }

        /* ============================================================
           DEPLOY STAGING / PRODUCTION
        ============================================================ */
        stage('Deploy to STAGING') {
            when { branch 'staging' }
            steps { echo "Deploy ke STAGING..." }
        }

        stage('Deploy to PRODUCTION') {
            when { branch 'main' }
            steps {
                echo "Deploy ke PRODUCTION..."

                sshagent(['SSH_Ubuntu_Server']) {
                    sh '''
                      ssh -o StrictHostKeyChecking=no ubuntu@13.212.183.71"
                        docker run -d -p 9500:9500 --name app-testing vuln-flask-app:${IMAGE_TAG} 
                      "
                    '''
                }
            }
        }
    }

    /* ============================================================
       POST STEPS
    ============================================================ */
    post {
        always {
            archiveArtifacts artifacts: 'reports/semgrep.sarif', fingerprint: true
        }
    }
}