pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 45, unit: 'MINUTES')
        skipDefaultCheckout(true)
    }

    parameters {
        string(name: 'IMAGE_TAG', defaultValue: '', description: 'Docker image tag; defaults to v<Jenkins build number>')
        string(name: 'AZURE_VM_HOST', defaultValue: '', description: 'Azure VM public IP address or DNS name')
        string(name: 'DEPLOY_PATH', defaultValue: '/opt/my-app', description: 'Absolute deployment directory on the Azure VM')
        string(name: 'PUBLIC_BASE_URL', defaultValue: '', description: 'Public URL, for example https://shop.example.com')
    }

    environment {
        DOCKER_REGISTRY = 'docker.io'
        FRONTEND_IMAGE = 'thanh2909/my-frontend'
        API_IMAGE = 'thanh2909/my-api'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Initialize') {
            steps {
                script {
                    env.RELEASE_TAG = params.IMAGE_TAG?.trim() ? params.IMAGE_TAG.trim() : "v${env.BUILD_NUMBER}"
                    currentBuild.displayName = "#${env.BUILD_NUMBER} ${env.RELEASE_TAG}"

                    // Isolate this build from stale credentials on the agent.
                    env.DOCKER_CONFIG = "${env.WORKSPACE}/.docker-ci-${env.BUILD_NUMBER}"
                }
                sh '''
                    set -eu
                    command -v docker
                    docker version >/dev/null

                    case "$RELEASE_TAG" in
                      ''|*[!A-Za-z0-9_.-]*)
                        echo "Invalid image tag: $RELEASE_TAG" >&2
                        exit 1
                        ;;
                    esac
                    [ "${#RELEASE_TAG}" -le 128 ] || {
                      echo "Image tag must not exceed 128 characters" >&2
                      exit 1
                    }

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
                      --pull \
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
                      --pull \
                      --target runtime \
                      --tag "$API_IMAGE:$RELEASE_TAG" \
                      ./backend

                    docker build \
                      --pull \
                      --target runtime \
                      --tag "$FRONTEND_IMAGE:$RELEASE_TAG" \
                      ./frontend
                '''
            }
        }

        stage('Push images') {
            when {
                branch 'main'
            }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-cred',
                    usernameVariable: 'DOCKERHUB_USERNAME',
                    passwordVariable: 'DOCKERHUB_TOKEN'
                )]) {
                    retry(2) {
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

        stage('Deploy to Azure VM') {
            when {
                branch 'main'
            }
            steps {
                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'azure-vm-ssh',
                        keyFileVariable: 'AZURE_SSH_KEY',
                        usernameVariable: 'AZURE_VM_USER'
                    ),
                    file(
                        credentialsId: 'azure-vm-known-hosts',
                        variable: 'AZURE_KNOWN_HOSTS'
                    )
                ]) {
                    sh '''
                        set -eu

                        case "$AZURE_VM_HOST" in
                          ''|*[!A-Za-z0-9.:-]*)
                            echo "AZURE_VM_HOST must be an IP address or DNS name" >&2
                            exit 1
                            ;;
                        esac
                        case "$DEPLOY_PATH" in
                          /*) ;;
                          *) echo "DEPLOY_PATH must be absolute" >&2; exit 1 ;;
                        esac
                        case "$DEPLOY_PATH" in
                          *[!A-Za-z0-9_./-]*)
                            echo "DEPLOY_PATH contains unsupported characters" >&2
                            exit 1
                            ;;
                        esac
                        case "$PUBLIC_BASE_URL" in
                          http://*|https://*) ;;
                          *) echo "PUBLIC_BASE_URL must begin with http:// or https://" >&2; exit 1 ;;
                        esac
                        case "$PUBLIC_BASE_URL" in
                          *[!A-Za-z0-9.:/_-]*)
                            echo "PUBLIC_BASE_URL contains unsupported characters" >&2
                            exit 1
                            ;;
                        esac

                        ./scripts/deploy-azure-vm.sh \
                          "$AZURE_VM_HOST" \
                          "$AZURE_VM_USER" \
                          "$AZURE_SSH_KEY" \
                          "$DEPLOY_PATH" \
                          "$RELEASE_TAG" \
                          "$PUBLIC_BASE_URL" \
                          "$FRONTEND_IMAGE" \
                          "$API_IMAGE" \
                          "$AZURE_KNOWN_HOSTS"
                    '''
                }
            }
        }
    }

    post {
        success {
            echo "Pipeline completed successfully for ${env.RELEASE_TAG}"
        }
        unsuccessful {
            echo "Pipeline did not complete successfully. Check the failed stage before retrying."
        }
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
