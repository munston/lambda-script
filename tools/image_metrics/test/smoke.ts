declare const require: any; declare const process: any; declare const __dirname: string;
const fs = require('fs'); const path = require('path'); const cp = require('child_process'); const root=path.resolve(__dirname,'..','..');
function run(args:string[]):void{const p=cp.spawnSync(process.execPath,args,{cwd:root,encoding:'utf-8'}); process.stdout.write(p.stdout||''); process.stderr.write(p.stderr||''); if(p.status!==0)throw new Error(`command failed: ${args.join(' ')}`);}
function assertFile(p:string):void{if(!fs.existsSync(p)||fs.statSync(p).size<=0)throw new Error(`missing or empty file: ${p}`);}
const out=path.join(root,'runs','smoke-image-metrics'); fs.rmSync(out,{recursive:true,force:true});
run(['dist/src/cli.js','version']);
run(['dist/src/cli.js','analyze','synthetic://smoke-a','--out',path.join(out,'analyze')]); assertFile(path.join(out,'analyze','report.json')); assertFile(path.join(out,'analyze','feature_fixture.json'));
run(['dist/src/cli.js','image-parametric-demo','--out',path.join(out,'parametric'),'synthetic://smoke-a','synthetic://smoke-b']); assertFile(path.join(out,'parametric','image_parametric_report.json'));
run(['dist/src/cli.js','stochastic-update','synthetic://smoke-a','--out',path.join(out,'update'),'--trials','16','--support','8','--step','0.018']); assertFile(path.join(out,'update','updated.ppm')); assertFile(path.join(out,'update','update_trace.json')); assertFile(path.join(out,'update','support_dictionary.json'));
console.log('image-metrics sparse Gaussian update smoke passed');
