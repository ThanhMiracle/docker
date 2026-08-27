pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timestamps()
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
    }

    stages {
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
                      -e AWS_REGION=ap-southeast-1 \
                      -e AWS_S3_BUCKET=ci-test-bucket \
                      my-api-test:${BUILD_NUMBER}

                    # There is no frontend unit-test script yet. A production
                    # compilation catches dependency and compile failures.
                    docker build --target build ./frontend
                '''
            }
        }

        stage('Build') {
            steps {
                sh '''
                    set -eu
                    docker build \
                      --tag ${FRONTEND_IMAGE}:${BUILD_NUMBER} \
                      --tag ${FRONTEND_IMAGE}:latest \
                      ./frontend
                    docker build \
                      --tag ${API_IMAGE}:${BUILD_NUMBER} \
                      --tag ${API_IMAGE}:latest \
                      ./backend
                '''
            }
        }

        stage('Push') {
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

                        docker push ${FRONTEND_IMAGE}:${BUILD_NUMBER}
                        docker push ${API_IMAGE}:${BUILD_NUMBER}
                        docker push ${FRONTEND_IMAGE}:latest
                        docker push ${API_IMAGE}:latest
                        docker logout "$DOCKER_REGISTRY"
                    '''
                }
            }
        }

        stage('Deploy') {
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
                      "$BUILD_NUMBER"
                '''
            }
        }
    }

}
