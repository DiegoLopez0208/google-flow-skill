#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');

const VERSION = '2.3.0';
const WHEEL = `google_flow_skill-${VERSION}-py3-none-any.whl`;
const URL = `https://github.com/DiegoLopez0208/google-flow-skill/releases/download/v${VERSION}/${WHEEL}`;
const SHA256 = 'ca4a1fe5e91dc686cc5491d7eda2a00f33a3b8f9ed48f7ebd83ecf9b69ce9365';
const root = path.resolve(process.env.GOOGLE_FLOW_RUNTIME_DIR ||
  path.join(os.homedir(), '.google-flow-skill', `runtime-npm-${VERSION}`));
const python = path.join(root, process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');

function execute(command, args, capture = false) {
  const result = spawnSync(command, args, {
    stdio: capture ? 'pipe' : 'inherit', encoding: 'utf8', windowsHide: true,
    env: { ...process.env, PYTHONPATH: '', PYTHONHOME: '' }
  });
  if (result.error && !capture) console.error(result.error.message);
  return result;
}

function findPython() {
  const choices = process.env.GOOGLE_FLOW_PYTHON
    ? [[process.env.GOOGLE_FLOW_PYTHON, []]]
    : (process.platform === 'win32'
      ? [['py', ['-3']], ['python', []], ['python3', []]]
      : [['python3', []], ['python', []]]);
  for (const [command, prefix] of choices) {
    const result = execute(command, [...prefix, '-I', '-c',
      'import sys; print(sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3,10) else 1)'], true);
    if (result.status === 0) return { command, prefix, version: result.stdout.trim() };
  }
  return null;
}

function runtimeVersion() {
  if (!fs.existsSync(python)) return null;
  const result = execute(python, ['-I', '-m', 'google_flow_skill', '--version'], true);
  return result.status === 0 ? result.stdout.trim() : null;
}

async function setup() {
  if (runtimeVersion() === `google-flow ${VERSION}`) {
    console.log(`Runtime ${VERSION} already installed: ${root}`);
    return;
  }
  const base = findPython();
  if (!base) throw new Error('Python 3.10+ is required. Install Python, or set GOOGLE_FLOW_PYTHON to its executable path.');
  if (fs.existsSync(root) && !fs.existsSync(python)) {
    throw new Error(`Incomplete environment at ${root}. Choose a new GOOGLE_FLOW_RUNTIME_DIR or remove that environment and retry.`);
  }
  fs.mkdirSync(path.dirname(root), { recursive: true });
  const lock = `${root}.setup.lock`;
  const descriptor = fs.openSync(lock, 'wx');
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'google-flow-npm-'));
  try {
    console.log(`Downloading Google Flow runtime ${VERSION} from GitHub Releases...`);
    const response = await fetch(URL, { signal: AbortSignal.timeout(120000) });
    if (!response.ok) throw new Error(`Runtime download failed: HTTP ${response.status}`);
    const bytes = Buffer.from(await response.arrayBuffer());
    if (crypto.createHash('sha256').update(bytes).digest('hex') !== SHA256) {
      throw new Error('Runtime checksum mismatch. Installation stopped.');
    }
    const wheel = path.join(temporary, WHEEL);
    fs.writeFileSync(wheel, bytes);
    if (!fs.existsSync(python)) {
      const created = execute(base.command, [...base.prefix, '-I', '-m', 'venv', root]);
      if (created.status !== 0) throw new Error('Could not create a Python venv. Install your OS Python venv support and retry.');
    }
    const installed = execute(python, ['-I', '-m', 'pip', 'install', '--disable-pip-version-check', wheel]);
    if (installed.status !== 0) throw new Error('Runtime installation failed. Check the pip output and retry setup.');
    if (runtimeVersion() !== `google-flow ${VERSION}`) throw new Error('Installed runtime verification failed.');
    console.log(`Installed runtime ${VERSION}: ${root}\nNext: npx google-flow-skill doctor\nThen: npx google-flow-skill login`);
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
    fs.closeSync(descriptor);
    fs.unlinkSync(lock);
  }
}

function doctor() {
  const base = findPython();
  console.log(`Python 3.10+: ${base ? base.version : 'MISSING'}`);
  const version = runtimeVersion();
  const runtimeOk = version === `google-flow ${VERSION}`;
  console.log(`Runtime: ${runtimeOk ? version : 'MISSING or incorrect version; run npx google-flow-skill setup'}`);
  console.log(`Runtime directory: ${root}`);
  if (!base && !fs.existsSync(python)) { process.exitCode = 1; return; }
  const command = fs.existsSync(python) ? python : base.command;
  const prefix = fs.existsSync(python) ? [] : base.prefix;
  const probe = execute(command, [...prefix, '-I', '-c', [
    'import os, sys, shutil',
    'from pathlib import Path',
    'candidates = [shutil.which("google-chrome"), shutil.which("google-chrome-stable"), shutil.which("chrome")]',
    'if sys.platform == "win32":',
    ' for key in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):',
    '  if os.environ.get(key): candidates.append(str(Path(os.environ[key])/"Google/Chrome/Application/chrome.exe"))',
    'elif sys.platform == "darwin":',
    ' candidates.extend(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", str(Path.home()/"Applications/Google Chrome.app/Contents/MacOS/Google Chrome")])',
    'found = next((p for p in candidates if p and Path(p).is_file()), None)',
    'print(found or "MISSING; install Google Chrome separately")',
    'sys.exit(0 if found else 1)'
  ].join('\n')], true);
  console.log(`Chrome: ${probe.stdout ? probe.stdout.trim() : 'check failed'}`);
  console.log('Google login and credit balance are checked separately with login and credits.');
  process.exitCode = base && runtimeOk && probe.status === 0 ? 0 : 1;
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length === 0 || args[0] === '--help' || args[0] === 'help') {
    console.log(`Google Flow npm installer ${VERSION}
Usage: npx google-flow-skill setup
       npx google-flow-skill doctor
       npx google-flow-skill run <runtime arguments>
       npx google-flow-skill <runtime command> [arguments]

Requires Node 20+, Python 3.10+ and Google Chrome.
setup downloads a verified wheel and installs dependencies in a separate venv.
doctor checks local requirements without opening Chrome or generating content.
Other commands run the Python CLI; image/video/batch can spend Flow credits.
--version prints the npm installer version; run --version prints the runtime version.
GOOGLE_FLOW_PYTHON selects Python; GOOGLE_FLOW_RUNTIME_DIR selects the venv.`);
    return;
  }
  if (args[0] === '--version') { console.log(`google-flow-skill ${VERSION}`); return; }
  if (args[0] === 'setup' || args[0] === 'doctor') {
    if (args.length !== 1) throw new Error(`${args[0]} does not accept arguments.`);
    if (args[0] === 'setup') await setup(); else doctor();
    return;
  }
  if (runtimeVersion() !== `google-flow ${VERSION}`) throw new Error('Run npx google-flow-skill setup before using the runtime.');
  const forwarded = args[0] === 'run' ? args.slice(1) : args;
  const result = execute(python, ['-I', '-m', 'google_flow_skill', ...forwarded]);
  process.exitCode = result.status === null ? 1 : result.status;
}

main().catch(error => { console.error(`google-flow-skill: ${error.message}`); process.exitCode = 1; });
