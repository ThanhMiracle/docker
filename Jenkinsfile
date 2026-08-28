pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    parameters {
        string(name: 'AZURE_VM_HOST', defaultValue: '', description: 'Public DNS name or IP address of the Azure Linux VM')
        string(name: 'AZURE_VM_USER', defaultValue: 'azureuser', description: 'SSH user on the Azure Linux VM')
        string(name: 'DEPLOY_PATH', defaultValue: '/opt/my-app', description: 'Absolute application directory on the Azure VM')
        string(name: 'PUBLIC_BASE_URL', defaultValue: '', description: 'Public HTTPS URL, for example https://shop.example.com')
        string(name: 'AZURE_SSH_CREDENTIAL_ID', defaultValue: 'azure-vm-ssh', description: 'Jenkins SSH private-key credential ID for the Azure VM')
        string(name: 'DOCKERHUB_CREDENTIAL_ID', defaultValue: 'dockerhub-credentials', description: 'Jenkins Docker Hub username/password credential ID')
        string(name: 'FRONTEND_IMAGE', defaultValue: 'thanh2909/my-frontend', description: 'Docker image repository for the frontend')
        string(name: 'API_IMAGE', defaultValue: 'thanh2909/my-api', description: 'Docker image repository for the API')
    }

    environment {
        DOCKER_REGISTRY = 'docker.io'
        IMAGE_TAG = "v${BUILD_NUMBER}"
    }

    stages {
        stage('Verify tools') {
            steps {
                sh '''
                    set -eu
                    command -v docker
                    command -v ssh
                    command -v scp
                    docker compose version
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    set -eu
                    docker build --target test --tag my-api-test:${BUILD_NUMBER} ./backend
                    docker run --rm \
                      -e DATABASE_URL=sqlite:////tmp/test.db \
                      -e JWT_SECRET=ci-only-secret \
                      -e JWT_EXPIRE_MINUTES=120 \
                      -e ADMIN_EMAIL=alice@example.com \
                      -e STORAGE_BACKEND=minio \
                      -e MINIO_BUCKET=ci-test-bucket \
                      -e MINIO_PUBLIC_URL=http://minio.invalid/uploads \
                      -e MINIO_ENDPOINT_URL=http://minio.invalid \
                      my-api-test:${BUILD_NUMBER}
                    docker build --target build ./frontend
                '''
            }
        }

        stage('Build release images') {
            when { branch 'main' }
            steps {
                sh '''
                    set -eu
                    docker build --tag ${FRONTEND_IMAGE}:${IMAGE_TAG} --tag ${FRONTEND_IMAGE}:latest ./frontend
                    docker build --tag ${API_IMAGE}:${IMAGE_TAG} --tag ${API_IMAGE}:latest ./backend
                '''
            }
        }

        stage('Push release images') {
            when { branch 'main' }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: "${params.DOCKERHUB_CREDENTIAL_ID}",
                    usernameVariable: 'DOCKERHUB_USERNAME',
                    passwordVariable: 'DOCKERHUB_TOKEN'
                )]) {
                    sh '''
                        set +x
                        printf '%s' "$DOCKERHUB_TOKEN" | docker login "$DOCKER_REGISTRY" --username "$DOCKERHUB_USERNAME" --password-stdin
                        set -x
                        docker push ${FRONTEND_IMAGE}:${IMAGE_TAG}
                        docker push ${API_IMAGE}:${IMAGE_TAG}
                        docker push ${FRONTEND_IMAGE}:latest
                        docker push ${API_IMAGE}:latest
                        docker logout "$DOCKER_REGISTRY"
                    '''
                }
            }
        }

        stage('Deploy Azure VM') {
            when { branch 'main' }
            steps {
                withCredentials([sshUserPrivateKey(
                    credentialsId: "${params.AZURE_SSH_CREDENTIAL_ID}",
                    keyFileVariable: 'AZURE_SSH_KEY',
                    usernameVariable: 'AZURE_CREDENTIAL_USER'
                )]) {
                    sh '''
                        set -eu
                        test -n "$AZURE_VM_HOST"
                        test -n "$PUBLIC_BASE_URL"
                        ./scripts/deploy-azure-vm.sh \
                          "$AZURE_VM_HOST" \
                          "${AZURE_VM_USER:-$AZURE_CREDENTIAL_USER}" \
                          "$AZURE_SSH_KEY" \
                          "$DEPLOY_PATH" \
                          "$IMAGE_TAG" \
                          "$PUBLIC_BASE_URL"
                    '''
                }
            }
        }
    }

    post {
        always {
            sh 'docker logout "$DOCKER_REGISTRY" || true; docker image prune -f || true'
        }
    }
}
