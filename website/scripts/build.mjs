import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const root = path.resolve(import.meta.dirname, '..');
const repo = path.resolve(root, '..');
const track = path.join(repo, 'tracks/ai-field-engineer');
const web = path.join(root, 'ai-field-engineer');
const output = path.join(root, 'dist');
const dest = path.join(output, 'ai-field-engineer');
const prefix = '/ai-field-engineer';
const harnessWeb = path.join(root, 'agent-harness-from-scratch');
const run = (cmd, args, cwd) => execFileSync(cmd, args, {
  cwd, stdio: 'inherit', env: { ...process.env, ASTRO_TELEMETRY_DISABLED: '1', STRICT: '1' },
});

if (!fs.existsSync(path.join(web, 'node_modules'))) run('npm', ['ci', '--no-audit', '--no-fund'], web);
run('node', ['scripts/sync.mjs'], web);
run(path.join(web, 'node_modules/.bin/astro'), ['build'], web);
run('node', ['scripts/search-index.mjs'], web);

fs.rmSync(output, { recursive: true, force: true });
fs.mkdirSync(output, { recursive: true });
fs.cpSync(path.join(web, 'dist'), dest, { recursive: true });
// Each course keeps its canonical learning source in tracks/. The harness sync reads
// that source without running its labs or making provider calls.
if (!fs.existsSync(path.join(harnessWeb, 'node_modules'))) run('npm', ['ci', '--no-audit', '--no-fund'], harnessWeb);
run('npm', ['run', 'build'], harnessWeb);
fs.cpSync(path.join(harnessWeb, 'dist'), path.join(output, 'agent-harness-from-scratch'), { recursive: true });
fs.mkdirSync(path.join(dest, 'media/videos'), { recursive: true });
fs.mkdirSync(path.join(dest, 'media/posters'), { recursive: true });
for (const file of fs.readdirSync(path.join(track, '01-videos')).filter(f => f.endsWith('.mp4'))) {
  const source = path.join(track, '01-videos', file);
  if (fs.statSync(source).size > 25 * 1024 * 1024) throw new Error(`${file} exceeds Cloudflare's 25 MiB asset limit`);
  fs.copyFileSync(source, path.join(dest, 'media/videos', file));
  const poster = path.join(track, 'assets/posters', file.replace(/\.mp4$/, '.jpg'));
  if (!fs.existsSync(poster)) throw new Error(`Missing poster ${poster}; run npm run posters`);
  fs.copyFileSync(poster, path.join(dest, 'media/posters', path.basename(poster)));
}

// Astro prefixes its own links. Course-authored links and the progress spine are root-relative in the
// original standalone kit, so scope those to this track when assembling the multi-track site.
const rootUrl = /\b(href|src|poster|action)=(['"])\/(?!\/|ai-field-engineer(?:\/|\2))/g;
const fromUrl = /([?&]from=)\/(?!ai-field-engineer\/)/g;
const walk = (dir) => {
  for (const item of fs.readdirSync(dir, { withFileTypes: true })) {
    const file = path.join(dir, item.name);
    if (item.isDirectory()) walk(file);
    else if (item.name.endsWith('.html')) {
      const html = fs.readFileSync(file, 'utf8')
        .replace(rootUrl, (_, attr, quote) => `${attr}=${quote}${prefix}/`)
        .replace(fromUrl, (_, start) => `${start}${prefix}/`);
      fs.writeFileSync(file, html);
    }
  }
};
walk(dest);

const spineFile = path.join(dest, 'kit-spine.js');
const spineSource = fs.readFileSync(spineFile, 'utf8');
const match = spineSource.match(/window\.KIT_SPINE\s*=\s*(\[[\s\S]*\]);/);
if (!match) throw new Error('Could not find the course spine');
const spine = JSON.parse(match[1]);
for (const page of spine) page.r = prefix + page.r;
fs.writeFileSync(spineFile, spineSource.replace(match[1], JSON.stringify(spine)));

const landing = `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>The Local Node — learn by building</title><meta name="description" content="Open learning materials for people who build and explain technology."><style>body{margin:0;background:#101d30;color:#f8f3e9;font:18px/1.5 system-ui,sans-serif}main{max-width:1050px;margin:auto;padding:5rem 1.5rem}h1{font-size:clamp(3rem,8vw,6rem);line-height:1;letter-spacing:-.055em;margin:0 0 1rem}p{max-width:48rem;color:#c7d2df}a{color:inherit}.card{display:block;max-width:40rem;margin-top:3.5rem;padding:2rem;border:1px solid #62768e;border-radius:18px;text-decoration:none}.card:hover,.card:focus-visible{border-color:#eea168;background:#172b44}.card strong{display:block;font-size:1.65rem}.card span{color:#c7d2df}small{display:block;margin-top:3rem;color:#9eb0c5}</style><main><p>THE LOCAL NODE</p><h1>Learn by building.</h1><p>Practical, open learning tracks with lessons, working code, and the reasoning behind each step.</p><a class="card" href="/ai-field-engineer/"><strong>AI Field Engineer →</strong><span>Start with model serving, measurement, evaluation, and real customer problems.</span></a><a class="card" href="/agent-harness-from-scratch/"><strong>Agent Harness from Scratch →</strong><span>Build one Python harness across coding, synthetic SRE, and resident automation. Optional foundations and 32 progressive lessons, including four optional extensions; offline by default. Course in progress; validation pending.</span></a><small>Open learning materials, built in public. <a href="https://github.com/maruthiprithivi/the-local-node">Browse the source on GitHub</a>.</small></main></html>`;
fs.writeFileSync(path.join(output, 'index.html'), landing);
fs.writeFileSync(path.join(output, '404.html'), '<!doctype html><title>Page not found · The Local Node</title><main><h1>Page not found</h1><p><a href="/">Back to The Local Node</a></p></main>');

const errors = [];
walkLinks(output, errors);
if (errors.length) throw new Error(`Broken local links (${errors.length}):\n${errors.slice(0, 20).join('\n')}`);
console.log(`Built The Local Node: ${spine.length} course stops, ${fs.readdirSync(path.join(dest, 'media/videos')).length} videos`);

function walkLinks(dir, errors) {
  for (const item of fs.readdirSync(dir, { withFileTypes: true })) {
    const file = path.join(dir, item.name);
    if (item.isDirectory()) walkLinks(file, errors);
    else if (item.name.endsWith('.html')) {
      const html = fs.readFileSync(file, 'utf8');
      for (const [, href] of html.matchAll(/\bhref="(\/[^"]*)"/g)) {
        const url = href.split(/[?#]/)[0];
        const target = path.join(output, decodeURIComponent(url));
        if (!fs.existsSync(target) && !fs.existsSync(target + '.html') && !fs.existsSync(path.join(target, 'index.html'))) {
          errors.push(`${path.relative(output, file)} → ${href}`);
        }
      }
    }
  }
}
