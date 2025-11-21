pipeline {
    agent any

    environment {
        APP_ENV = "${env.BRANCH_NAME == 'main' ? 'production' : 'staging'}"
        
        // DB info (secretnya jangan taruh sini)
        DB_HOST = "172.17.0.1"
        DB_NAME = "hasan_testing_db"

        // PATH untuk semgrep (pipx)
        PATH = "/var/jenkins_home/.local/bin:${env.PATH}"

        // Untuk sekarang image tetap latest
        IMAGE_TAG = "latest"
    }

    stages {

        /* ============================================================
           CHECKOUT
        ============================================================ */
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        /* ============================================================
           TRIVY FILESYSTEM SCAN (SCA)
        ============================================================ */
        stage('Trivy FS Scan') {
            steps {
                sh """
                    mkdir -p reports
                    echo "[TRIVY] Scanning filesystem..."
                    trivy fs \
                        --severity HIGH,CRITICAL \
                        --exit-code 1 \
                        --no-progress \
                        --format json \
                        --output reports/trivy-fs-report.json \
                        .
                """
            }
        }

        /* ============================================================
           DOCKER BUILD
        ============================================================ */
        stage('Build Docker Image') {
            steps {
                script {
                    echo "Building Docker image vuln-flask-app:latest"
                    sh """
                        docker build -t vuln-flask-app:${env.IMAGE_TAG} .
                    """
                }
            }
        }

        /* ============================================================
           TRIVY IMAGE SCAN
        ============================================================ */
        stage('Trivy Image Scan') {
            steps {
                sh """
                    mkdir -p reports
                    echo "[TRIVY] Scanning Docker image vuln-flask-app:${env.IMAGE_TAG}"
                    trivy image \
                        --severity HIGH,CRITICAL \
                        --exit-code 1 \
                        --no-progress \
                        --format json \
                        --output reports/trivy-image-report.json \
                        vuln-flask-app:${env.IMAGE_TAG}
                """
            }
        }

        /* ============================================================
           SONARQUBE ANALYSIS
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
           DEPLOY
        ============================================================ */
        stage('Deploy to STAGING') {
            when { branch 'staging' }
            steps {
                echo "Deploy ke STAGING..."
                // Tambah step docker run staging kalau mau
            }
        }

        stage('Deploy to PRODUCTION') {
            when { branch 'main' }
            steps {
                echo "Deploy ke PRODUCTION menggunakan vuln-flask-app:${env.IMAGE_TAG}"

                sshagent(['SSH_Ubuntu_Server']) {
                    withCredentials([usernamePassword(
                        credentialsId: 'hasan_testing_MySQL', 
                        usernameVariable: 'DB_USER',
                        passwordVariable: 'DB_PASS'
                    )]) {
                        sh """
                            ssh -o StrictHostKeyChecking=no ubuntu@13.212.114.218 '
                                docker stop app-testing || true &&
                                docker rm app-testing || true &&
                                docker run -d -p 9500:9500 --name app-testing \
                                    -e DB_HOST=${DB_HOST} \
                                    -e DB_NAME=${DB_NAME} \
                                    -e DB_USER=${DB_USER} \
                                    -e DB_PASS=${DB_PASS} \
                                    vuln-flask-app:${IMAGE_TAG}
                            '
                        """
                    }
                }
            }
        }

        /* ============================================================
           ZAP DAST BASELINE
        ============================================================ */
        stage('DAST - ZAP API Scan') {
            when { branch 'main' }
            steps {
                  sh '''
                    mkdir -p reports
                    chmod 777 reports

                   docker run --rm \
                    -u 0:0 \
                    -v "$(pwd)/reports:/zap/wrk" \
                    zaproxy/zap-stable \
                    zap-api-scan.py \
                        -t http://13.212.114.218:9500/openapi.json \
                        -f openapi \
                        -J zap-api-report.json || true

                    echo "[DEBUG] Isi folder reports setelah ZAP API:"
                    ls -lah reports || true
                '''
            }
        }
    }

    /* ============================================================
       POST STEPS (Artifacts)
    ============================================================ */
    post {
        always {
            archiveArtifacts artifacts: 'reports/*.json', fingerprint: true, allowEmptyArchive: true
            archiveArtifacts artifacts: 'reports/*.sarif', fingerprint: true, allowEmptyArchive: true
            archiveArtifacts artifacts: 'reports/*.html', fingerprint: true, allowEmptyArchive: true
        }
    }
}