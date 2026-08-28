pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    parameters {
        string(name: 'IMAGE_TAG', defaultValue: '', description: 'Docker image tag; defaults to v<Jenkins build number>')
    }

    environment {
        DOCKER_REGISTRY = 'docker.io'
        FRONTEND_IMAGE = 'thanh2909/my-frontend'
        API_IMAGE = 'thanh2909/my-api'
    }

    stages {
        stage('Initialize') {
            steps {
                script {
                    env.RELEASE_TAG = params.IMAGE_TAG?.trim() ? params.IMAGE_TAG.trim() : "v${env.BUILD_NUMBER}"

                    // Isolate this build from stale credentials on the agent.
                    env.DOCKER_CONFIG = "${env.WORKSPACE}/.docker-ci-${env.BUILD_NUMBER}"
                }
                sh '''
                    set -eu
                    command -v docker
                    mkdir -p "$DOCKER_CONFIG"
                    chmod 700 "$DOCKER_CONFIG"
                    echo "Building release: $RELEASE_TAG"
                '''
            }
        }

        stage('Test backend') {
            steps {
                sh '''
                    set -eu
                    docker build \
                      --target test \
                      --tag "my-api-test:$RELEASE_TAG" \
                      ./backend

                    docker run --rm \
                      -e DATABASE_URL=sqlite:////tmp/test.db \
                      -e JWT_SECRET=ci-only-secret \
                      -e JWT_EXPIRE_MINUTES=120 \
                      -e ADMIN_EMAIL=alice@example.com \
                      -e STORAGE_BACKEND=minio \
                      -e MINIO_BUCKET=ci-test-bucket \
                      -e MINIO_PUBLIC_URL=http://minio.invalid/uploads \
                      -e MINIO_ENDPOINT_URL=http://minio.invalid \
                      "my-api-test:$RELEASE_TAG"
                '''
            }
        }

        stage('Build images') {
            steps {
                sh '''
                    set -eu
                    docker build \
                      --target runtime \
                      --tag "$API_IMAGE:$RELEASE_TAG" \
                      ./backend

                    docker build \
                      --target runtime \
                      --tag "$FRONTEND_IMAGE:$RELEASE_TAG" \
                      ./frontend
                '''
            }
        }

        stage('Push images') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-cred',
                    usernameVariable: 'DOCKERHUB_USERNAME',
                    passwordVariable: 'DOCKERHUB_TOKEN'
                )]) {
                    sh '''
                        set -eu
                        set +x
                        printf '%s' "$DOCKERHUB_TOKEN" | docker login "$DOCKER_REGISTRY" \
                          --username "$DOCKERHUB_USERNAME" \
                          --password-stdin

                        docker push "$API_IMAGE:$RELEASE_TAG"
                        docker push "$FRONTEND_IMAGE:$RELEASE_TAG"
                    '''
                }
            }
        }
    }

    post {
        always {
            sh '''
                expected_config="$WORKSPACE/.docker-ci-$BUILD_NUMBER"
                if [ "${DOCKER_CONFIG:-}" = "$expected_config" ]; then
                    docker logout "$DOCKER_REGISTRY" >/dev/null 2>&1 || true
                    rm -rf -- "$expected_config"
                fi

                if [ -n "${RELEASE_TAG:-}" ]; then
                    docker image rm \
                      "my-api-test:$RELEASE_TAG" \
                      "$API_IMAGE:$RELEASE_TAG" \
                      "$FRONTEND_IMAGE:$RELEASE_TAG" \
                      >/dev/null 2>&1 || true
                fi
            '''
        }
    }
}
