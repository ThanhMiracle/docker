pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        skipDefaultCheckout(false)
    }

    parameters {
        booleanParam(name: 'PUSH_TO_DOCKERHUB', defaultValue: false, description: 'Push API and frontend images to Docker Hub after tests pass')
        booleanParam(name: 'DEPLOY_TO_AZURE', defaultValue: false, description: 'Deploy the pushed images to the Azure VM (main branch only)')
        string(name: 'DOCKER_IMAGE_TAG', defaultValue: '', description: 'Docker image tag; defaults to v<Jenkins build number>')
        string(name: 'AZURE_VM_HOST', defaultValue: '', description: 'Azure Linux VM public DNS name or IP')
        string(name: 'AZURE_VM_USER', defaultValue: 'azureuser', description: 'SSH user on the Azure VM')
        string(name: 'DEPLOY_PATH', defaultValue: '/opt/my-app', description: 'Absolute application directory on the VM')
        string(name: 'PUBLIC_BASE_URL', defaultValue: '', description: 'Public app URL, e.g. https://shop.example.com')
        string(name: 'AZURE_SSH_CREDENTIAL_ID', defaultValue: 'azure-vm-ssh', description: 'Jenkins SSH private-key credential ID')
        string(name: 'DOCKERHUB_CREDENTIAL_ID', defaultValue: 'dockerhub-credentials', description: 'Jenkins Docker Hub credential ID')
        string(name: 'FRONTEND_IMAGE', defaultValue: 'thanh2909/my-frontend', description: 'Frontend Docker Hub repository')
        string(name: 'API_IMAGE', defaultValue: 'thanh2909/my-api', description: 'API Docker Hub repository')
    }

    environment {
        DOCKER_REGISTRY = 'docker.io'
    }

    stages {
        stage('Initialize') {
            steps {
                script {
                    env.IMAGE_TAG = params.DOCKER_IMAGE_TAG?.trim() ? params.DOCKER_IMAGE_TAG.trim() : "v${env.BUILD_NUMBER}"
                }
                sh '''
                    set -eu
                    command -v docker
                    command -v ssh
                    command -v scp
                    docker compose version
                    echo "Release tag: ${IMAGE_TAG}"
                '''
            }
        }

        stage('Backend tests') {
            steps {
                sh '''
                    set -eu
                    docker build --target test --tag my-api-test:${IMAGE_TAG} ./backend
                    docker run --rm \
                      -e DATABASE_URL=sqlite:////tmp/test.db \
                      -e JWT_SECRET=ci-only-secret \
                      -e JWT_EXPIRE_MINUTES=120 \
                      -e ADMIN_EMAIL=alice@example.com \
                      -e STORAGE_BACKEND=minio \
                      -e MINIO_BUCKET=ci-test-bucket \
                      -e MINIO_PUBLIC_URL=http://minio.invalid/uploads \
                      -e MINIO_ENDPOINT_URL=http://minio.invalid \
                      my-api-test:${IMAGE_TAG}
                '''
            }
        }

        stage('Frontend build') {
            steps {
                sh '''
                    set -eu
                    docker build --target build ./frontend
                '''
            }
        }

        stage('Build release images') {
            when { expression { return params.PUSH_TO_DOCKERHUB || params.DEPLOY_TO_AZURE } }
            steps {
                sh '''
                    set -eu
                    docker build --tag ${FRONTEND_IMAGE}:${IMAGE_TAG} --tag ${FRONTEND_IMAGE}:latest ./frontend
                    docker build --tag ${API_IMAGE}:${IMAGE_TAG} --tag ${API_IMAGE}:latest ./backend
                '''
            }
        }

        stage('Push Docker Hub images') {
            when {
                allOf {
                    anyOf {
                        branch 'dev'
                        branch 'main'
                    }
                    expression { return params.PUSH_TO_DOCKERHUB || params.DEPLOY_TO_AZURE }
                }
            }
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
                    '''
                }
            }
        }

        stage('Deploy to Azure VM') {
            when {
                allOf {
                    branch 'main'
                    expression { return params.DEPLOY_TO_AZURE }
                }
            }
            steps {
                withCredentials([sshUserPrivateKey(
                    credentialsId: "${params.AZURE_SSH_CREDENTIAL_ID}",
                    keyFileVariable: 'AZURE_SSH_KEY',
                    usernameVariable: 'CREDENTIAL_VM_USER'
                )]) {
                    sh '''
                        set -eu
                        test -n "$AZURE_VM_HOST"
                        test -n "$PUBLIC_BASE_URL"
                        ./scripts/deploy-azure-vm.sh \
                          "$AZURE_VM_HOST" \
                          "${AZURE_VM_USER:-$CREDENTIAL_VM_USER}" \
                          "$AZURE_SSH_KEY" \
                          "$DEPLOY_PATH" \
                          "$IMAGE_TAG" \
                          "$PUBLIC_BASE_URL" \
                          "$FRONTEND_IMAGE" \
                          "$API_IMAGE"
                    '''
                }
            }
        }
    }

    post {
        always {
            sh '''
                docker logout "$DOCKER_REGISTRY" >/dev/null 2>&1 || true
                docker image prune -f >/dev/null 2>&1 || true
            '''
        }
    }
}
