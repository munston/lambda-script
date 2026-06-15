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

function readJson(file: string): any {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function readText(file: string): string {
  return fs.readFileSync(file, 'utf8');
}

function assertFile(pathName: string, message: string): void {
  assert(fs.existsSync(pathName), message);
}

function assertNumberField(report: Record<string, unknown>, field: string): void {
  assert.strictEqual(typeof report[field], 'number', `expected numeric report field ${field}`);
}

function assertTrainingReport(report: Record<string, unknown>, label: string): void {
  assertNumberField(report, 'initialValLoss');
  assertNumberField(report, 'finalValLoss');
  assertNumberField(report, 'finalValAccuracy');
  assert(Number(report.finalValLoss) <= Number(report.initialValLoss), `expected ${label} finalValLoss to improve or match initialValLoss`);
}

function assertSummaryContains(summary: string, fields: string[]): void {
  for (const field of fields) assert(summary.includes(`${field}:`), `summary missing ${field}`);
}

function runCli(command: string, outDir: string, extra: string[] = []): void {
  child.execFileSync(process.execPath, [path.join(__dirname, '..', 'src', 'cli.js'), command, '--out', outDir, ...extra], { stdio: 'ignore' });
}

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'text-metrics-portable-'));

assert(backendVersion().includes('portable-typescript-shim'));
assert(supportedExtensions().includes('portable shim'));
assert(typeof buildSparseBasis === 'function');
assert(typeof localInterrogationWitness === 'function');

const parametricDir = path.join(tmp, 'parametric-demo');
const parametric = defaultParametricDemo(parametricDir);
assert(parametric.finalValLoss < parametric.initialValLoss, 'expected parametric demo to reduce validation loss');
assert(parametric.finalValAccuracy > 0.70, 'expected parametric demo accuracy above 0.70');
const parametricReportPath = path.join(parametricDir, 'parametric_demo_report.json');
const parametricSummaryPath = path.join(parametricDir, 'parametric_demo_summary.txt');
assertFile(parametricReportPath, 'missing parametric report');
assertFile(parametricSummaryPath, 'missing parametric summary');
const parametricReport = readJson(parametricReportPath);
assertTrainingReport(parametricReport, 'parametric demo');
assertSummaryContains(readText(parametricSummaryPath), [
  'initial_train_loss',
  'initial_val_loss',
  'final_train_loss',
  'final_val_loss',
  'final_train_accuracy',
  'final_val_accuracy',
  'learned_scale_mean',
]);

const imageDir = path.join(tmp, 'image-parametric-demo');
const imageParametric = defaultImageParametricDemo(imageDir);
assert(imageParametric.finalValLoss < imageParametric.initialValLoss, 'expected image parametric demo to reduce validation loss');
assert(imageParametric.finalValAccuracy >= 0.5, 'expected image parametric demo to meet chance-or-better validation accuracy');
const imageReportPath = path.join(imageDir, 'image_parametric_report.json');
const imageSummaryPath = path.join(imageDir, 'image_parametric_summary.txt');
assertFile(imageReportPath, 'missing image parametric report');
assertFile(imageSummaryPath, 'missing image parametric summary');
const imageReport = readJson(imageReportPath);
assertTrainingReport(imageReport, 'image parametric demo');
assertNumberField(imageReport, 'finalValScoreCorrelation');
assertSummaryContains(readText(imageSummaryPath), [
  'native_score_threshold',
  'initial_train_loss',
  'initial_val_loss',
  'final_train_loss',
  'final_val_loss',
  'final_train_accuracy',
  'final_val_accuracy',
  'final_val_score_correlation',
  'learned_scale_mean',
]);

const cliParametricDir = path.join(tmp, 'cli-parametric');
runCli('parametric-demo', cliParametricDir);
assert(fs.existsSync(cliParametricDir), 'missing CLI parametric output directory');
const cliParametricReportPath = path.join(cliParametricDir, 'parametric_demo_report.json');
const cliParametricSummaryPath = path.join(cliParametricDir, 'parametric_demo_summary.txt');
assertFile(cliParametricReportPath, 'missing CLI parametric report');
assertFile(cliParametricSummaryPath, 'missing CLI parametric summary');
const cliParametricReport = readJson(cliParametricReportPath);
assertTrainingReport(cliParametricReport, 'CLI parametric demo');
assertSummaryContains(readText(cliParametricSummaryPath), [
  'initial_val_loss',
  'final_val_loss',
  'final_val_accuracy',
]);

const cliImageDir = path.join(tmp, 'cli-image-parametric');
runCli('image-parametric-demo', cliImageDir);
assert(fs.existsSync(cliImageDir), 'missing CLI image parametric output directory');
const cliImageReportPath = path.join(cliImageDir, 'image_parametric_report.json');
const cliImageSummaryPath = path.join(cliImageDir, 'image_parametric_summary.txt');
assertFile(cliImageReportPath, 'missing CLI image parametric report');
assertFile(cliImageSummaryPath, 'missing CLI image parametric summary');
const cliImageReport = readJson(cliImageReportPath);
assertTrainingReport(cliImageReport, 'CLI image parametric demo');
assertNumberField(cliImageReport, 'finalValScoreCorrelation');
assertSummaryContains(readText(cliImageSummaryPath), [
  'initial_val_loss',
  'final_val_loss',
  'final_val_accuracy',
  'final_val_score_correlation',
]);

console.log('OK portable text metrics smoke');
