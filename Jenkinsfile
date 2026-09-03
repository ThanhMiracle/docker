pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 45, unit: 'MINUTES')
        skipDefaultCheckout(true)
    }

    parameters {
        choice(name: 'COMPONENT', choices: ['all', 'backend', 'frontend'], description: 'Component to build and push')
        string(name: 'IMAGE_TAG', defaultValue: '', description: 'Optional Docker image tag; blank builds and scans without pushing or deploying')
        string(name: 'SONAR_HOST_URL', defaultValue: 'http://sonarqube:9000', description: 'SonarQube URL on the Docker Compose network')
        string(name: 'AZURE_VM_HOST', defaultValue: '', description: 'Azure VM public IP address or DNS name')
        string(name: 'DEPLOY_PATH', defaultValue: '/opt/my-app', description: 'Absolute deployment directory on the Azure VM')
        string(name: 'PUBLIC_BASE_URL', defaultValue: '', description: 'Public URL, for example https://shop.example.com')
    }

    environment {
        DOCKER_REGISTRY = 'docker.io'
        FRONTEND_IMAGE = 'thanh2909/my-frontend'
        API_IMAGE = 'thanh2909/my-api'
        SONAR_SCANNER_IMAGE = 'sonarsource/sonar-scanner-cli:12.1.0.3233_8.0.1'
        SONAR_USER_HOME = "${WORKSPACE}/.sonar"
        TRIVY_IMAGE = 'aquasec/trivy:0.74.0'
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
                    env.RELEASE_TAG = params.IMAGE_TAG?.trim() ?: ''
                    currentBuild.displayName = env.RELEASE_TAG \
                        ? "#${env.BUILD_NUMBER} ${params.COMPONENT} ${env.RELEASE_TAG}" \
                        : "#${env.BUILD_NUMBER} ${params.COMPONENT} untagged"

                    // Isolate this build from stale credentials on the agent.
                    env.DOCKER_CONFIG = "${env.WORKSPACE}/.docker-ci-${env.BUILD_NUMBER}"
                }
                sh '''
                    set -eu
                    command -v docker
                    docker version >/dev/null

                    case "$RELEASE_TAG" in
                      '') ;;
                      *[!A-Za-z0-9_.-]*)
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
                    rm -f -- \
                      "$WORKSPACE/.api-test-image-id" \
                      "$WORKSPACE/.api-image-id" \
                      "$WORKSPACE/.frontend-image-id"
                    echo "Building component: $COMPONENT"
                    if [ -n "$RELEASE_TAG" ]; then
                      echo "Building release: $RELEASE_TAG"
                    else
                      echo "No image tag supplied; push and deployment will be skipped"
                    fi
                '''
            }
        }

        stage('SonarQube analysis') {
            steps {
                withCredentials([string(
                    credentialsId: 'sonarqube-token',
                    variable: 'SONAR_TOKEN'
                )]) {
                    sh '''
                        set -eu

                        test -f "$WORKSPACE/sonar-project.properties" || {
                        echo "sonar-project.properties is missing from the Jenkins checkout" >&2
                        exit 1
                        }

                        case "$SONAR_HOST_URL" in
                        http://*|https://*) ;;
                        *)
                            echo "SONAR_HOST_URL must begin with http:// or https://" >&2
                            exit 1
                            ;;
                        esac

                        export SONAR_USER_HOME="$WORKSPACE/.sonar"
                        mkdir -p "$SONAR_USER_HOME"

                        echo "SONAR_USER_HOME=$SONAR_USER_HOME"

                        sonar-scan
                    '''
                }
            }
        }

        stage('Test backend') {
            when {
                expression {
                    params.COMPONENT == 'all' || params.COMPONENT == 'backend'
                }
            }
            steps {
                sh '''
                    set -eu
                    docker build \
                      --pull \
                      --target test \
                      --iidfile "$WORKSPACE/.api-test-image-id" \
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
                      "$(cat "$WORKSPACE/.api-test-image-id")"
                '''
            }
        }

        stage('Build backend') {
            when {
                expression {
                    params.COMPONENT == 'all' || params.COMPONENT == 'backend'
                }
            }
            steps {
                sh '''
                    set -eu
                    set -- docker build \
                      --pull \
                      --target runtime \
                      --iidfile "$WORKSPACE/.api-image-id"
                    if [ -n "$RELEASE_TAG" ]; then
                      set -- "$@" --tag "$API_IMAGE:$RELEASE_TAG"
                    fi
                    "$@" ./backend
                '''
            }
        }

        stage('Build frontend') {
            when {
                expression {
                    params.COMPONENT == 'all' || params.COMPONENT == 'frontend'
                }
            }
            steps {
                sh '''
                    set -eu
                    set -- docker build \
                      --pull \
                      --target runtime \
                      --iidfile "$WORKSPACE/.frontend-image-id"
                    if [ -n "$RELEASE_TAG" ]; then
                      set -- "$@" --tag "$FRONTEND_IMAGE:$RELEASE_TAG"
                    fi
                    "$@" ./frontend
                '''
            }
        }

        stage('Scan backend image') {
            when {
                expression {
                    params.COMPONENT == 'all' || params.COMPONENT == 'backend'
                }
            }
            steps {
                sh '''
                    set -eu
                    docker run --rm \
                      -v /var/run/docker.sock:/var/run/docker.sock \
                      -v trivy-cache:/root/.cache/ \
                      "$TRIVY_IMAGE" image \
                      --exit-code 1 \
                      --ignore-unfixed \
                      --severity HIGH,CRITICAL \
                      "$(cat "$WORKSPACE/.api-image-id")"
                '''
            }
        }

        stage('Scan frontend image') {
            when {
                expression {
                    params.COMPONENT == 'all' || params.COMPONENT == 'frontend'
                }
            }
            steps {
                sh '''
                    set -eu
                    docker run --rm \
                      -v /var/run/docker.sock:/var/run/docker.sock \
                      -v trivy-cache:/root/.cache/ \
                      "$TRIVY_IMAGE" image \
                      --exit-code 1 \
                      --ignore-unfixed \
                      --severity HIGH,CRITICAL \
                      "$(cat "$WORKSPACE/.frontend-image-id")"
                '''
            }
        }

        stage('Push backend') {
            when {
                allOf {
                    branch 'main'
                    expression {
                        params.IMAGE_TAG?.trim()
                    }
                    expression {
                        params.COMPONENT == 'all' || params.COMPONENT == 'backend'
                    }
                }
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
                        '''
                    }
                }
            }
        }

        stage('Push frontend') {
            when {
                allOf {
                    branch 'main'
                    expression {
                        params.IMAGE_TAG?.trim()
                    }
                    expression {
                        params.COMPONENT == 'all' || params.COMPONENT == 'frontend'
                    }
                }
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

                            docker push "$FRONTEND_IMAGE:$RELEASE_TAG"
                        '''
                    }
                }
            }
        }

        stage('Deploy to Azure VM') {
            when {
                allOf {
                    branch 'main'
                    expression {
                        params.IMAGE_TAG?.trim()
                    }
                    expression {
                        params.COMPONENT == 'all'
                    }
                }
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
                      "$API_IMAGE:$RELEASE_TAG" \
                      "$FRONTEND_IMAGE:$RELEASE_TAG" \
                      >/dev/null 2>&1 || true
                fi

                for image_id_file in \
                  "$WORKSPACE/.api-test-image-id" \
                  "$WORKSPACE/.api-image-id" \
                  "$WORKSPACE/.frontend-image-id"; do
                    if [ -s "$image_id_file" ]; then
                        docker image rm "$(cat "$image_id_file")" >/dev/null 2>&1 || true
                        rm -f -- "$image_id_file"
                    fi
                done
            '''
        }
    }
}