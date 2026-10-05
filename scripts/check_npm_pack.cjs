'use strict';
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
// Use npm's JavaScript entry point so Windows does not require a shell.
const npm = process.env.npm_execpath || path.join(path.dirname(process.execPath), 'node_modules/npm/bin/npm-cli.js');
const packed = fs.existsSync(npm)
  ? spawnSync(process.execPath, [npm, 'pack', '--json', '--ignore-scripts'], { encoding: 'utf8' })
  : spawnSync('npm', ['pack', '--json', '--ignore-scripts'], { encoding: 'utf8' });
assert.equal(packed.status, 0, packed.stderr);
const [info] = JSON.parse(packed.stdout);
const actual = info.files.map(file => file.path).sort();
assert.deepEqual(actual, ['LICENSE', 'README.md', 'npm/cli.cjs', 'package.json'].sort());
const destination = path.resolve('.npm-check');
fs.mkdirSync(destination, { recursive: true });
const extracted = spawnSync('tar', ['-xzf', info.filename, '-C', destination], { encoding: 'utf8' });
assert.equal(extracted.status, 0, extracted.stderr);
console.log(`npm package verified: ${info.filename}; ${actual.join(', ')}`);
