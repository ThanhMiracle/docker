library(
    identifier: 'micro-lib@main',
    retriever: modernSCM([
        $class: 'GitSCMSource',
        remote: 'https://github.com/ThanhMiracle/jenkins-shared-lib.git',
        credentialsId: 'github-pat'
    ])
)

ec2AsgCiCd(
<<<<<<< HEAD
    deployBranch: 'main',

    dockerCredentialsId: 'dockerhub-creds',
    dockerRegistry: 'docker.io',

    frontendImage: 'thanh2909/simple-fullstack-docker-v3-ci-tests-frontend',
    backendImage: 'thanh2909/simple-fullstack-docker-v3-ci-tests-api',

    frontendContext: './frontend',
    backendContext: './backend',

    frontendService: 'frontend',
    backendService: 'api',

    composeFile: 'docker-compose.prod.yml',
    nginxDir: 'nginx',

    testCommand: '''
        docker build -t fullstack-backend-ci:${RELEASE_TAG} ./backend

        docker run --rm \
          -e DATABASE_URL=sqlite:////tmp/app.db \
          -e JWT_SECRET=ci-secret \
          -e JWT_EXPIRE_MINUTES=120 \
          -e AWS_REGION=ap-southeast-1 \
          -e AWS_S3_BUCKET=ci-test-uploads \
          -e AWS_EC2_METADATA_DISABLED=true \
          -v "$PWD/backend/tests:/app/tests:ro" \
          fullstack-backend-ci:${RELEASE_TAG} \
          pytest -q -p no:cacheprovider /app/tests
    ''',

    // Bỏ trống nếu Jenkins EC2 đã có IAM role.
    awsCredentialsId: env.AWS_CREDENTIALS_ID ?: '',
    awsRegion: env.AWS_REGION ?: 'ap-southeast-1',

    artifactBucket: env.DEPLOY_ARTIFACT_BUCKET,
    environmentParameter: env.DEPLOY_ENV_PARAMETER,
    autoScalingGroup: env.DEPLOY_ASG_NAME,
    launchTemplateId: env.DEPLOY_LAUNCH_TEMPLATE_ID,

=======
    dockerCredentialsId: 'dockerhub-creds',
    dockerRegistry: 'docker.io',
    frontendImage: 'thanh2909/simple-fullstack-docker-v3-ci-tests-frontend',
    backendImage: 'thanh2909/simple-fullstack-docker-v3-ci-tests-api',
    frontendContext: './frontend',
    backendContext: './backend',
    frontendService: 'frontend',
    backendService: 'api',

    composeFile: 'docker-compose.prod.yml',
    nginxDir: 'nginx',
    testCommand: '''
        docker build --target test \
          -t fullstack-backend-ci:${RELEASE_TAG} ./backend
        docker run --rm \
          -e DATABASE_URL=sqlite:////tmp/app.db \
          -e JWT_SECRET=ci-secret \
          -e JWT_EXPIRE_MINUTES=120 \
          -e MINIO_ENDPOINT=127.0.0.1:9000 \
          -e MINIO_ACCESS_KEY=minioadmin \
          -e MINIO_SECRET_KEY=minioadmin \
          -e MINIO_BUCKET=uploads \
          -e MINIO_SECURE=false \
          -e MINIO_PUBLIC_URL=http://127.0.0.1:9000 \
          fullstack-backend-ci:${RELEASE_TAG}
    ''',

    // Configure these values in Jenkins global/folder environment variables.
    // AWS_CREDENTIALS_ID can be empty when the Jenkins agent has an IAM role.
    awsCredentialsId: env.AWS_CREDENTIALS_ID ?: '',
    awsRegion: env.AWS_REGION ?: 'ap-southeast-1',
    artifactBucket: env.DEPLOY_ARTIFACT_BUCKET,
    environmentParameter: env.DEPLOY_ENV_PARAMETER,
    autoScalingGroup: env.DEPLOY_ASG_NAME,
    launchTemplateId: env.DEPLOY_LAUNCH_TEMPLATE_ID,

>>>>>>> 36d4878 (add test)
    trivyEnabled: true
)
