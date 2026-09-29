// Build-time content sync: reads the kit (read-only) and the course data (course/course.yaml, the day
// content files, chapters.txt) and writes the Starlight pages, the sidebar, the course spine for kit.js,
// the code zip and the lab book copies the web server publishes. Run from website/ai-field-engineer before `astro build`.
//   node scripts/sync.mjs            (KIT_DIR=/path/to/kit to override, STRICT=1 fails on warnings)
// The guided course (docs/course-spec.md): scripts/course.mjs builds the model, scripts/course-pages.mjs
// turns it into page bodies, and this file decides where each page goes and what links to what.
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { zipSync } from 'fflate';
import { loadCourse, validateCourse } from './course.mjs';
import * as P from './course-pages.mjs';

const WEB = path.resolve(import.meta.dirname, '..');
const KIT = path.resolve(process.env.KIT_DIR ?? path.join(WEB, '../../tracks/ai-field-engineer'));
const DOCS = path.join(WEB, 'src/content/docs');
const GEN = path.join(WEB, 'src/generated');
const LABBOOK_OUT = path.join(WEB, 'public/lab-book');
const SPINE_OUT = path.join(WEB, 'public/kit-spine.js');
const DOWNLOADS_OUT = path.join(WEB, 'public/downloads');
const KIT_README_ROUTE = '/reference/kit-readme/'; // the kit README (the old home page) lives in Reference
// STRICT=1 (the default in the image) fails the build on any warning; STRICT=0 or unset only prints them.
const STRICT = /^(1|true|yes)$/i.test(process.env.STRICT ?? '');

