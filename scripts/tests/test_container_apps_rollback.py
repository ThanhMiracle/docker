"""Exercise rollback with mocked Azure/GitHub CLIs; never contact production.

Install PyYAML==6.0.3, then run python -m unittest discover -s scripts/tests -v.
Requires bash and jq on PATH. On Windows, set BASH_EXE to Git Bash's bash.exe.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
DIGEST = 'sha256:' + 'a' * 64
MOCK = r'''#!/usr/bin/env python
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
tool = Path(sys.argv[0]).name
def emit(value):
    os.write(1, (json.dumps(value) if not isinstance(value, str) else value).encode())
if tool == 'gh':
    run = dict(path='.github/workflows/release.yml', status='completed', conclusion='success',
               event='push', head_branch='main', head_sha='b'*40, run_attempt=1,
               head_repository=dict(full_name='test/repo'))
    if os.environ.get('CASE') == 'failed_release': run['conclusion'] = 'failure'
    if os.environ.get('CASE') == 'wrong_workflow': run['path'] = '.github/workflows/pr-ci.yml'
    emit(run)
elif tool == 'curl':
    if os.environ.get('CASE') == 'unreachable': sys.exit(7)
    if os.environ.get('CASE') == 'frontend_failure' and args[-1].startswith('https://fe.'):
        sys.exit(22)
    if '--output' in args:
        output = args[args.index('--output') + 1]
        if 'frontend-env.js' in output:
            # Git Bash passes POSIX temp paths; use a known Windows path in mocks.
            Path(os.environ['MOCK_TEMP'], 'frontend-env.js').write_text('window.__ENV__={"API_BASE":"/api"};')
    with open(os.environ['MOCK_LOG'], 'a') as log: log.write(json.dumps(['curl'] + args) + '\n')
    if '--output' not in args:
        if os.environ.get('CASE') == 'html_response':
            emit('<html>SPA fallback</html>')
        elif '/ready' in args[-1]:
            emit(dict(status='ready'))
        elif '/health' in args[-1]:
            emit(dict(status='ok'))
        else:
            emit(dict(items=[], total=0))
elif tool == 'az':
    def flag(name): return args[args.index(name) + 1]
    if args[:2] == ['extension', 'add']: sys.exit(0)
    if args[:3] == ['containerapp', 'env', 'show']:
        emit(dict(properties=dict(vnetConfiguration=dict(internal=os.environ.get('CASE') != 'public'))))
        sys.exit(0)
    app = flag('--name')
    container = 'backend' if app == 'be' else 'frontend'
    image = 'registry.azurecr.io/' + ('my-api' if app == 'be' else 'my-fe') + '@sha256:' + 'a'*64
    state_file = Path(os.environ['MOCK_TEMP'], app + '.json')
    if args[:2] == ['containerapp', 'update']:
        with open(os.environ['MOCK_LOG'], 'a') as log: log.write(json.dumps(args) + '\n')
        revision = app + '--' + flag('--revision-suffix')
        state_file.write_text(json.dumps(dict(revision=revision, image=flag('--image'))))
        emit(revision)
    elif args[:3] == ['containerapp', 'revision', 'show']:
        state = json.loads(state_file.read_text())
        emit(dict(properties=dict(active=True, provisioningState='Failed' if os.environ.get('CASE') == 'backend_failure' and app == 'be' else 'Provisioned',
          healthState='Healthy', template=dict(containers=[dict(name=container, image=state['image'])]))))
    elif args[:2] == ['containerapp', 'show']:
        revision = json.loads(state_file.read_text())['revision'] if state_file.exists() else app + '--old'
        emit(dict(properties=dict(latestReadyRevisionName=revision,
          managedEnvironmentId='/env/test', configuration=dict(activeRevisionsMode='Single',
          ingress=dict(targetPort=8000 if app == 'be' else 8080, external=True, fqdn=app+'.example.com'),
          registries=[dict(server='registry.azurecr.io', identity='system')]),
          template=dict(containers=[dict(name=container, image=image, env=[dict(name='API_BASE', value='/api')])]))))
    else: raise SystemExit('Unexpected Azure command: ' + repr(args))
'''


def bash_path(path):
    path = Path(path).resolve().as_posix()
    return '/' + path[0].lower() + path[2:] if os.name == 'nt' else path


class RollbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bash = os.environ.get('BASH_EXE') or shutil.which('bash')
        if not cls.bash:
            raise RuntimeError('bash is required')
        cls.workflow = yaml.safe_load((ROOT / '.github/workflows/rollback-container.yml').read_text())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.bin = self.directory / 'bin'
        self.bin.mkdir()
        for name in ('az', 'gh', 'curl'):
            path = self.bin / name
            path.write_text(MOCK, newline='\n')
            path.chmod(0o755)
        self.log = self.directory / 'commands.jsonl'
        self.output = self.directory / 'output'
        self.env = dict(os.environ, RESOURCE_GROUP='rg', BACKEND_APP='be', FRONTEND_APP='fe',
            MSYS2_ARG_CONV_EXCL='API_BASE=',
            BACKEND_CONTAINER='backend', FRONTEND_CONTAINER='frontend', ACR_LOGIN_SERVER='registry.azurecr.io',
            BACKEND_IMAGE='registry.azurecr.io/my-api@'+DIGEST,
            FRONTEND_IMAGE='registry.azurecr.io/my-fe@'+DIGEST,
            FRONTEND_API_BASE='/api', BACKEND_URL='https://be.example.com', FRONTEND_URL='https://fe.example.com',
            GITHUB_RUN_ID='99', GITHUB_RUN_ATTEMPT='1', GITHUB_OUTPUT=bash_path(self.output),
            GITHUB_REPOSITORY='test/repo', RELEASE_RUN_ID='123', ROLLBACK_REASON='incident test',
            BUILD_COMMIT='b'*40, BUILD_RUN_ID='123', BUILD_RUN_ATTEMPT='1',
            DEPLOY_OPERATION='rollback', REVISION_PREFIX='rb',
            RUNNER_TEMP=bash_path(self.directory), MOCK_TEMP=str(self.directory), MOCK_LOG=str(self.log))

    def run_bash(self, content):
        script = self.directory / 'run.sh'
        script.write_text('set -euo pipefail\n' + content, newline='\n')
        # Set PATH in Bash so mock extensionless commands take priority over az.cmd.
        command = f'export PATH="{bash_path(self.bin)}:$PATH"; bash "{bash_path(script)}"'
        return subprocess.run([self.bash, '-c', command], cwd=self.directory,
                              env=self.env, capture_output=True, text=True)

    def script(self, name):
        return self.run_bash(f'bash "{bash_path(ROOT / "scripts" / name)}"')

    def step(self, step_id):
        step = next(s for s in self.workflow['jobs']['rollback']['steps'] if s.get('id') == step_id)
        return self.run_bash(step['run'])

    def commands(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def updates(self):
        return [cmd for cmd in self.commands() if cmd[:2] == ['containerapp', 'update']]

    def test_restores_exact_images_backend_first_without_changing_environment(self):
        result = self.script('deploy-container-apps.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = self.updates()
        self.assertEqual([cmd[cmd.index('--name')+1] for cmd in commands], ['be', 'fe'])
        self.assertEqual([cmd[cmd.index('--image')+1] for cmd in commands],
                         [self.env['BACKEND_IMAGE'], self.env['FRONTEND_IMAGE']])
        self.assertTrue(all('--set-env-vars' not in cmd for cmd in commands))
        self.assertIn('frontend_revision=fe--rb99-1', self.output.read_text())

    def test_backend_failure_stops_frontend_update(self):
        self.env['CASE'] = 'backend_failure'
        result = self.script('deploy-container-apps.sh')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.updates()), 1)
        self.assertIn('failed to become healthy', result.stderr + result.stdout)

    def test_normal_deployment_still_sets_frontend_route(self):
        self.env['DEPLOY_OPERATION'] = 'deploy'
        self.env.pop('REVISION_PREFIX')
        result = self.script('deploy-container-apps.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = self.updates()
        self.assertNotIn('--set-env-vars', commands[0])
        self.assertIn('API_BASE=/api', commands[1])
        self.assertIn('frontend_revision=fe--gh99-1', self.output.read_text())

    def test_preflight_preserves_frontend_route_and_checks_private_http(self):
        result = self.script('check-container-apps.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('frontend_api_base=/api', self.output.read_text())
        self.assertIn('backend_url=https://be.example.com\n', self.output.read_text())
        self.assertEqual([cmd[-1] for cmd in self.commands()],
                         ['https://be.example.com/', 'https://fe.example.com/'])
        self.assertEqual(self.updates(), [])

    def test_public_apps_get_http_checks(self):
        self.env.update(CASE='public', BACKEND_URL='https://be.example.com', FRONTEND_URL='https://fe.example.com')
        result = self.script('deploy-container-apps.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        urls = [cmd[-1] for cmd in self.commands() if cmd[0] == 'curl']
        self.assertEqual(urls, ['https://be.example.com/health', 'https://be.example.com/ready',
                               'https://be.example.com/products/?limit=1',
                               'https://fe.example.com/', 'https://fe.example.com/env.js?deployment=rb99-1'])

    def test_unreachable_private_origins_stop_before_any_update(self):
        self.env['CASE'] = 'unreachable'
        result = self.script('check-container-apps.sh')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DEPLOY_RUNNER_LABELS', result.stdout)
        self.assertEqual(self.updates(), [])

    def test_missing_http_origin_is_not_reported_as_verified(self):
        self.env['BACKEND_URL'] = ''
        result = self.script('deploy-container-apps.sh')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.updates(), [])

    def test_frontend_failure_reports_partial_operation_without_hidden_rollback(self):
        self.env['CASE'] = 'frontend_failure'
        result = self.script('deploy-container-apps.sh')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.updates()), 2)
        self.assertEqual([cmd[cmd.index('--revision-suffix') + 1] for cmd in self.updates()],
                         ['rb99-1', 'rb99-1'])

    def test_customer_smoke_rejects_html_fallback_with_http_200(self):
        result = self.run_bash(f'bash "{bash_path(ROOT / "scripts/smoke-test.sh")}" https://shop.example.com')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.env['CASE'] = 'html_response'
        result = self.run_bash(f'bash "{bash_path(ROOT / "scripts/smoke-test.sh")}" https://shop.example.com')
        self.assertNotEqual(result.returncode, 0)

    def test_rejects_failed_or_wrong_workflow_and_unsafe_input(self):
        for case in ('failed_release', 'wrong_workflow'):
            with self.subTest(case=case):
                self.env['CASE'] = case
                self.assertNotEqual(self.step('release').returncode, 0)
        self.env.pop('CASE')
        self.env['RELEASE_RUN_ID'] = '$(echo injected)'
        self.assertNotEqual(self.step('release').returncode, 0)
        self.env['RELEASE_RUN_ID'] = '123'
        self.env['ROLLBACK_REASON'] = '  '
        self.assertNotEqual(self.step('release').returncode, 0)

    def test_release_identity_and_digest_must_match_checksum_verified_manifest(self):
        release = self.directory / 'release'
        release.mkdir()
        manifest = dict(schema_version=1, commit='b'*40, workflow_run_id=123, workflow_run_attempt=1,
                        images=dict(api=dict(repository='registry.azurecr.io/my-api', digest=DIGEST),
                                    frontend=dict(repository='registry.azurecr.io/my-fe', digest=DIGEST)))
        def save():
            data = json.dumps(manifest).encode()
            (release / 'release-manifest.json').write_bytes(data)
            (release / 'checksums.txt').write_text(hashlib.sha256(data).hexdigest()+'  release-manifest.json\n', newline='\n')
        save()
        result = self.step('images')
        self.assertEqual(result.returncode, 0, result.stderr)
        for field, value in (('commit', 'c'*40), ('workflow_run_attempt', 2)):
            with self.subTest(field=field):
                original = manifest[field]
                manifest[field] = value
                save()
                self.assertNotEqual(self.step('images').returncode, 0)
                manifest[field] = original
        manifest['images']['api']['digest'] = 'latest'
        save()
        self.assertNotEqual(self.step('images').returncode, 0)
        manifest['images']['api']['digest'] = DIGEST
        save()
        (release / 'release-manifest.json').write_text('{}')
        self.assertNotEqual(self.step('images').returncode, 0)

    def test_successful_release_is_resolved(self):
        result = self.step('release')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('commit='+'b'*40, self.output.read_text())


if __name__ == '__main__':
    unittest.main()
