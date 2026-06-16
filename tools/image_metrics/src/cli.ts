declare const require: any;
declare const process: any;
declare const module: any;
const fs = require('fs');
const path = require('path');
import { analyzeImageToDir, backendVersion, supportedExtensions, stochasticUpdateToDir } from './native';
import { convnetDistortionToDir } from './convnet';
import { fitTransformToDir } from './fit_transform';
import { segmentImageToDir, importLabelsToDir, trainPatchClassifierToDir, segmentPredictToDir, buildTargetsToDir, matchFeatureToDir } from './annotation';
import { cartoonifyOptimizeToDir } from './cartoonify_optimizer';
import { deepCartoonifyToDir } from './deep_cartoonify';
import { cartoonStyleProfileToDir, cartoonNegativeProfileToDir, styleConditionedCartoonifyToDir } from './style_conditioned_cartoonify';
function usage(): string { return [
  'Usage:',
  '  image-metrics version',
  '  image-metrics extensions',
  '  image-metrics analyze <image> --out <dir>',
  '  image-metrics stochastic-update <image> --out <dir> [--seed n] [--trials n] [--support n] [--step x]',
  '  image-metrics convnet-distortion <image> --out <dir> [--seed n] [--shallow-strength x] [--deep-strength x]',
  '  image-metrics fit-transform <source> <target> --out <dir> [--seed n] [--trials n] [--smoothness-weight x] [--edge-weight x] [--complexity-weight x]',
  '  image-metrics segment <image> --out <dir> [--image-id id] [--grid n]',
  '  image-metrics import-labels <run-dir> <labels.json> [--source-tool name]',
  '  image-metrics train-patch-classifier <dataset-dir> --out <model-dir>',
  '  image-metrics segment-predict <image> <model.json> --out <dir> [--grid n]',
  '  image-metrics build-targets <dataset-dir> --out <dir> --feature name --label label',
  '  image-metrics match-feature <image> <target_features.json> --out <dir> --feature name [--label label] [--strength x]',
  '  image-metrics cartoonify-optimize <image> --out <dir> [--seed n] [--layers n] [--grid n] [--tries n] [--metric cartoon]',
  '  image-metrics deep-cartoonify <image> --out <dir> [--seed n] [--depth n] [--trials n] [--patience n] [--threshold x] [--metric cartoon]',
  '  image-metrics cartoon-style-profile <target> --out <dir> [--source image]',
  '  image-metrics cartoon-negative-profile <clean> <distorted> --out <dir>',
  '  image-metrics style-conditioned-cartoonify <image> <style_profile.json> --out <dir> [--negative-profile negative_profile.json] [--seed n] [--layers n] [--trials n] [--strength x]',
  '  image-metrics image-parametric-demo --out <dir> [images...]'
].join('\n'); }
function argValue(args: string[], name: string, fallback: string): string { const i = args.indexOf(name); return i >= 0 && args[i + 1] ? args[i + 1] : fallback; }
const VALUE_FLAGS = ['--out','--seed','--trials','--support','--step','--shallow-strength','--deep-strength','--smoothness-weight','--edge-weight','--complexity-weight','--grid','--image-id','--source-tool','--feature','--label','--strength','--layers','--tries','--metric','--depth','--patience','--threshold','--source','--negative-profile'];
function positional(args: string[], start = 1): string[] { const out: string[] = []; for (let i = start; i < args.length; i++) { if (VALUE_FLAGS.includes(args[i])) { i++; continue; } if (!args[i].startsWith('--')) out.push(args[i]); } return out; }
function runParametric(outDir: string, images: string[]): any { fs.mkdirSync(outDir, { recursive: true }); const paths = images.length ? images : ['synthetic://a','synthetic://b']; const records = paths.map((p, i) => ({ path: p, report: analyzeImageToDir({ imagePath: p, outDir: path.join(outDir, `analysis_${i}`) }) })); const result = { mode: 'image-parametric-demo', backend: backendVersion(), imagePaths: records.map(r => r.path), nativeScores: records.map(r => Number((r.report as any).score || 0)), capabilityNote: 'feature extraction and parametric image metric smoke path' }; fs.writeFileSync(path.join(outDir, 'image_parametric_report.json'), JSON.stringify(result, null, 2)); fs.writeFileSync(path.join(outDir, 'image_parametric_summary.txt'), `backend: ${result.backend}\nimages: ${result.imagePaths.length}\n`); return result; }
export function runCli(args: string[]): number {
  try {
    const command = args[0];
    if (!command) { console.log(usage()); return 1; }
    if (command === 'version') { console.log(backendVersion()); return 0; }
    if (command === 'extensions') { console.log(supportedExtensions()); return 0; }
    if (command === 'analyze') { const xs = positional(args,1); if (!xs.length) throw new Error('analyze requires an image path'); console.log(JSON.stringify(analyzeImageToDir({ imagePath: xs[0], outDir: argValue(args,'--out','runs/image-analyze') }), null, 2)); return 0; }
    if (command === 'stochastic-update') { const xs = positional(args,1); if (!xs.length) throw new Error('stochastic-update requires an image path'); console.log(JSON.stringify(stochasticUpdateToDir({ imagePath: xs[0], outDir: argValue(args,'--out','runs/stochastic-update'), seed: Number(argValue(args,'--seed','20260615')), trials: Number(argValue(args,'--trials','96')), support: Number(argValue(args,'--support','24')), step: Number(argValue(args,'--step','0.020')) }), null, 2)); return 0; }
    if (command === 'convnet-distortion') { const xs = positional(args,1); if (!xs.length) throw new Error('convnet-distortion requires an image path'); console.log(JSON.stringify(convnetDistortionToDir({ imagePath: xs[0], outDir: argValue(args,'--out','runs/convnet-distortion'), seed: Number(argValue(args,'--seed','20260615')), shallowStrength: Number(argValue(args,'--shallow-strength','0.75')), deepStrength: Number(argValue(args,'--deep-strength','1.35')) }), null, 2)); return 0; }
    if (command === 'fit-transform') { const xs = positional(args,1); if (xs.length < 2) throw new Error('fit-transform requires source and target image paths'); console.log(JSON.stringify(fitTransformToDir({ sourcePath: xs[0], targetPath: xs[1], outDir: argValue(args,'--out','runs/fit-transform'), seed: Number(argValue(args,'--seed','20260616')), trials: Number(argValue(args,'--trials','192')), smoothnessWeight: Number(argValue(args,'--smoothness-weight','0.00')), edgeWeight: Number(argValue(args,'--edge-weight','0.15')), complexityWeight: Number(argValue(args,'--complexity-weight','0.04')) }), null, 2)); return 0; }
    if (command === 'segment') { const xs = positional(args,1); if (!xs.length) throw new Error('segment requires an image path'); console.log(JSON.stringify(segmentImageToDir(xs[0], argValue(args,'--out','runs/segment'), argValue(args,'--image-id',path.basename(xs[0])), Number(argValue(args,'--grid','10'))), null, 2)); return 0; }
    if (command === 'import-labels') { const xs = positional(args,1); if (xs.length < 2) throw new Error('import-labels requires run-dir and labels.json'); console.log(JSON.stringify(importLabelsToDir(xs[0], xs[1], argValue(args,'--source-tool','external_annotation_tool')), null, 2)); return 0; }
    if (command === 'train-patch-classifier') { const xs = positional(args,1); if (!xs.length) throw new Error('train-patch-classifier requires dataset-dir'); console.log(JSON.stringify(trainPatchClassifierToDir(xs[0], argValue(args,'--out','runs/patch-classifier')), null, 2)); return 0; }
    if (command === 'segment-predict') { const xs = positional(args,1); if (xs.length < 2) throw new Error('segment-predict requires image and model.json'); console.log(JSON.stringify(segmentPredictToDir(xs[0], xs[1], argValue(args,'--out','runs/segment-predict'), Number(argValue(args,'--grid','10'))), null, 2)); return 0; }
    if (command === 'build-targets') { const xs = positional(args,1); if (!xs.length) throw new Error('build-targets requires dataset-dir'); console.log(JSON.stringify(buildTargetsToDir(xs[0], argValue(args,'--out','runs/targets'), argValue(args,'--feature','skin_shade'), argValue(args,'--label','skin')), null, 2)); return 0; }
    if (command === 'match-feature') { const xs = positional(args,1); if (xs.length < 2) throw new Error('match-feature requires image and target_features.json'); console.log(JSON.stringify(matchFeatureToDir(xs[0], xs[1], argValue(args,'--feature','skin_shade'), argValue(args,'--out','runs/match-feature'), argValue(args,'--label','skin'), Number(argValue(args,'--strength','0.75'))), null, 2)); return 0; }
    if (command === 'cartoonify-optimize') { const xs = positional(args,1); if (!xs.length) throw new Error('cartoonify-optimize requires an image path'); console.log(JSON.stringify(cartoonifyOptimizeToDir({ imagePath: xs[0], outDir: argValue(args,'--out','runs/cartoonify-optimize'), seed: Number(argValue(args,'--seed','20260616')), layers: Number(argValue(args,'--layers','3')), grid: Number(argValue(args,'--grid','8')), tries: Number(argValue(args,'--tries','12')), metric: argValue(args,'--metric','cartoon') }), null, 2)); return 0; }
    if (command === 'deep-cartoonify') { const xs = positional(args,1); if (!xs.length) throw new Error('deep-cartoonify requires an image path'); console.log(JSON.stringify(deepCartoonifyToDir({ imagePath: xs[0], outDir: argValue(args,'--out','runs/deep-cartoonify'), seed: Number(argValue(args,'--seed','20260616')), depth: Number(argValue(args,'--depth','5')), trials: Number(argValue(args,'--trials','8')), patience: Number(argValue(args,'--patience','3')), threshold: Number(argValue(args,'--threshold','0.001')), metric: argValue(args,'--metric','cartoon') }), null, 2)); return 0; }
    if (command === 'cartoon-style-profile') { const xs = positional(args,1); if (!xs.length) throw new Error('cartoon-style-profile requires a target image'); const src = argValue(args,'--source',''); console.log(JSON.stringify(cartoonStyleProfileToDir({ targetPath: xs[0], sourcePath: src || undefined, outDir: argValue(args,'--out','runs/cartoon-style-profile') }), null, 2)); return 0; }
    if (command === 'cartoon-negative-profile') { const xs = positional(args,1); if (xs.length < 2) throw new Error('cartoon-negative-profile requires clean and distorted image paths'); console.log(JSON.stringify(cartoonNegativeProfileToDir({ cleanPath: xs[0], distortedPath: xs[1], outDir: argValue(args,'--out','runs/cartoon-negative-profile') }), null, 2)); return 0; }
    if (command === 'style-conditioned-cartoonify') { const xs = positional(args,1); if (xs.length < 2) throw new Error('style-conditioned-cartoonify requires image and style_profile.json'); const neg = argValue(args,'--negative-profile',''); console.log(JSON.stringify(styleConditionedCartoonifyToDir({ imagePath: xs[0], styleProfilePath: xs[1], negativeProfilePath: neg || undefined, outDir: argValue(args,'--out','runs/style-conditioned-cartoonify'), seed: Number(argValue(args,'--seed','20260616')), layers: Number(argValue(args,'--layers','3')), trials: Number(argValue(args,'--trials','8')), strength: Number(argValue(args,'--strength','0.75')) }), null, 2)); return 0; }
    if (command === 'image-parametric-demo') { console.log(JSON.stringify(runParametric(argValue(args,'--out','runs/image-parametric-demo'), positional(args,1)), null, 2)); return 0; }
    console.error(usage()); return 1;
  } catch (err) { console.error(err instanceof Error ? err.message : String(err)); return 1; }
}
if (typeof require !== 'undefined' && require.main === module) process.exit(runCli(process.argv.slice(2)));
