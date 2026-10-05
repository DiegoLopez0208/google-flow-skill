'use strict';

// Test the packed npm executable with a real, isolated Python environment.
// No login, browser launch or generation. setup downloads the pinned release.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'flow-npm-smoke-'));
const cli = process.argv[2] ? path.resolve(process.argv[2]) : path.resolve('npm/cli.cjs');
const env = { ...process.env, GOOGLE_FLOW_RUNTIME_DIR: path.join(directory, 'runtime'), FLOW_HOME: path.join(directory, 'state') };
function run(args, expected = 0) {
  const result = spawnSync(process.execPath, [cli, ...args], { cwd: directory, env, encoding: 'utf8' });
  assert.equal(result.status, expected, result.stdout + result.stderr);
  return result.stdout;
}
try {
  assert.match(run(['--version']), /google-flow-skill 2\.3\.0/);
  run(['run', '--version'], 1);
  const missing = run(['doctor'], 1);
  assert.match(missing, /Runtime: MISSING/);
  assert.equal(fs.existsSync(env.GOOGLE_FLOW_RUNTIME_DIR), false);
  run(['setup']);
  assert.match(run(['setup']), /already installed/);
  assert.match(run(['run', '--version']), /google-flow 2\.3\.0/);
  run(['video', '--help']);
  run(['run', '--not-a-real-argument'], 2);
  run(['status'], 1);
  assert.equal(fs.existsSync(env.FLOW_HOME), false);
  const output = path.join(directory, 'examples with spaces');
  run(['examples', '--out', output]);
  assert.ok(fs.existsSync(path.join(output, 'example_script.json')));
  const doctor = spawnSync(process.execPath, [cli, 'doctor'], { cwd: directory, env, encoding: 'utf8' });
  assert.ok([0, 1].includes(doctor.status), doctor.stderr);
  assert.match(doctor.stdout, /Runtime: google-flow 2\.3\.0/);
  assert.match(doctor.stdout, /Chrome:/);
  console.log('npm smoke passed: isolated setup, repeat setup, arguments, exit codes, examples and doctor.');
} finally {
  fs.rmSync(directory, { recursive: true, force: true });
}
