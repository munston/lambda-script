declare const require: any;
const fs = require('fs');
const path = require('path');
const os = require('os');
const child = require('child_process');

import { computeTextMetric } from './metrics';
import { ensureDir, writeHighlighted, writeJson, writeReport } from './render';
import { TextMetricResult } from './types';

export interface BundleInput {
  sourcePath: string;
  workingDir: string;
  extracted: boolean;
  imagePath: string;
  captionPath: string;
  promptPath?: string;
}

export interface BundleAnalysisSummary {
  manifest: {
    sourcePath: string;
    workingDir: string;
    extracted: boolean;
    imageFile: string;
    captionFile: string;
    promptFile?: string;
    acceptedAt: string;
    imageBytes: number;
    captionChars: number;
    promptChars?: number;
  };
  captionScore: number;
  promptScore?: number;
  combinedScore: number;
}

function isDirectory(p: string): boolean {
  return fs.existsSync(p) && fs.statSync(p).isDirectory();
}

function isFile(p: string): boolean {
  return fs.existsSync(p) && fs.statSync(p).isFile();
}

function isTarball(p: string): boolean {
  const lower = p.toLowerCase();
  return lower.endsWith('.tar') || lower.endsWith('.tar.gz') || lower.endsWith('.tgz');
}

function collectFilesRec(dir: string): string[] {
  const out: string[] = [];
  for (const entry of fs.readdirSync(dir)) {
    const full = path.join(dir, entry);
    const stat = fs.statSync(full);
    if (stat.isDirectory()) out.push(...collectFilesRec(full));
    else if (stat.isFile()) out.push(full);
  }
  return out;
}

function baseNameNoExt(p: string): string {
  const b = path.basename(p).toLowerCase();
  if (b.endsWith('.tar.gz')) return b.slice(0, -7);
  return b.replace(/\.[^.]+$/, '');
}

function chooseImage(files: string[]): string {
  const images = files.filter(f => ['.png', '.jpg', '.jpeg', '.webp'].includes(path.extname(f).toLowerCase()));
  if (images.length !== 1) throw new Error(`expected exactly one image in bundle, found ${images.length}`);
  return images[0];
}

function choosePrompt(files: string[]): string | undefined {
  const textFiles = files.filter(f => ['.txt', '.md'].includes(path.extname(f).toLowerCase()));
  const direct = textFiles.find(f => /(^|[._ -])(initial_?prompt|prompt)([._ -]|$)/i.test(path.basename(f)));
  return direct;
}

function chooseCaption(files: string[], promptPath?: string): string {
  const textFiles = files.filter(f => ['.txt', '.md'].includes(path.extname(f).toLowerCase()));
  const withoutPrompt = textFiles.filter(f => f !== promptPath);
  const direct = withoutPrompt.find(f => /(^|[._ -])(caption|annotation)([._ -]|$)/i.test(path.basename(f)));
  if (direct) return direct;
  if (withoutPrompt.length === 1) return withoutPrompt[0];
  throw new Error(`expected exactly one caption/annotation text file in bundle, found ${withoutPrompt.length}`);
}

function extractTarball(tarballPath: string): string {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lambda-text-metrics-'));
  child.execFileSync('tar', ['-xf', tarballPath, '-C', tempDir]);
  return tempDir;
}

export function loadBundle(inputPath: string): BundleInput {
  if (!isDirectory(inputPath) && !isFile(inputPath)) throw new Error(`bundle path not found: ${inputPath}`);
  let workingDir = inputPath;
  let extracted = false;
  if (isFile(inputPath)) {
    if (!isTarball(inputPath)) throw new Error('bundle file must be a .tar, .tar.gz, or .tgz archive');
    workingDir = extractTarball(inputPath);
    extracted = true;
  }
  const files = collectFilesRec(workingDir);
  const imagePath = chooseImage(files);
  const promptPath = choosePrompt(files);
  const captionPath = chooseCaption(files, promptPath);
  return { sourcePath: inputPath, workingDir, extracted, imagePath, captionPath, promptPath };
}

function readText(file: string): string {
  return fs.readFileSync(file, 'utf8');
}

function analyzeTextToDir(text: string, out: string): TextMetricResult {
  const result = computeTextMetric(text);
  writeReport(out, result);
  writeHighlighted(out, text, result);
  return result;
}

function writeBundleSummary(out: string, summary: BundleAnalysisSummary): void {
  const lines = [
    `source: ${summary.manifest.sourcePath}`,
    `image: ${summary.manifest.imageFile}`,
    `caption: ${summary.manifest.captionFile}`,
    `prompt: ${summary.manifest.promptFile ?? 'none'}`,
    `caption_score: ${summary.captionScore}`,
    `prompt_score: ${summary.promptScore ?? 'n/a'}`,
    `combined_score: ${summary.combinedScore}`,
  ];
  fs.writeFileSync(path.join(out, 'bundle_summary.txt'), lines.join('\n') + '\n');
}

export function analyzeBundleInput(inputPath: string, out: string): BundleAnalysisSummary {
  const bundle = loadBundle(inputPath);
  ensureDir(out);

  const imageExt = path.extname(bundle.imagePath).toLowerCase();
  const imageOut = path.join(out, `image${imageExt}`);
  const captionOut = path.join(out, 'caption.txt');
  const promptOut = path.join(out, 'prompt.txt');
  fs.copyFileSync(bundle.imagePath, imageOut);
  fs.copyFileSync(bundle.captionPath, captionOut);
  if (bundle.promptPath) fs.copyFileSync(bundle.promptPath, promptOut);

  const captionText = readText(bundle.captionPath);
  const promptText = bundle.promptPath ? readText(bundle.promptPath) : undefined;
  const captionResult = analyzeTextToDir(captionText, path.join(out, 'caption_analysis'));
  const promptResult = promptText ? analyzeTextToDir(promptText, path.join(out, 'prompt_analysis')) : undefined;
  const combinedText = promptText ? `${promptText}\n\n${captionText}` : captionText;
  const combinedResult = analyzeTextToDir(combinedText, path.join(out, 'combined_analysis'));

  const manifest = {
    sourcePath: bundle.sourcePath,
    workingDir: bundle.extracted ? baseNameNoExt(bundle.sourcePath) : bundle.workingDir,
    extracted: bundle.extracted,
    imageFile: path.basename(bundle.imagePath),
    captionFile: path.basename(bundle.captionPath),
    promptFile: bundle.promptPath ? path.basename(bundle.promptPath) : undefined,
    acceptedAt: new Date().toISOString(),
    imageBytes: fs.statSync(bundle.imagePath).size,
    captionChars: captionText.length,
    promptChars: promptText ? promptText.length : undefined,
  };
  const summary: BundleAnalysisSummary = {
    manifest,
    captionScore: captionResult.score,
    promptScore: promptResult?.score,
    combinedScore: combinedResult.score,
  };
  writeJson(path.join(out, 'bundle_manifest.json'), manifest);
  writeJson(path.join(out, 'bundle_report.json'), summary);
  writeBundleSummary(out, summary);
  return summary;
}
