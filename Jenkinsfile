pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    parameters {
        string(
            name: 'ALB_NAME',
            defaultValue: '',
            description: 'AWS Application Load Balancer name used for API_BASE'
        )
        choice(
            name: 'ALB_SCHEME',
            choices: ['https', 'http'],
            description: 'Public protocol exposed by the ALB'
        )
        string(
            name: 'AWS_DEPLOY_REGION',
            defaultValue: 'ap-southeast-1',
            description: 'AWS region containing the ALB'
        )
        string(
            name: 'ASG_NAME',
            defaultValue: '',
            description: 'Auto Scaling Group whose instances receive the deployment'
        )
        string(
            name: 'PROD_ENV_PARAMETER',
            defaultValue: '/my-app/production/env',
            description: 'SSM SecureString parameter containing the production .env'
        )
        string(
            name: 'DOCKERHUB_CREDENTIAL_ID',
            defaultValue: 'dockerhub-credentials',
            description: 'Jenkins username/password credential ID for Docker Hub'
        )
        string(
            name: 'FRONTEND_IMAGE',
            defaultValue: 'thanh2909/my-frontend',
            description: 'Docker image repository for the frontend'
        )
        string(
            name: 'API_IMAGE',
            defaultValue: 'thanh2909/my-api',
            description: 'Docker image repository for the API'
        )
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
                    command -v aws
                    command -v jq
                    docker compose version
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    set -eu

                    docker build \
                      --target test \
                      --tag my-api-test:${BUILD_NUMBER} \
                      ./backend

                    docker run --rm \
                      -e DATABASE_URL=sqlite:////tmp/test.db \
                      -e JWT_SECRET=ci-only-secret \
                      -e JWT_EXPIRE_MINUTES=120 \
                      -e STORAGE_BACKEND=minio \
                      -e MINIO_BUCKET=ci-test-bucket \
                      -e MINIO_PUBLIC_URL=http://minio.invalid/uploads \
                      -e MINIO_ENDPOINT_URL=http://minio.invalid \
                      my-api-test:${BUILD_NUMBER}

                    # There is no frontend unit-test script yet. A production
                    # compilation catches dependency and compile failures.
                    docker build --target build ./frontend
                '''
            }
        }

        stage('Build release images') {
            steps {
                sh '''
                    set -eu
                    docker build \
                      --tag ${FRONTEND_IMAGE}:${IMAGE_TAG} \
                      --tag ${FRONTEND_IMAGE}:latest \
                      ./frontend
                    docker build \
                      --tag ${API_IMAGE}:${IMAGE_TAG} \
                      --tag ${API_IMAGE}:latest \
                      ./backend
                '''
            }
        }

        stage('Push release images') {
            when {
                branch 'main'
            }
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: "${params.DOCKERHUB_CREDENTIAL_ID}",
                        usernameVariable: 'DOCKERHUB_USERNAME',
                        passwordVariable: 'DOCKERHUB_TOKEN'
                    )
                ]) {
                    sh '''
                        set +x
                        printf '%s' "$DOCKERHUB_TOKEN" |
                          docker login "$DOCKER_REGISTRY" \
                            --username "$DOCKERHUB_USERNAME" \
                            --password-stdin
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

        stage('Deploy production') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    set -eu
                    ./scripts/deploy-ssm.sh \
                      "$ASG_NAME" \
                      "$ALB_NAME" \
                      "$ALB_SCHEME" \
                      "$AWS_DEPLOY_REGION" \
                      "$PROD_ENV_PARAMETER" \
                      "$IMAGE_TAG"
                '''
            }
        }
    }

    post {
        always {
            sh 'docker logout "$DOCKER_REGISTRY" || true; docker image prune -f || true'
        }
    }

}
