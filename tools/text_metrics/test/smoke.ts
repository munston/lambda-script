declare const __dirname: string;
declare const require: any;
declare const process: any;
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const child = require('child_process');

import {
  backendVersion,
  supportedExtensions,
  defaultParametricDemo,
  defaultImageParametricDemo,
  buildSparseBasis,
  localInterrogationWitness,
} from '../src';

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'text-metrics-portable-'));

assert(backendVersion().includes('portable-typescript-shim'));
assert(supportedExtensions().includes('portable shim'));
assert(typeof buildSparseBasis === 'function');
assert(typeof localInterrogationWitness === 'function');

const parametricDir = path.join(tmp, 'parametric-demo');
const parametric = defaultParametricDemo(parametricDir);
assert(parametric.finalValLoss < parametric.initialValLoss, 'expected parametric demo to reduce validation loss');
assert(parametric.finalValAccuracy > 0.70, 'expected parametric demo accuracy above 0.70');
assert(fs.existsSync(path.join(parametricDir, 'parametric_demo_report.json')), 'missing parametric report');
assert(fs.existsSync(path.join(parametricDir, 'parametric_demo_summary.txt')), 'missing parametric summary');

const imageDir = path.join(tmp, 'image-parametric-demo');
const imageParametric = defaultImageParametricDemo(imageDir);
assert(imageParametric.finalValLoss < imageParametric.initialValLoss, 'expected image parametric demo to reduce validation loss');
assert(imageParametric.finalValAccuracy >= 0.5, 'expected image parametric demo to meet chance-or-better validation accuracy');
assert(fs.existsSync(path.join(imageDir, 'image_parametric_report.json')), 'missing image parametric report');
assert(fs.existsSync(path.join(imageDir, 'image_parametric_summary.txt')), 'missing image parametric summary');

const cliParametricDir = path.join(tmp, 'cli-parametric');
child.execFileSync(process.execPath, [path.join(__dirname, '..', 'src', 'cli.js'), 'parametric-demo', '--out', cliParametricDir], { stdio: 'ignore' });
assert(fs.existsSync(path.join(cliParametricDir, 'parametric_demo_report.json')), 'missing CLI parametric report');

const cliImageDir = path.join(tmp, 'cli-image-parametric');
child.execFileSync(process.execPath, [path.join(__dirname, '..', 'src', 'cli.js'), 'image-parametric-demo', '--out', cliImageDir], { stdio: 'ignore' });
assert(fs.existsSync(path.join(cliImageDir, 'image_parametric_report.json')), 'missing CLI image parametric report');

console.log('OK portable text metrics smoke');
