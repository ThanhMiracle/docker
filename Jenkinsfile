library(
  identifier: 'micro-lib@main',
  retriever: modernSCM([
    $class: 'GitSCMSource',
    remote: 'https://github.com/ThanhMiracle/jenkins-shared-lib.git',
    credentialsId: 'github-pat'
  ])
)

backendPromoteEc2Pipeline(
    registry: 'thanh2909',
    apiImageName: 'simple-fullstack-docker-v3-ci-tests-api',

    apiContext: './backend',
    apiDockerfile: 'Dockerfile',
    apiTestCommand: 'pytest -q',

    composeDevFile: 'docker-compose.yml',
    composeProdFile: 'docker-compose.prod.yml',
    envFile: '.env',

    dockerRegistryCredentialId: 'dockerhub-creds',

    ec2Host: 'YOUR_EC2_PUBLIC_IP',
    ec2User: 'ec2-user',
    sshCredentialId: 'ec2-ssh-key',
    deployPath: '/opt/simple-fullstack-app',

    smokeUrl: 'http://YOUR_EC2_PUBLIC_IP/',
    smokeApiUrl: 'http://YOUR_EC2_PUBLIC_IP/api',

    envCredentials: [
        'DATABASE_URL',
        'JWT_SECRET',
        'JWT_EXPIRE_MINUTES',
        'MINIO_ENDPOINT',
        'MINIO_ACCESS_KEY',
        'MINIO_SECRET_KEY',
        'MINIO_BUCKET',
        'MINIO_SECURE',
        'MINIO_PUBLIC_URL',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
        'POSTGRES_DB'
    ]
)