const warnings = [];
const warn = (m) => warnings.push(m);
const skipped = [];
const abs = (rel) => path.join(KIT, rel);
const read = (rel) => fs.readFileSync(abs(rel), 'utf8').replace(/^﻿/, '').replace(/\r\n?/g, '\n');
const exists = (rel) => fs.existsSync(abs(rel));
const lineCount = (s) => (s === '' ? 0 : s.replace(/\n$/, '').split('\n').length);
const q = (s) => JSON.stringify(s); // JSON strings are valid YAML scalars
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
// Keeps _ and - apart so kv_calc.py and kv-calc.py get different ids; check-links fails on any duplicate.
const anchorFor = (file) => 'file-' + file.replace(/[^A-Za-z0-9_-]/g, '-');
const mb = (bytes) => (bytes / 1e6).toFixed(1) + ' MB';
const plain = (md) => md.replace(/[*`]/g, '').replace(/\s+/g, ' ').trim();

// ---------- which kit files get published ----------
// Only text source files are published. Honour every .gitignore in the kit, and on top of that never
// publish secrets or what the lessons generate next to their code (models, adapters, logs, run state),
// whether or not a .gitignore lists it. Skip binaries, very large files and symlinks.
const SKIP_DIRS = new Set(['.git', 'node_modules', '__pycache__', '.venv', '.astro', 'dist', 'out',
  'logs', 'adapters', 'fused', 'models', 'sft_model', 'checkpoints', 'bench', 'results', 'wandb', 'mlruns']);
const SECRET = /^(\.env(\..+)?|\.envrc|\.netrc|\.npmrc|\.pypirc|\.pgpass|credentials.*\.json|service-account.*\.json|.*\.(pem|key|p12|pfx|crt|jks|secret)|id_(rsa|ed25519|ecdsa)(\.pub)?)$/i;
const PUBLISHABLE = /(\.(py|sh|md|json|jsonl|toml|ya?ml|ts|tsx|js|mjs|cjs|txt|cfg|ini|csv)|^Makefile|^LICENSE|^\.gitignore|^\.gitkeep|^\.env\.example)$/;
const MAX_BYTES = 1_000_000;
// Credentials inside an otherwise normal-looking file (private keys, cloud and API tokens).
const SECRET_TEXT = /-----BEGIN [A-Z ]*PRIVATE KEY-----|\bAKIA[0-9A-Z]{16}\b|\bsk-[A-Za-z0-9_-]{20,}|\bgh[pousr]_[A-Za-z0-9]{30,}|\bxox[abpr]-[A-Za-z0-9-]{10,}|\bfw_[A-Za-z0-9]{20,}|\bAIza[0-9A-Za-z_-]{35}\b/;

// One .gitignore line -> a rule for kit-relative paths under `base` (the .gitignore's folder).
function ignoreRule(line, base) {
  let pat = line.trim();
  if (!pat || pat.startsWith('#')) return null;
  const negate = pat.startsWith('!');
  if (negate) pat = pat.slice(1);
  const dirOnly = pat.endsWith('/');
  pat = pat.replace(/\/+$/, '');
  const anchored = pat.includes('/');
  pat = pat.replace(/^\\(?=[#!])/, ''); // \# and \! are literal
  const body = pat.replace(/^\//, '').split(/(\*\*\/|\*\*|\*|\?|\[!?[^\]]+\])/).map((t) =>
    t === '**/' ? '(?:.*/)?' : t === '**' ? '.*' : t === '*' ? '[^/]*' : t === '?' ? '[^/]'
      : /^\[.*\]$/.test(t) ? t.replace(/^\[!/, '[^').replace(/\\/g, '\\\\')
      : t.replace(/[.+^${}()|[\]\\]/g, '\\$&')).join('');
  return { base, negate, dirOnly, re: new RegExp(`^${anchored ? '' : '(?:.*/)?'}${body}$`) };
}
const rulesIn = (dirRel) => {
  const gi = abs(path.posix.join(dirRel, '.gitignore'));
  return fs.existsSync(gi) ? fs.readFileSync(gi, 'utf8').split('\n').map((l) => ignoreRule(l, dirRel)).filter(Boolean) : [];
};
// Last matching rule wins, as in git. Paths inside an ignored folder never get here (walk skips the folder).
function ignored(rules, kitPath, isDir) {
  let hit = false;
  for (const r of rules) {
    if (r.base && !kitPath.startsWith(r.base + '/')) continue;
    if ((isDir || !r.dirOnly) && r.re.test(r.base ? kitPath.slice(r.base.length + 1) : kitPath)) hit = !r.negate;
  }
  return hit;
}

// Every publishable file under relDir (paths relative to relDir), sorted.
function walk(relDir) {
  const out = [];
  const parts = relDir.split('/');
  let inherited = [];
  for (let i = 0; i < parts.length; i++) inherited = inherited.concat(rulesIn(parts.slice(0, i).join('/')));
  const rec = (sub, rules) => {
    const dirRel = sub ? `${relDir}/${sub}` : relDir;
    rules = rules.concat(rulesIn(dirRel));
    for (const e of fs.readdirSync(abs(dirRel), { withFileTypes: true })) {
      const p = sub ? `${sub}/${e.name}` : e.name;
      const kitPath = `${relDir}/${p}`;
      if (e.isSymbolicLink()) { skipped.push(`${kitPath} (symlink)`); continue; }
      if (e.isDirectory()) {
        if (ignored(rules, kitPath, true)) continue;
        const generated = SKIP_DIRS.has(e.name) || e.name.endsWith('.egg-info') || fs.existsSync(abs(`${kitPath}/pyvenv.cfg`));
        if (generated) { if (!['.git', 'node_modules', '__pycache__'].includes(e.name)) skipped.push(`${kitPath}/ (generated or tooling folder)`); continue; }
        rec(p, rules);
        continue;
      }
      if (e.name === '.DS_Store' || !e.isFile() || ignored(rules, kitPath, false)) continue;
      const full = abs(kitPath);
      const why = SECRET.test(e.name) && e.name !== '.env.example' ? 'secret'
        : !PUBLISHABLE.test(e.name) ? 'not a text source file'
        : fs.statSync(full).size > MAX_BYTES ? 'larger than 1 MB'
        : fs.readFileSync(full).subarray(0, 8192).includes(0) ? 'binary' : null;
      if (why) { skipped.push(`${kitPath} (${why})`); continue; }
      if (SECRET_TEXT.test(fs.readFileSync(full, 'utf8'))) { warn(`${kitPath} looks like it contains a credential; not published`); continue; }
      out.push(p);
    }
  };
  rec('', inherited);
  return out.sort();
}

// ---------- kit README tables ----------
const readme = read('README.md');
function sectionOf(md, heading) {
  const at = md.indexOf(heading);
  if (at < 0) throw new Error(`README section not found: ${heading}`);
  const next = md.indexOf('\n## ', at + heading.length);
  return md.slice(at, next < 0 ? undefined : next);
}
function tableAfter(md, heading) {
  const rows = [];
  for (const line of sectionOf(md, heading).split('\n').slice(1)) {
    if (line.startsWith('|')) rows.push(line);
    else if (rows.length) break;
  }
  return rows.slice(2).map((r) => r.split('|').slice(1, -1).map((c) => c.trim()));
}
const unticked = (s) => s.replace(/`/g, '');

// ---------- videos ----------
const narration = JSON.parse(read('04-video-source/src/narration.json'));
const postersTxt = fs.readFileSync(path.join(WEB, 'posters.txt'), 'utf8');
const POSTER_AT = new Map(postersTxt.split('\n').filter((l) => l.trim() && !l.startsWith('#')).map((l) => l.trim().split(/\s+/)));
const POSTER_VERSION = crypto.createHash('sha1').update(postersTxt).digest('hex').slice(0, 8);
const videoVersion = (st) => (st ? `${st.size.toString(36)}${Math.round(st.mtimeMs).toString(36)}` : '0');
const videos = tableAfter(readme, '## The 18 videos').map(([num, file, min, what, runNext]) => {
  const fileName = unticked(file);
  const stem = fileName.replace(/\.mp4$/, '');
  const n = narration[stem.replace(/^\d\d-/, '')];
  if (!n) throw new Error(`narration.json has no entry for ${stem}`);
  const st = exists(`01-videos/${fileName}`) ? fs.statSync(abs(`01-videos/${fileName}`)) : null;
  if (!st) warn(`video file missing: 01-videos/${fileName}`);
  if (!POSTER_AT.has(stem)) warn(`posters.txt has no poster time for ${stem}`);
  return {
    num, fileName, stem, min, what, runNext, title: n.title, subtitle: n.subtitle, size: st?.size ?? 0,
    // Versioned media URLs: nginx caches /media/ for a week, so a changed file or poster needs a new URL.
    src: `/media/videos/${fileName}?v=${videoVersion(st)}`,
    poster: `/media/posters/${stem}.jpg?v=${POSTER_VERSION}-${videoVersion(st)}`,
    slug: `videos/${stem}`, route: `/videos/${stem}/`,
  };
});
for (const f of fs.readdirSync(abs('01-videos')).filter((f) => f.endsWith('.mp4'))) {
  if (!videos.some((v) => v.fileName === f)) warn(`01-videos/${f} is not in the README video table`);
}
const videoByFile = new Map(videos.map((v) => [v.fileName, v]));

// ---------- course days (which day each video / lesson belongs to) ----------
const course = [
  ...tableAfter(readme, '### Part 1:').map((r) => ({ part: 1, row: r })),
  ...tableAfter(readme, '### Part 2:').map((r) => ({ part: 2, row: r })),
].map(({ part, row: [day, watch, todo] }) => ({ part, day, watch, todo }));
const part2Lessons = new Set(
  course.filter((c) => c.part === 2).flatMap((c) => c.todo.match(/\d\d-[\w-]+/g) ?? [])
    .filter((d) => !course.some((c) => c.part === 1 && c.todo.includes(d))),
);

// ---------- lab book ----------
const LAB_BOOK = 'field-engineer-lab-book.html';
const labbook = fs.readdirSync(abs('02-lab-book')).filter((f) => f.endsWith('.html')).sort().map((f) => ({
  file: f,
  title: read(`02-lab-book/${f}`).match(/<title>([^<]+)<\/title>/i)?.[1]?.trim() ?? f,
  route: `/lab-book/${f}`,
}));
// Lab cards (F1..F7, L1..L9, T1..T3) are built by the page's script; the page opens one from #lab-XX.
const cardIds = new Set(exists(`02-lab-book/${LAB_BOOK}`)
  ? [...read(`02-lab-book/${LAB_BOOK}`).matchAll(/\{\s*id:\s*'([FLT]\d)'/g)].map((m) => m[1]) : []);

// ---------- lessons ----------
// The first "# " heading outside code fences is the page title: returns [title, body without that line].
function splitTitle(md) {
  const lines = md.split('\n');
  let fence = null;
  for (let i = 0; i < lines.length; i++) {
    const f = lines[i].match(/^\s*(`{3,}|~{3,})/);
    if (fence) { if (f && f[1][0] === fence[0] && f[1].length >= fence.length) fence = null; continue; }
    if (f) { fence = f[1]; continue; }
    const h = lines[i].match(/^# +(.+?)(?:[ \t]+#+)?[ \t]*$/);
    if (h) return [h[1], [...lines.slice(0, i), ...lines.slice(i + 1)].join('\n').replace(/^\n+/, '')];
  }
  return [null, md];
}
const lessonInfo = new Map(tableAfter(readme, '## The 19 lessons').map(([, folder, what, runsOn]) => [unticked(folder), { what, runsOn }]));
// Short sidebar labels: the link texts of the 03-labs README lessons table.
const shortLabel = new Map([...read('03-labs/README.md').matchAll(/^\| *(\d\d) *\| *\[([^\]]+)\]\(lessons\/([^/)]+)\/?\)/gm)].map((m) => [m[3], `${m[1]} · ${m[2]}`]));
const lessonRules = rulesIn('').concat(rulesIn('03-labs'), rulesIn('03-labs/lessons'));
const lessons = fs.readdirSync(abs('03-labs/lessons'), { withFileTypes: true }).filter((e) => {
  if (!/^\d\d-/.test(e.name)) return false;
  const rel = `03-labs/lessons/${e.name}`;
  if (!e.isDirectory() || ignored(lessonRules, rel, true)) { skipped.push(`${rel} (not a lesson folder)`); return false; }
  if (!exists(`${rel}/README.md`)) { warn(`${rel} has no README.md`); return false; }
  return true;
}).map((e) => e.name).sort().map((dir) => {
  const rel = `03-labs/lessons/${dir}`;
  const md = read(`${rel}/README.md`);
  const title = splitTitle(md)[0] ?? dir;
  const files = walk(rel).filter((f) => f !== 'README.md');
  if (!lessonInfo.has(dir)) warn(`lesson ${dir} is not in the README lessons table`);
  return {
    dir, rel, md, title, label: shortLabel.get(dir) ?? title.split(':')[0], files, info: lessonInfo.get(dir),
    slug: `lessons/${dir}`, route: `/lessons/${dir}/`, part: part2Lessons.has(dir) ? 2 : 1,
  };
});
const lessonByDir = new Map(lessons.map((l) => [l.dir, l]));
const lessonByNum = new Map(lessons.map((l) => [l.dir.slice(0, 2), l]));

// ---------- the course (course/course.yaml + course/content/day-NN.yaml + chapters.txt) ----------
// Content problems (docs/course-spec.md section 3) are warnings: STRICT builds fail on them.
const model = loadCourse({ KIT, WEB, lessons, videos, narration, cardIds, readme, read });
{
  const notes = [];
  for (const p of validateCourse(model, { warnings: notes })) warn(`course: ${p}`);
  for (const n of notes) console.log(`sync: course note: ${n}`);
}
const stepsOfLesson = new Map(); // lesson dir -> the course steps built on it (lesson 16 has two)
for (const s of model.steps) if (s.lesson) stepsOfLesson.set(s.lesson.dir, [...(stepsOfLesson.get(s.lesson.dir) ?? []), s]);
const ownsFile = (s, f) => !s.files || s.files.some((x) => x === f || x === path.posix.basename(f));
// The page that shows a lesson file: for a lesson split over several steps, the step whose `files` has it.
function lessonFileRoute(l, f) {
  const own = (stepsOfLesson.get(l.dir) ?? []).find((s) => ownsFile(s, f));
  return `${own?.route ?? l.route}#${anchorFor(f)}`;
}
for (const [dir, ss] of stepsOfLesson) {
  if (ss.length < 2) continue;
  for (const f of lessonByDir.get(dir).files) if (!ss.some((s) => ownsFile(s, f))) warn(`course: lessons/${dir}/${f} is on no page (the lesson is split and no step lists it in files)`);
}
for (const l of lessons) if (!stepsOfLesson.has(l.dir)) warn(`course: lesson ${l.dir} is not a course step; it keeps a plain page reached only from the lessons index`);

const spine = model.spine;
const SPINE_END = { link: '/', label: 'Back to the start' };

// ---------- toolkit (03-labs outside lessons) ----------
const LABS_SKIP = (f) => f.startsWith('lessons/') || f.startsWith('results/') || f === 'README.md' || f === 'lab-book.html';
const TOOLKIT_PAGES = [
  { slug: 'toolkit/felab', title: 'felab package', description: 'The shared helper package every lesson imports.', match: (f) => f.startsWith('felab/') },
  { slug: 'toolkit/data', title: 'Data and schema', description: 'The support-ticket dataset and the triage schema used by the eval and fine-tuning lessons. The .jsonl files show their first rows.', match: (f) => f.startsWith('data/') },
  { slug: 'toolkit/ci', title: 'Smoke test and CI', description: 'The end-to-end smoke test and the GitHub Actions workflow that runs it.', match: (f) => f.startsWith('scripts/') || f.startsWith('.github/') },
  { slug: 'toolkit/config', title: 'Makefile and config', description: 'Make targets, Python packaging, requirements and the environment template.', match: (f) => !f.includes('/') },
];
const labsAll = walk('03-labs'); // also what the code zip holds (section 5.9)
const labsFiles = labsAll.filter((f) => !LABS_SKIP(f));
for (const p of TOOLKIT_PAGES) p.files = labsFiles.filter((f) => p.match(f));
for (const f of labsFiles) if (!TOOLKIT_PAGES.some((p) => p.files.includes(f))) warn(`03-labs/${f} is not placed on any page`);
if (exists('03-labs/lab-book.html') && read('03-labs/lab-book.html') !== read(`02-lab-book/${LAB_BOOK}`)) {
  warn(`03-labs/lab-book.html differs from 02-lab-book/${LAB_BOOK} but only the latter is published`);
}
const toolkitRoute = new Map(TOOLKIT_PAGES.flatMap((p) => p.files.map((f) => [f, `/${p.slug}/#${anchorFor(f)}`])));

// ---------- video source (04-video-source) ----------
const VS_SKIP = new Set(['package-lock.json', 'README.md']);
const vsFiles = walk('04-video-source').filter((f) => !VS_SKIP.has(f));
const VS_PAGES = [
  { slug: 'video-source/narration', title: 'Narration script', description: 'Every scene of all 18 videos: the visual, its parameters and the narration text (src/narration.json).', match: (f) => f === 'src/narration.json' },
  { slug: 'video-source/visuals', title: 'Scene visuals', description: 'The React components that draw every scene (src/components/Visuals.tsx).', match: (f) => f === 'src/components/Visuals.tsx' },
  { slug: 'video-source/scripts', title: 'TTS and render scripts', description: 'Kokoro text-to-speech and the render loop.', match: (f) => f.startsWith('scripts/') },
  { slug: 'video-source/app', title: 'Remotion app', description: 'The compositions, scene timing, subtitles and project config.', match: () => true },
];
for (const p of VS_PAGES) {
  p.files = vsFiles.filter((f) => p.match(f) && !VS_PAGES.slice(0, VS_PAGES.indexOf(p)).some((o) => o.files.includes(f)));
}
const vsRoute = new Map(VS_PAGES.flatMap((p) => p.files.map((f) => [f, `/${p.slug}/#${anchorFor(f)}`])));

// Bare file names that are unique across the published kit (e.g. `test.jsonl`, `5_teardown.sh`) link to
// their block wherever they are mentioned.
const everyFile = [
  ...[...toolkitRoute].filter(([f]) => f.includes('/')),
  ...lessons.flatMap((l) => l.files.filter((f) => !f.endsWith('.md')).map((f) => [f, lessonFileRoute(l, f)])),
];
const baseCount = new Map();
for (const [f] of everyFile) baseCount.set(path.posix.basename(f), (baseCount.get(path.posix.basename(f)) ?? 0) + 1);
const uniqueToolkitBase = new Map(everyFile.filter(([f]) => baseCount.get(path.posix.basename(f)) === 1 && !/^(README\.md|__init__\.py)$/.test(path.posix.basename(f)))
  .map(([f, r]) => [path.posix.basename(f), r]));

// ---------- link rewriting ----------
// Map a kit path (as written in a README) to a site URL, or null when there is no page for it.
function routeFor(ref, ctx) {
  let p = ref.trim().replace(/^\.\//, '').replace(/^fireworks-field-engineer-kit\//, '');
  if (!p || /^[a-z]+:/i.test(p)) return null;
  if (/\s/.test(p)) {
    // `kv_calc.py --ctx 131072`, `measure.py → stream_once()`: link to the first token that names a file.
    for (const tok of p.split(/\s+/)) if (/[./]/.test(tok) && !/^\.+$/.test(tok)) { const r = routeFor(tok, ctx); if (r) return r; }
    return null;
  }
  if (p.startsWith('../')) {
    if (!ctx.srcDir) return null;
    p = path.posix.normalize(path.posix.join(ctx.srcDir, p));
    if (p.startsWith('..')) return null;
    if (p === 'README.md') return KIT_README_ROUTE;
  }
  p = p.replace(/\/+$/, '');
  if (p.includes('*')) { // `lessons/02-*/serve_mlx.sh`: link when exactly one published file matches
    const re = new RegExp(`^(?:03-labs/)?${p.replace(/^03-labs\//, '').split('*').map((t) => t.replace(/[.+?^${}()|[\]\\]/g, '\\$&')).join('[^/]*')}$`);
    const hits = lessons.flatMap((l) => l.files.map((f) => [`lessons/${l.dir}/${f}`, lessonFileRoute(l, f)])).filter(([f]) => re.test(f));
    return hits.length === 1 ? hits[0][1] : null;
  }
  const base = path.posix.basename(p);
  if (/^(01-videos\/)?\d\d-[\w-]+\.mp4$/.test(p)) return videoByFile.get(base)?.route ?? null;
  if (p === '01-videos') return '/videos/';
  const lb = labbook.find((b) => p === b.file || p === `02-lab-book/${b.file}`);
  if (lb) return lb.route;
  if (p === 'lab-book.html' || p === '03-labs/lab-book.html' || p === '02-lab-book') return `/lab-book/${LAB_BOOK}`;
  if (p === '03-labs/lessons' || p === 'lessons') return '/lessons/';
  const m = p.match(/^(?:03-labs\/)?(?:lessons\/)?(\d\d-[\w-]+)(?:\/(.+))?$/);
  if (m && lessonByDir.has(m[1]) && (p.includes('lessons/') || !m[2])) {
    const l = lessonByDir.get(m[1]);
    if (!m[2] || m[2] === 'README.md') return l.route;
    return l.files.includes(m[2]) ? lessonFileRoute(l, m[2]) : null;
  }
  if (ctx.files?.includes(p)) return `${ctx.route}#${anchorFor(p)}`;
  const labsRel = p.replace(/^03-labs\//, '');
  if (toolkitRoute.has(labsRel)) return toolkitRoute.get(labsRel);
  if (labsRel === 'felab') return '/toolkit/felab/';
  if (p === '03-labs' || p === '03-labs/README.md') return '/toolkit/';
  if (p === '04-video-source') return '/video-source/';
  const vsRel = p.replace(/^04-video-source\//, '');
  if (vsRoute.has(vsRel)) return vsRoute.get(vsRel);
  if (uniqueToolkitBase.has(p)) return uniqueToolkitBase.get(p);
  return null;
}

// Relative markdown link target -> site URL (null = no page; the link text is kept, the link dropped).
function hrefFor(href, ctx) {
  if (/^([a-z]+:|#|\/)/i.test(href)) return href;
  const [p, hash] = href.split('#');
  const resolved = path.posix.normalize(path.posix.join(ctx.srcDir, p));
  const r = resolved === 'README.md' ? KIT_README_ROUTE : routeFor(resolved, { ...ctx, srcDir: '' }) ?? routeFor(p, ctx);
  if (!r) { warn(`${ctx.src}: link target has no page: ${href}`); return null; }
  return hash ? `${r.split('#')[0]}#${hash}` : r;
}

const CODE_SPAN = /(?<!`)(`+)(?!`)([\s\S]*?[^`])\1(?!`)/g; // CommonMark: closes on a run of the same length
const MD_LINK = /(!?)\[([^\]]*)\]\(\s*(<[^>]*>|[^)\s]+)(\s+"[^"]*")?\s*\)/g;

function rewriteLine(line, ctx) {
  // 1. park code spans, so nothing inside them is treated as a link
  const codes = [];
  line = line.replace(CODE_SPAN, (all, ticks, code) => `\u0001${codes.push({ all, code: ticks.length > 1 ? code.trim() : code }) - 1}\u0001`);
  // 2. markdown links: fix relative targets, park the whole link
  const links = [];
  line = line.replace(MD_LINK, (all, bang, text, target, title = '') => {
    const href = target.replace(/^<|>$/g, '');
    if (bang || !/[./#]/.test(href)) return all; // images, and `a[i](x)` style text that only looks like a link
    const h = hrefFor(href, ctx);
    return h === null ? text : `\u0002${links.push(`[${text}](${h}${title})`) - 1}\u0002`;
  });
  // 3. inline code outside links that names a kit file or folder becomes a link to its page
  line = line.replace(/\u0001(\d+)\u0001/g, (_, i) => {
    const c = codes[Number(i)];
    const r = c.all.startsWith('``') ? null : routeFor(c.code, ctx);
    return r ? `[${c.all}](${r})` : c.all;
  });
  return line.replace(/\u0002(\d+)\u0002/g, (_, i) => links[Number(i)].replace(/\u0001(\d+)\u0001/g, (__, j) => codes[Number(j)].all));
}

// Table cells such as "L4 · L5", "L6 + F2" or "Capstone": link each lab card id to its card.
const linkCards = (line) => line
  .replace(/(^|[\s|·+(])([FLT]\d)(?=$|[\s|·+),])/g, (m, pre, id) => (cardIds.has(id) ? `${pre}[${id}](/lab-book/${LAB_BOOK}#lab-${id})` : m))
  .replace(/\| *Capstone *\|/g, `| [Capstone](/lab-book/${LAB_BOOK}#capstone) |`);

// Rewrite prose lines only: fenced code (also inside a blockquote) and indented code blocks are left as
// they are. demote pushes headings down so notes stay out of the page TOC.
const LIST_ITEM = /^\s*([-*+]|\d+[.)])\s/;
function rewrite(md, ctx, { demote = 0 } = {}) {
  let fence = null, fenceInQuote = false, prevBlank = true, inIndented = false, inList = false;
  return md.split('\n').map((line) => {
    const quoted = /^\s*>/.test(line);
    if (fence && fenceInQuote && !quoted) fence = null; // the blockquote ended, and its fence with it
    const f = line.replace(/^(\s*>)+ ?/, '').match(/^\s*(`{3,}|~{3,})(.*)$/);
    if (fence) {
      const close = fenceInQuote ? f : line.match(/^\s*(`{3,}|~{3,})(.*)$/); // `> ```` inside a plain fence is content
      if (close && close[1][0] === fence[0] && close[1].length >= fence.length && !close[2].trim()) fence = null;
      return line;
    }
    if (f) { fence = f[1]; fenceInQuote = quoted; return line; }
    const blank = !line.trim();
    const indented = /^( {4,}|\t)/.test(line);
    // An indented block after a blank line is code, unless it continues a list item.
    if (indented && !inList && (prevBlank || inIndented)) { inIndented = true; prevBlank = false; return line; }
    if (!blank) {
      inIndented = false;
      // a list stays open through lazy continuation lines; a new paragraph after a blank line closes it
      if (LIST_ITEM.test(line)) inList = true;
      else if (!indented && prevBlank) inList = false;
    }
    prevBlank = blank;
    if (ctx.cardTables && line.startsWith('|')) line = linkCards(line);
    if (demote) line = line.replace(/^(#{1,6}) /, (_, h) => '#'.repeat(Math.min(6, h.length + demote)) + ' ');
    return rewriteLine(line, ctx);
  }).join('\n');
}

// Lesson header "> **Lab book:** … **L5**  **Watch:** …  / > **Time:** …  **Cost:** …": the fields are
// separated by double spaces that markdown collapses, and " · " already appears inside values, so each
// field gets its own line. Lab card ids link to their card, and named lab book sections to the section.
const LAB_SECTIONS = [
  ['Fireworks labs', 'labs-fw'], ['Local labs', 'labs-spark'], ['Training labs', 'labs-train'],
  ['DGX Spark section', 'spark'], ['Capstone section', 'capstone'], ['Talk tracks', 'talk'],
  ['Guardrails panel', 'cost'], ['Cost calculators', 'cost'], ['Fine-tune cost calculator', 'cost'],
  ['Ceiling calculator', 'spark'],
];
function lessonHeader(md) {
  const lines = md.split('\n');
  let i = 0;
  while (i < lines.length && !lines[i].startsWith('>')) { if (lines[i].trim()) return md; i++; }
  const start = i;
  while (i < lines.length && lines[i].startsWith('>')) i++;
  const quote = lines.slice(start, i);
  if (!quote.every((l) => /^> \*\*[^*]+:\*\*/.test(l))) return md; // not the usual field lines: leave it alone
  const fields = quote.flatMap((l) => l.slice(2).split(/\s{2,}(?=\*\*)/)).map((f) => {
    f = f.replace(/\*\*([FLT]\d)\*\*/g, (m, id) => (cardIds.has(id) ? `[**${id}**](/lab-book/${LAB_BOOK}#lab-${id})` : m));
    if (f.startsWith('**Lab book:**')) {
      for (const [name, id] of LAB_SECTIONS) f = f.replace(name, `[${name}](/lab-book/${LAB_BOOK}#${id})`);
    }
    return f;
  });
  return [...lines.slice(0, start), ...fields.map((f, j) => `> ${f}${j < fields.length - 1 ? '\\' : ''}`), ...lines.slice(i)].join('\n');
}

// ---------- page builders ----------
const LANG = {
  py: ['python', 'Python'], sh: ['bash', 'Bash'], json: ['json', 'JSON'], jsonl: ['json', 'JSON Lines'],
  toml: ['toml', 'TOML'], yml: ['yaml', 'YAML'], yaml: ['yaml', 'YAML'], ts: ['ts', 'TypeScript'],
  tsx: ['tsx', 'TSX'], js: ['js', 'JavaScript'], mjs: ['js', 'JavaScript'], txt: ['txt', 'Text'],
};
function langOf(file) {
  const base = path.posix.basename(file);
  if (base === 'Makefile') return ['makefile', 'Makefile'];
  if (base.startsWith('.env')) return ['dotenv', 'Env'];
  if (base === '.gitignore' || base === '.gitkeep' || base === 'LICENSE') return ['txt', 'Text'];
  return LANG[base.split('.').pop()] ?? ['txt', 'Text'];
}
const fenceFor = (src) => '`'.repeat(Math.max(3, ...[...src.matchAll(/`+/g)].map((m) => m[0].length + 1)));

const JSONL_PREVIEW = 3;
const OPEN_MAX_LINES = 400; // the first file of a page opens when it is this short (or is the page's only file)
const NUMBERED_MAX_LINES = 1000; // line-number gutters cost markup on every line
// Past this, a file is shown as plain text: thousands of highlighted lines make a page stall for many
// seconds in Safari's engine (measured on the narration script).
const PLAIN_MIN_LINES = 2000;
// open: false, 'first' (open if short), or 'always'. weight: how much this block counts in search
// against the page prose (lessons > toolkit > video source).
function fileBlock(kitRel, name, open, weight) {
  let src = read(kitRel);
  const total = lineCount(src);
  const [lang, label] = langOf(name);
  let note = `${label} · ${total.toLocaleString('en-US')} ${total === 1 ? 'line' : 'lines'}`;
  if (name.endsWith('.jsonl')) {
    src = src.split('\n').slice(0, JSONL_PREVIEW).join('\n');
    note += ` · first ${JSONL_PREVIEW} shown`;
  }
  const plainText = total >= PLAIN_MIN_LINES;
  if (plainText) note += ' · plain text (large file)';
  const isOpen = open === 'always' || (open === 'first' && total <= OPEN_MAX_LINES);
  const fence = fenceFor(src);
  const meta = ['frame="code"', total <= NUMBERED_MAX_LINES ? 'showLineNumbers' : '', name.endsWith('.jsonl') ? 'wrap' : ''].filter(Boolean).join(' ');
  const body = plainText
    ? [`<pre class="kit-raw" tabindex="0"><code>${esc(src.replace(/\n$/, ''))}</code></pre>`]
    : [`${fence}${lang} ${meta}`, src.replace(/\n$/, ''), fence];
  return [
    `<details class="kit-file" id="${anchorFor(name)}" data-pagefind-weight="${weight}"${isOpen ? ' open' : ''}>`,
    `<summary><code>${esc(name)}</code> <span>${esc(note)}</span></summary>`,
    '',
    ...body,
    '',
    '</details>',
  ].join('\n');
}

// A markdown file shown inside a lesson: rendered, headings pushed below the page's TOC levels.
function docBlock(kitRel, name, ctx) {
  const md = rewrite(read(kitRel), ctx, { demote: 3 });
  return [`<details class="kit-file kit-doc" id="${anchorFor(name)}">`, `<summary><code>${esc(name)}</code> <span>Notes</span></summary>`, '', md.trim(), '', '</details>'].join('\n');
}

// ---------- sidebar (spec 5.1) ----------
// Home, the course (one collapsed group per day: overview, steps, wrap-up), Reference pages (open, their
// pages, then Reference. Lesson pages appear only as course steps; Starlight opens the
// day group that holds the current page.
// Videos in course order: the order the course first plays each one in full, then any it never plays.
const videoOrder = new Map();
model.steps.forEach((s, i) => s.videos.forEach((v, j) => {
  if (v.mode === 'all' && !videoOrder.has(v.stem)) videoOrder.set(v.stem, i * 10 + j);
}));
const videosInCourse = [...videos].sort((a, b) => (videoOrder.get(a.stem) ?? 1e6 + Number(a.num)) - (videoOrder.get(b.stem) ?? 1e6 + Number(b.num)));
const labBookEntry = (file) => labbook.find((b) => b.file === file);
const dayGroup = (d) => ({
  label: `Day ${d.n} · ${d.title}`,
  collapsed: true,
  ...(d.paid ? { badge: { text: '$', variant: 'caution' } } : {}),
  items: [
    { label: 'Overview', slug: d.slug },
    ...d.steps.map((s) => ({ label: `${s.n} · ${s.title}`, slug: s.slug, ...(s.optional ? { badge: { text: 'optional', variant: 'note' } } : {}) })),
    { label: 'Wrap-up and drill', slug: d.wrapSlug },
  ],
});
const PART_NAME = { 1: 'Serving', 2: 'Training' };
const labsOverview = { label: 'Labs overview', slug: 'toolkit' };
const sidebar = [
  { label: 'Home', link: '/' },
  ...[...new Set(model.days.map((d) => d.part))].map((part) => ({
    label: `Course · Part ${part} · ${PART_NAME[part] ?? ''}`.replace(/ · $/, ''),
    items: model.days.filter((d) => d.part === part).map(dayGroup),
  })),
  { label: 'Reference', collapsed: true, items: [
    { label: 'Videos (in course order)', slug: 'videos' },
    { label: 'Each video', collapsed: true, items: videosInCourse.map((v) => ({ label: v.title, slug: v.slug })) },
    { label: 'Lessons and code', slug: 'lessons' },
    ...[[LAB_BOOK, 'Lab book'], ['inference-field-guide.html', 'Field guide']]
      .filter(([f]) => labBookEntry(f)).map(([f, label]) => ({ label, link: labBookEntry(f).route })),
    ...labbook.filter((b) => b.file !== LAB_BOOK && b.file !== 'inference-field-guide.html').map((b) => ({ label: b.title, link: b.route })),
    { label: 'Glossary', slug: 'reference/glossary' },
    { label: 'Troubleshooting', slug: 'reference/troubleshooting' },
    { label: 'Kit README (offline start)', slug: 'reference/kit-readme' },
    { label: 'Toolkit', collapsed: true, items: [labsOverview, ...TOOLKIT_PAGES.map((p) => ({ label: p.title, slug: p.slug }))] },
    { label: 'Video source', collapsed: true, items: [{ label: 'Video source overview', slug: 'video-source' }, ...VS_PAGES.map((p) => ({ label: p.title, slug: p.slug }))] },
  ] },
];
fs.mkdirSync(GEN, { recursive: true });
fs.writeFileSync(path.join(GEN, 'sidebar.json'), JSON.stringify(sidebar, null, 2));

// ---------- previous / next (spec 5.6) ----------
// Every spine page (home, then per day: overview, steps, wrap-up) gets
// Starlight's prev/next set to its spine neighbours; the last wrap-up leads back home.
// Video pages page through the videos in course order. Every other page (Reference) has none, so Starlight
// never walks the sidebar into or out of the course.
const slugOfRoute = (route) => route.replace(/^\/|\/$/g, '');
const spineLabel = (e) => (e.kind === 'step' ? `Day ${model.steps.find((s) => s.id === e.id).day} · ${e.title}` : e.title);
const pager = new Map();
spine.forEach((e, i) => {
  const prev = spine[i - 1];
  const next = spine[i + 1];
  pager.set(slugOfRoute(e.route), {
    prev: prev ? { link: prev.route, label: spineLabel(prev) } : false,
    next: next ? { link: next.route, label: spineLabel(next) } : SPINE_END,
  });
});
videosInCourse.forEach((v, i) => {
  const prev = videosInCourse[i - 1];
  const next = videosInCourse[i + 1];
  pager.set(v.slug, {
    prev: prev ? { link: prev.route, label: prev.title } : false,
    next: next ? { link: next.route, label: next.title } : false,
  });
});

// Last line of defence: whatever the source (kit README, lesson README, notes, code, lab book), nothing
// that looks like a credential is written out. STRICT builds fail; other builds publish it redacted.
function clean(text, where) {
  if (!SECRET_TEXT.test(text)) return text;
  warn(`${where} contains something that looks like a credential; it was redacted`);
  return text.replace(new RegExp(SECRET_TEXT.source, 'g'), '[redacted]');
}

let pageCount = 0;
const written = new Set();
function page(slug, fm, body) {
  if (written.has(slug)) warn(`two pages were written to /${slug}/`);
  written.add(slug);
  pageCount++;
  const file = path.join(DOCS, slug === '' ? 'index.md' : `${slug}.md`);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const all = { ...fm, ...(pager.get(slug) ?? { prev: false, next: false }) };
  const front = Object.entries(all).filter(([, v]) => v !== undefined).map(([k, v]) => `${k}: ${typeof v === 'string' ? q(v) : JSON.stringify(v)}`);
  fs.writeFileSync(file, clean(`---\n${front.join('\n')}\n---\n\n${body.trim()}\n`, `page /${slug}`));
}

// ---------- write everything ----------
fs.rmSync(DOCS, { recursive: true, force: true });
fs.rmSync(LABBOOK_OUT, { recursive: true, force: true });
fs.mkdirSync(LABBOOK_OUT, { recursive: true });

const totalMinutes = readme.match(/Total ≈ (\d+) minutes/)?.[1];
// Frontmatter descriptions: markdown reduced to one plain line.
const plainText = (s) => String(s ?? '').replace(/\[([^\]]*)\]\([^)]*\)/g, '$1').replace(/[*`]/g, '').replace(/\s+/g, ' ').trim();
const short = (s, n = 180) => { const t = plainText(s); return t.length > n ? `${t.slice(0, n - 1).replace(/\s+\S*$/, '')}…` : t || undefined; };

// An array literal from a lab book script (`const NAME = [` ... a line starting with `];`), read as data.
function arrayLiteral(html, name, after = '') {
  const from = after ? html.indexOf(after) : 0;
  const at = html.indexOf(`const ${name} = [`, Math.max(0, from));
  if (from < 0 || at < 0) throw new Error(`const ${name} = [ not found`);
  const start = html.indexOf('[', at);
  const end = html.slice(start).search(/\n\s*\];/) + start;
  return vm.runInNewContext(`(${html.slice(start, end).trimEnd()}\n])`, {}, { timeout: 1000 });
}

// ---------- the course pages (spec 5.2 to 5.5) ----------
// d1-s2 shows the lab book's spend-cap checklist; its ticks are mirrored to the lab book's own storage.
let guardItems = [];
try {
  guardItems = arrayLiteral(read(`02-lab-book/${LAB_BOOK}`), 'items', 'guardrail checklist');
  if (!Array.isArray(guardItems) || !guardItems.length || guardItems.some((t) => typeof t !== 'string')) throw new Error('not a list of text lines');
} catch (e) {
  warn(`lab book: the guardrail checklist items could not be read (${e.message}); Day 1 step 2 shows no spend-cap ticks`);
  guardItems = [];
}
const courseCtx = {
  esc, fileBlock, docBlock,
  // the site's link rewriter; it maps line to line, so the templates can weave their notes in afterwards
  rewrite: (md, rctx) => rewrite(md.replace("the lab book's training section", `[the lab book's training section](/lab-book/${LAB_BOOK}#labs-train)`), rctx),
  labBookHref: (from, id) => `/lab-book/${LAB_BOOK}?from=${from}#lab-${id}`,
  guardItems,
};

page('', { title: 'Start here', description: 'Twelve guided days to build, measure and explain AI systems with your own results.', tableOfContents: false }, P.homePage(model));
for (const d of model.days) {
  page(d.slug, { title: `Day ${d.n} · ${d.title}`, description: short(d.tile ?? d.overview?.today), tableOfContents: false }, P.dayPage(d, model));
  const wrap = P.wrapupPage(d, model);
  page(d.wrapSlug, { title: `Day ${d.n} wrap-up and drill`, description: short(d.wrapup?.done) ?? `Day ${d.n}: review your numbers and explain your results.`, tableOfContents: false }, wrap);
}
for (const s of model.steps) {
  const desc = short(s.why) ?? (s.lesson?.info ? plain(`${s.lesson.info.what} (runs on: ${s.lesson.info.runsOn})`) : undefined);
  page(s.slug, { title: s.title, description: desc }, P.stepPage(s, model, courseCtx));
}

// ---------- Reference (spec 5.7) ----------
page('videos', { title: 'Videos', description: `All ${videos.length} videos in the order the course plays them${totalMinutes ? `, about ${totalMinutes} minutes in total` : ''}. Subtitles are burned in.`, tableOfContents: false },
  P.videoLibraryPage(model, videos));
for (const v of videos) page(v.slug, { title: v.title, description: v.subtitle, tableOfContents: false }, P.videoPageExtras(v, model));

// Lessons index: the kit README table plus the course step each lesson is (lesson pages are course steps).
{
  const stepCell = (dir) => (stepsOfLesson.get(dir) ?? []).map((s) => `[Day ${s.day} · Step ${s.n}](${s.route})`).join(', ') || 'not in the course';
  let row = 0;
  const table = sectionOf(readme, '## The 19 lessons').replace(/^## .*\n+/, '').split('\n').map((line) => {
    if (!line.startsWith('|')) { row = 0; return line; }
    const cells = line.split('|').slice(1, -1);
    row++;
    const add = row === 1 ? ' day · step ' : row === 2 ? '---' : ` ${stepCell(line.match(/`(\d\d-[\w-]+)`/)?.[1])} `;
    return `|${[cells[0], add, ...cells.slice(1)].join('|')}|`;
  }).join('\n');
  page('lessons', { title: 'Lessons and code', description: `All ${lessons.length} lessons: what you do, where it runs and which course step it is.`, tableOfContents: false },
    `<p class="kit-intro">All ${lessons.length} lessons, in order. Each one is a step of the course: open it from the Day and Step column, or follow the course from the start.</p>\n\n` +
    rewrite(table, { src: 'README.md', srcDir: '' }));
}
// A lesson that is no course step (none today) keeps a plain page: the README and its files.
for (const l of lessons.filter((x) => !stepsOfLesson.has(x.dir))) {
  const ctx = { src: `${l.rel}/README.md`, srcDir: l.rel, files: l.files, route: l.route };
  const docs = l.files.filter((f) => f.endsWith('.md'));
  const code = l.files.filter((f) => !f.endsWith('.md'));
  const parts = [rewrite(lessonHeader(splitTitle(l.md)[1]), ctx)];
  if (l.files.length) {
    parts.push('## Files in this lesson');
    docs.forEach((f) => parts.push(docBlock(`${l.rel}/${f}`, f, ctx)));
    code.forEach((f, i) => parts.push(fileBlock(`${l.rel}/${f}`, f, i === 0 && 'first', 0.5)));
  }
  page(l.slug, { title: l.title, description: l.info ? plain(`${l.info.what} (runs on: ${l.info.runsOn})`) : undefined }, parts.join('\n\n'));
}

page('reference/glossary', { title: 'Glossary', description: `${model.glossary.length} terms from the course, each with an example.`, tableOfContents: false }, P.glossaryPage(model));

// Troubleshooting: the kit README's fixes, then every step's own "Stuck?" rows, in course order.
{
  const kitFixes = rewrite(sectionOf(readme, "## If something doesn't work").replace(/^## .*\n+/, ''), { src: 'README.md', srcDir: '' });
  const stepFixes = model.steps.filter((s) => s.stuck.length).map((s) => [
    `### Day ${s.day} · Step ${s.n} · ${s.title}`,
    '',
    ['<dl class="kc-card kc-stuck-list kc not-content">',
      ...s.stuck.map((x) => `<div><dt>${P.inlineMd(x.problem, { from: '/reference/troubleshooting/' })}</dt><dd>${P.inlineMd(x.fix, { from: '/reference/troubleshooting/' })}</dd></div>`),
      '</dl>'].join('\n'),
    '',
    `<p class="kit-intro"><a href="${s.route}">Go to the step</a></p>`,
  ].join('\n'));
  page('reference/troubleshooting', { title: 'Troubleshooting', description: 'Fixes for common problems: the kit README list, then the fixes from each course step.' },
    ['<p class="kit-intro">The kit’s own list first, then the fixes from each step of the course.</p>', '## From the kit README', kitFixes,
      ...(stepFixes.length ? ['## From the course steps', ...stepFixes] : [])].join('\n\n'));
}

// Kit README (offline start): the old home page. The "unzip the 11 parts" note only applies to the zip
// download, so it is dropped.
{
  const ctx = { src: 'README.md', srcDir: '', cardTables: true };
  let body = splitTitle(readme)[1].replace(/^> \*\*Got this as \d+ parts[\s\S]*?\n(?!>)/m, '');
  body = rewrite(body, ctx);
  const cards = [
    ['/videos/', '01 Watch', `${videos.length} videos`, totalMinutes ? `about ${totalMinutes} minutes` : 'narrated explainers'],
    [`/lab-book/${LAB_BOOK}?from=${KIT_README_ROUTE}`, '02 Read', 'Lab book', 'plus the field guide'],
    ['/lessons/', '03 Run', `${lessons.length} lessons`, `${lessons[0]?.dir.slice(0, 2)} to ${lessons.at(-1)?.dir.slice(0, 2)}, with code`],
    ['/video-source/', '04 Source', 'Video source', 'Remotion + Kokoro'],
  ];
  const grid = `<div class="kit-cards not-content">\n${cards.map(([href, k, t, s]) =>
    `<a href="${href}"><span class="kit-eyebrow">${k}</span><strong>${t}</strong><span>${s}</span></a>`).join('\n')}\n</div>`;
  page('reference/kit-readme', { title: 'Kit README (offline start)', description: 'The kit README: how to use the kit offline, without this site.' }, `${grid}\n\n${body}`);
}

// Toolkit
page('toolkit', { title: 'Labs overview', description: 'The 03-labs README: how the lessons, the felab toolkit and the mock server fit together.' },
  rewrite(splitTitle(read('03-labs/README.md'))[1], { src: '03-labs/README.md', srcDir: '03-labs', cardTables: true }));
for (const p of TOOLKIT_PAGES) {
  page(p.slug, { title: p.title, description: p.description, tableOfContents: false },
    [`<p class="kit-intro">${esc(p.description)}</p>`, ...p.files.map((f, i) => fileBlock(`03-labs/${f}`, f, p.files.length === 1 ? 'always' : i === 0 && 'first', 0.5))].join('\n\n'));
}

// Video source
page('video-source', { title: 'Video source', description: 'The Remotion + Kokoro project that rendered the 18 videos.' },
  rewrite(splitTitle(read('04-video-source/README.md'))[1], { src: '04-video-source/README.md', srcDir: '04-video-source' }));
for (const p of VS_PAGES) {
  page(p.slug, { title: p.title, description: p.description, tableOfContents: false },
    [`<p class="kit-intro">${esc(p.description)}</p>`, ...p.files.map((f, i) => fileBlock(`04-video-source/${f}`, f, p.files.length === 1 ? 'always' : i === 0 && 'first', 0.2))].join('\n\n'));
}

// Lab book: the copies the web server publishes (the originals are never changed). Added, and nothing else:
// - <html lang> and <body data-pagefind-body>: search skips pages without them; the files have neither tag,
//   so they go where the browser implies them anyway (no doctype is added, so rendering mode is unchanged)
// - a viewport meta where it is missing, so phones do not show a zoomed-out desktop page
// - a small style block for phones: lab cards had no column size, so long code widened them past the
//   screen; smooth scrolling made #lab-XX jumps stop short; the section rail links were tiny to tap
// - the "Back to the course" bar (spec 5.8), fixed at the bottom (the lab book's section rail is sticky at
//   the top). Its target is ?from=, accepted only as a same-site path (^/[a-z0-9/._-]*$, not //...);
//   anything else goes to the home page. The course adds ?from=<its route> to every lab book link.
// - the closing </body></html>, without which search ignores the page title
const HEAD_ONLY = new Set(['meta', 'title', 'link', 'style', 'script', 'base', 'noscript', 'template']);
const RAW_TEXT = new Set(['style', 'script', 'title', 'noscript', 'template', 'textarea']);
const PHONE_FIX = '<style>' + [
  // smooth scrolling makes #lab-XX and section jumps stop short while the page is still being built
  'html{scroll-behavior:auto}',
  '.lab-body2{grid-template-columns:minmax(0,1fr)}',
  '@media (min-width:860px){.lab-body2{grid-template-columns:minmax(0,1.35fr) minmax(0,1fr)}}',
  // card header: id and title on one row, the meta chips wrap onto the next on narrow screens
  '@media (max-width:859px){details.lab-item summary{grid-template-columns:auto minmax(0,1fr)}details.lab-item .lab-meta{grid-column:1/-1;justify-content:flex-start}}',
  '@media (pointer:coarse){.rail a{padding-top:12px;padding-bottom:12px}}',
  // the back bar: slim, above everything, in the lab book's own colours (with fallbacks for the field guide)
  'body{padding-bottom:calc(56px + env(safe-area-inset-bottom,0px))}',
  '#kit-back{position:fixed;left:0;right:0;bottom:0;z-index:1000;display:flex;justify-content:center;padding:4px 12px calc(4px + env(safe-area-inset-bottom,0px));background:var(--surface,#fff);border-top:1px solid var(--rule,#d3d7ce);box-shadow:0 -6px 18px -12px rgba(0,0,0,.35)}',
  '#kit-back a{display:inline-flex;align-items:center;gap:8px;min-height:44px;padding:0 18px;border-radius:999px;font:600 15px/1.2 "IBM Plex Sans",system-ui,sans-serif;color:var(--accent,#0e7a6b);text-decoration:none}',
  '#kit-back a:hover,#kit-back a:focus-visible{background:var(--accent-soft,#d5ece6)}',
  '@media print{#kit-back{display:none}body{padding-bottom:0}}',
].join('') + '</style>\n';
const BACK_BAR = '<nav id="kit-back" aria-label="Course" data-pagefind-ignore><a href="/">Back to the course</a></nav>\n' +
  '<script>(function(){try{var f=new URLSearchParams(location.search).get("from");' +
  'if(f&&/^\\/[a-z0-9\\/._-]*$/.test(f)&&f.slice(0,2)!=="//")document.querySelector("#kit-back a").setAttribute("href",f);}catch(e){}})();</script>\n';
const VIEWPORT = '<meta name="viewport" content="width=device-width, initial-scale=1">\n';
function servedLabBook(html, title) {
  const tag = /<!--[\s\S]*?-->|<![^>]*>|<(\/?)([a-zA-Z][\w-]*)[^>]*>/g;
  let doctypeEnd = 0, hasHtml = false, hasViewport = false, bodyAt = -1, bodyTag = null, m;
  while ((m = tag.exec(html))) {
    if (m[0].startsWith('<!')) { if (/^<!doctype/i.test(m[0])) doctypeEnd = tag.lastIndex; continue; }
    if (m[1]) continue;
    const name = m[2].toLowerCase();
    if (name === 'html') { hasHtml = true; continue; }
    if (name === 'head') continue;
    if (name === 'meta' && /name=["']?viewport/i.test(m[0])) hasViewport = true;
    if (name === 'body') { bodyTag = m; break; }
    if (!HEAD_ONLY.has(name)) { bodyAt = m.index; break; }
    if (RAW_TEXT.has(name)) {
      const close = html.toLowerCase().indexOf(`</${name}`, tag.lastIndex);
      tag.lastIndex = close < 0 ? html.length : close;
    }
  }
  const meta = `data-pagefind-body data-pagefind-meta="title:${esc(title)}"`;
  if (bodyTag) {
    const end = bodyTag.index + bodyTag[0].length;
    html = html.slice(0, bodyTag.index) + PHONE_FIX + `<body ${meta}` + html.slice(bodyTag.index + 5, end) + '\n' + BACK_BAR + html.slice(end);
  } else if (bodyAt >= 0) html = `${html.slice(0, bodyAt)}${PHONE_FIX}<body ${meta}>\n${BACK_BAR}${html.slice(bodyAt)}`;
  else warn(`lab book: found no place for <body> in the served copy (${title})`);
  const headAdd = (hasHtml ? '' : '<html lang="en">\n') + (hasViewport ? '' : VIEWPORT);
  // Pagefind drops data-pagefind-meta unless the body is closed.
  if (!/<\/body\s*>/i.test(html)) html = html.replace(/\s*$/, '\n</body>\n</html>\n');
  return html.slice(0, doctypeEnd) + (doctypeEnd ? '\n' : '') + headAdd + html.slice(doctypeEnd);
}
for (const b of labbook) {
  const html = read(`02-lab-book/${b.file}`);
  fs.writeFileSync(path.join(LABBOOK_OUT, b.file), clean(servedLabBook(html, b.title), `02-lab-book/${b.file}`));
}

// ---------- the spine for kit.js (spec 6.2) ----------
// window.KIT_SPINE: the Next order. r route, k kind (home, day, step, wrapup), id, t title, day,
// opt (optional step), m minutes. Escaped to ASCII, so the file reads the same under any charset.
{
  const entries = spine.map((e) => {
    const step = e.kind === 'step' ? model.steps.find((s) => s.id === e.id) : null;
    const day = e.kind === 'home' ? 0 : Number(/^d(\d+)/.exec(e.id)?.[1] ?? 0);
    return { r: e.route, k: e.kind, id: e.id, t: e.title, day, ...(step ? { opt: !!step.optional } : {}), ...(e.minutes != null ? { m: e.minutes } : {}) };
  });
  const json = JSON.stringify(entries).replace(/[\u007f-￿]/g, (c) => `\\u${c.charCodeAt(0).toString(16).padStart(4, '0')}`);
  fs.writeFileSync(SPINE_OUT, `/* Written by scripts/sync.mjs from course/course.yaml: the course in Next order (read by kit.js). */\nwindow.KIT_SPINE = ${json};\n`);
}

// ---------- the code download (spec 5.9) ----------
// Exactly the 03-labs files the site publishes (walk: the same .gitignore, secret, size and binary filters),
// lesson READMEs included, under 03-labs/. Fixed dates so an unchanged kit gives a byte-identical zip;
// files that are executable in the kit keep their mode. Served behind the same cookie as every page.
{
  const ZIP_DATE = new Date('2026-01-01T00:00:00Z');
  const entries = {};
  for (const f of labsAll) {
    const full = abs(`03-labs/${f}`);
    const exec = (fs.statSync(full).mode & 0o111) !== 0;
    entries[`03-labs/${f}`] = [new Uint8Array(fs.readFileSync(full)), { mtime: ZIP_DATE, os: 3, attrs: ((exec ? 0o100755 : 0o100644) << 16) >>> 0 }];
  }
  fs.rmSync(DOWNLOADS_OUT, { recursive: true, force: true });
  fs.mkdirSync(DOWNLOADS_OUT, { recursive: true });
  const zip = zipSync(entries, { level: 9, mtime: ZIP_DATE });
  fs.writeFileSync(path.join(DOWNLOADS_OUT, '03-labs.zip'), zip);
  console.log(`sync: downloads/03-labs.zip: ${labsAll.length} files, ${mb(zip.length)}`);
}

console.log(`sync: ${pageCount} pages (home, ${model.days.length} days, ${model.steps.length} steps, ${model.days.length} wrap-ups, ${videos.length} videos, ${lessons.length} lessons), ${labbook.length} lab book files, from ${KIT}`);
for (const s of new Set(skipped)) console.log(`sync: not published: ${s}`);
const uniqueWarnings = [...new Set(warnings)];
for (const w of uniqueWarnings) console.warn(`sync warning: ${w}`);
if (uniqueWarnings.length && STRICT) { console.error(`sync: ${uniqueWarnings.length} warning(s) with STRICT=1`); process.exit(1); }
