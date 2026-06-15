declare const __dirname: string;
declare const require: any;
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..', '..', '..', '..');
const manifestPath = path.join(repoRoot, 'examples', 'gizmos', 'metrics.gizmo.json');
assert(fs.existsSync(manifestPath), 'expected examples/gizmos/metrics.gizmo.json to exist');

const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
assert.strictEqual(manifest.format, 'LS_GIZMO_V1');
assert.strictEqual(manifest.name, 'metrics');

const textMetrics = manifest.gadgets['text-metrics'];
assert(textMetrics, 'expected text-metrics gadget declaration');
assert.strictEqual(textMetrics.root, 'tools/text_metrics');
assert.strictEqual(textMetrics.language, 'typescript');
assert.strictEqual(textMetrics.target_ref, 'origin/gadgets/metrics/text-metrics/main');
assert.strictEqual(textMetrics.integration_branch, 'gadgets/metrics/text-metrics/main');
assert.strictEqual(textMetrics.agent_branch_template, 'gadget-agents/metrics/text-metrics/{agent}');
assert(textMetrics.owned_paths.includes('tools/text_metrics/'), 'expected text-metrics to own tools/text_metrics/');
assert(textMetrics.owned_paths.includes('examples/gizmos/metrics.gizmo.json'), 'expected text-metrics to own the metrics manifest');
assert.deepStrictEqual(textMetrics.verification_profiles.quick, ['cd tools/text_metrics && npm install', 'cd tools/text_metrics && npm run build']);
assert.deepStrictEqual(textMetrics.verification_profiles.full, ['cd tools_text_metrics && npm install'.replace('tools_text_metrics', 'tools/text_metrics'), 'cd tools/text_metrics && npm test']);

assert.strictEqual(textMetrics.commands.analyze, 'cd tools/text_metrics && node dist/src/cli.js analyze {file} --out {out}');
assert.strictEqual(textMetrics.commands.compare, 'cd tools/text_metrics && node dist/src/cli.js compare {file_a} {file_b} --out {out}');
assert.strictEqual(textMetrics.commands['analyze-bundle'], 'cd tools/text_metrics && node dist/src/cli.js analyze-bundle {bundle} --out {out}');

const imageMetrics = manifest.gadgets['image-metrics'];
assert(imageMetrics, 'expected image-metrics gadget declaration');
assert.strictEqual(imageMetrics.commands.analyze, 'image-metrics.bat analyze {image} --out {out}');
assert.strictEqual(imageMetrics.commands['image-parametric-demo'], 'image-metrics.bat image-parametric-demo --out {out} {images}');

const connection = manifest.connections.find((item: any) => item.from === 'text-metrics' && item.to === 'image-metrics');
assert(connection, 'expected text-metrics to image-metrics connection');
assert.strictEqual(connection.via, 'declared-artifacts');
assert(connection.allowed_reads.includes('report.json'), 'expected report.json allowed read');
assert(connection.allowed_reads.includes('feature_fixture.json'), 'expected feature_fixture.json allowed read');
assert(connection.allowed_reads.includes('image_parametric_report.json'), 'expected image_parametric_report.json allowed read');
assert(connection.allowed_commands.includes('analyze'), 'expected analyze allowed command');
assert(connection.allowed_commands.includes('image-parametric-demo'), 'expected image-parametric-demo allowed command');

const toolchain = manifest.imports['lambdascript-core'];
assert(toolchain, 'expected lambdascript-core import');
assert.strictEqual(toolchain.from_gizmo, 'lambdascript');
assert.strictEqual(toolchain.from_gadget, 'core');
assert.strictEqual(toolchain.mount, 'toolchains/lambdascript');
assert.strictEqual(toolchain.mode, 'read-only');
assert.strictEqual(toolchain.write_policy, 'deny');
assert(toolchain.allowed_commands.includes('forks'), 'expected forks command import');
assert(toolchain.allowed_commands.includes('glc'), 'expected glc command import');
assert(toolchain.allowed_commands.includes('gizmo'), 'expected gizmo command import');

console.log('OK text metrics manifest wiring');
