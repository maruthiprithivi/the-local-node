// The guided course: loads course/course.yaml (structure), course/content/day-NN.yaml (plain-language text)
// and chapters.txt (scene times), joins them with the kit (lesson READMEs, narration.json) and returns the
// model every course page is built from (docs/course-spec.md section 4).
//
//   import { loadCourse, validateCourse } from './course.mjs'
//   const model = loadCourse({ KIT, WEB, lessons, videos, narration, cardIds, readme, read })
//   const problems = validateCourse(model)          // [] when the content matches the kit
//
// CLI (runs without sync.mjs: it builds the lesson and video objects it needs from the kit itself):
//   node scripts/course.mjs --check [--day N] [--content DIR]   exit 1 when there are problems
//   node scripts/course.mjs --dump [--day N] [--content DIR]    print the model as JSON (debugging)
// --day N checks that day's content file only (plus the course structure), so a day can be checked while
// other days are unwritten. KIT_DIR overrides the kit root, COURSE_CONTENT_DIR (or --content) the content folder.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import YAML from 'yaml';

const HERE_WEB = path.resolve(import.meta.dirname, '..');

// ---------- small helpers ----------
// The page rules of spec 0 and 7, exported so the post-build checks can use the very same patterns.
export const EMOJI = /\p{Extended_Pictographic}|\u{FE0F}|[\u{1F1E6}-\u{1F1FF}]/u; // also text-style ones such as ⏱ and ▶
export const VIDEO_N = /\bvideos?\s+\d+\b/i; // "video 9", "videos 14-18": never on course pages
const collapse = (s) => String(s).replace(/\s+/g, ' ').trim();
const pad2 = (n) => String(n).padStart(2, '0');
const isObj = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
const words = (s) => collapse(s).split(' ').filter(Boolean).length;
const withoutCode = (s) => String(s).replace(/`+[^`]*`+/g, '');
const quoteSnip = (s, at, len = 60) => collapse(s.slice(Math.max(0, at - 25), at + len));

/** "45 min", "1 h 55", "2 h": a duration in minutes as the course writes it. */
export function minutesText(m) {
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60), r = m % 60;
  return r ? `${h} h ${pad2(r)}` : `${h} h`;
}
/** "about 45 min", "about 1 h 55": a total rounded to 5 minutes (spec 2.1). */
export const aboutMinutes = (m) => `about ${minutesText(Math.max(5, Math.round(m / 5) * 5))}`;

// A shell comment starts at a # that begins the line or follows whitespace, outside quotes.
function stripComment(line) {
  let q = null;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (q) { if (c === q) q = null; else if (c === '\\' && q === '"') i++; continue; }
    if (c === '"' || c === "'") { q = c; continue; }
    if (c === '\\') { i++; continue; }
    if (c === '#' && (i === 0 || /\s/.test(line[i - 1]))) return line.slice(0, i);
  }
  return line;
}
/** The key of a Run command (spec 3): first line, no trailing comment, whitespace collapsed, no trailing \. */
export const runKey = (firstLine) => collapse(stripComment(String(firstLine))).replace(/\s*\\$/, '');

// ---------- lesson README parsing ----------
/** Split markdown into "## " sections (headings inside code fences do not count). */
export function readmeSections(md) {
  const lines = md.split('\n');
  const out = [{ title: null, start: 0, lines: [] }];
  let fence = null;
  lines.forEach((line, i) => {
    const f = line.match(/^\s*(`{3,}|~{3,})/);
    if (fence) { if (f && f[1][0] === fence[0] && f[1].length >= fence.length) fence = null; }
    else if (f) fence = f[1];
    else if (/^## /.test(line)) { out.push({ title: line.slice(3).trim(), start: i, lines: [line] }); return; }
    out.at(-1).lines.push(line);
  });
  return out;
}
const sectionOf = (sections, re) => sections.find((s) => s.title && re.test(s.title)) ?? null;

// Fenced code blocks of a section: [{ line (1-based line of the first content line), lines }]
function fencedBlocks(section) {
  const blocks = [];
  let cur = null;
  section.lines.forEach((line, i) => {
    const f = line.match(/^\s*(`{3,}|~{3,})/);
    if (cur) {
      if (f && f[1][0] === cur.fence[0] && f[1].length >= cur.fence.length) { blocks.push(cur); cur = null; }
      else cur.lines.push(line);
    } else if (f) cur = { fence: f[1], line: section.start + i + 2, lines: [] };
  });
  return blocks;
}

// Logical commands of a Run block: lines joined across a trailing \, for/while/until loops up to their
// done; cd lines and comment-only lines are not commands.
function commandsIn(block) {
  const cmds = [];
  const L = block.lines;
  const tokens = (s) => stripComment(s).split(/[\s;]+/).filter(Boolean);
  const nesting = (s) => tokens(s).filter((t) => t === 'do').length - tokens(s).filter((t) => t === 'done').length;
  const continued = (s) => stripComment(s).trimEnd().endsWith('\\');
  for (let i = 0; i < L.length; i++) {
    const first = L[i];
    if (!stripComment(first).trim()) continue;
    const at = i;
    const text = [first];
    const loop = /^(for|while|until)\b/.test(first.trim());
    let depth = loop ? nesting(first) : 0;
    while (i + 1 < L.length && (continued(L[i]) || (loop && depth > 0))) {
      i++;
      text.push(L[i]);
      if (loop) depth += nesting(L[i]);
    }
    const key = runKey(first);
    if (/^cd(\s|$)/.test(key) && !/&&|;|\|/.test(key)) continue;
    cmds.push({ key, text: text.join('\n'), line: block.line + at });
  }
  return cmds;
}

const CHECK_ITEM = /^(\d+)\. (.+?) \*\((.+)\)\*$/s;

/**
 * Parse a lesson README: the "Check yourself" items, the "Explain what you learned" line and the Run
 * commands. errors: kit lines that do not follow the pattern (reported by the validator).
 */
export function parseReadme(md) {
  const sections = readmeSections(md);
  const errors = [];
  // Check yourself: "N. question *(answer)*", one item per numbered line (wrapped lines are joined)
  const checks = [];
  const cs = sectionOf(sections, /^Check yourself\b/);
  if (cs) {
    const items = [];
    cs.lines.slice(1).forEach((line, i) => {
      if (/^\d+\.\s/.test(line)) items.push({ text: line.trim(), line: cs.start + i + 2 });
      else if (line.trim() && items.length && !items.at(-1).closed && !/^#/.test(line)) items.at(-1).text += ' ' + line.trim();
      else if (!line.trim() && items.length) items.at(-1).closed = true; // a blank line ends the item: later prose is not part of it
    });
    items.forEach((it, i) => {
      const m = it.text.match(CHECK_ITEM);
      if (!m) { errors.push(`Check yourself item ${i + 1} (line ${it.line}) does not match "N. question *(answer)*"`); return; }
      if (Number(m[1]) !== i + 1) errors.push(`Check yourself item ${i + 1} (line ${it.line}) is numbered ${m[1]}`);
      checks.push({ n: i + 1, kitQ: m[2].trim(), kitA: m[3].trim(), line: it.line });
    });
    if (!items.length) errors.push('Check yourself section has no numbered items');
  }
  // Explain what you learned: the blockquote, lines joined, outer quotes removed
  let say = null;
  const ss = sectionOf(sections, /^Explain what you learned\b/);
  if (ss) {
    const q = [];
    for (const line of ss.lines.slice(1)) {
      if (/^\s*>/.test(line)) q.push(line.replace(/^\s*>\s?/, '').trim());
      else if (q.length) break;
    }
    if (q.length) {
      say = collapse(q.join(' '));
      if (/^["“].*["”]$/.test(say)) say = say.slice(1, -1).trim();
    } else errors.push('Explain what you learned section has no quoted line');
  }
  // Run: every logical command in the fenced blocks under "## Run"
  const rs = sectionOf(sections, /^Run$/);
  const run = rs ? fencedBlocks(rs).flatMap(commandsIn) : [];
  return { sections, checks, say, run, errors, hasChecks: !!cs, hasRun: !!rs };
}

// The README text a lesson step page shows under "From the lesson" (spec 5.4 item 6), after `replace`:
// without the H1, the header quote, the "Next ->" lines and the Check yourself / Explain what you learned sections.
function shownReadme(md, replace) {
  let text = md;
  for (const r of replace) if (typeof r?.find === 'string' && r.find && typeof r.with === 'string') text = text.split(r.find).join(r.with);
  const lines = text.split('\n');
  const drop = new Set();
  let i = 0;
  const skipBlank = () => { while (i < lines.length && !lines[i].trim()) i++; };
  skipBlank();
  if (/^# /.test(lines[i] ?? '')) drop.add(i++);          // the H1
  skipBlank();
  while (i < lines.length && /^>/.test(lines[i])) drop.add(i++); // the header quote (Lab book / Watch / Time / Cost)
  for (const s of readmeSections(text)) {
    if (s.title && /^(Check yourself|Explain what you learned)\b/.test(s.title)) s.lines.forEach((_, j) => drop.add(s.start + j));
  }
  lines.forEach((line, j) => { if (/^\*\*Next →\*\*/.test(line)) drop.add(j); });
  return lines.map((line, j) => ({ n: j + 1, line })).filter((x) => !drop.has(x.n - 1));
}

// ---------- chapter labels ----------
// Scenes with a heading use it ("Worked example · support assistant" -> "Worked example: support assistant").
// The others are named here by scene kind (and the parameter that tells two uses of one kind apart).
const KIND_LABELS = {
  Title: 'Introduction',
  'PrefillDecode:phase=prefill': 'Prefill: reading the prompt',
  'PrefillDecode:phase=decode': 'Decode: writing one token at a time',
  Metrics: 'The four numbers that matter',
  KvGrow: 'Why the KV cache exists',
  KvMath: 'How big the KV cache gets',
  'KvBlocks:mode=naive': 'Reserving memory up front',
  'KvBlocks:mode=paged': 'PagedAttention: memory in small blocks',
  BandwidthPipe: 'Every token reads the whole model',
  Ceiling: 'The decode speed ceiling',
  DeviceTable: 'Memory bandwidth across hardware',
  Roofline: 'Batching and the roofline',
  'Precision:mode=fp16': '16-bit: the baseline',
  'Precision:mode=fp8': '8-bit (FP8)',
  'Precision:mode=int4': '4-bit',
  KvQuant: 'Quantizing the KV cache',
  'BatchGantt:mode=static': 'Static batching',
  'BatchGantt:mode=continuous': 'Continuous batching',
  ChunkedPrefill: 'Chunked prefill',
  SpecDecode: 'Speculative decoding',
  'TrainingPipeline:stage=0': 'Start from a base model',
  'TrainingPipeline:stage=1': 'Supervised fine-tuning (SFT)',
  'TrainingPipeline:stage=2': 'Preference tuning (DPO)',
  'TrainingPipeline:stage=3': 'Reinforcement fine-tuning (RFT)',
  LoRA: 'LoRA: two small matrices',
  TrainDecide: 'Which method to choose',
  MemoryStack: 'What fills the memory',
  Offload: 'When the model does not fit',
  MoEActive: 'Mixture of experts',
  Parallelism: 'Tensor vs pipeline parallelism',
  'PlatformMap:highlight=0': 'The serving layers',
  'PlatformMap:highlight=1': 'GPU cloud vs managed platform',
  Modes: 'Four capacity modes',
  Maturity: 'The customer journey',
  'ServingStack:highlight=-1': 'What a serving engine does',
  'ServingStack:highlight=2': 'Why vLLM became the default',
  'SweepCurve:phase=throughput': 'Sweeping concurrency',
  'SweepCurve:phase=latency': 'Where p95 crosses the target',
  'PrefixTree:step=0': 'Prompts as a tree',
  'PrefixTree:step=1': 'Reusing the shared prefix',
  'QloraMem:mode=compare': 'Full fine-tuning vs QLoRA memory',
  'QloraMem:mode=fits': 'An 8B fine-tune on a desktop',
  TwoBox: 'Two boxes',
  TrainLoop: 'The training loop',
  'WeightUpdate:mode=full': 'Full fine-tuning moves every weight',
  'WeightUpdate:mode=lora': 'LoRA: freeze the weight, train two thin matrices',
  MemoryLedger: 'Where the training memory goes',
  LossMask: 'Loss masking: only the answer counts',
  'RlhfLoop:stage=0': 'Stage 1: start from an SFT model',
  'RlhfLoop:stage=1': 'Stage 2: comparisons train a reward model',
  'RlhfLoop:stage=2': 'Stage 3: the PPO loop',
  DpoShift: 'What the DPO loss does',
};
const SCENE_LABELS = { 'sft:1': 'Where SFT sits' }; // "<narration id>:<scene index>" overrides

/** Human chapter label of one narration scene, or null when there is none (the EndCard). */
export function sceneLabel(id, index, scene) {
  if (scene.visual === 'EndCard') return null;
  if (SCENE_LABELS[`${id}:${index}`]) return SCENE_LABELS[`${id}:${index}`];
  const p = scene.params ?? {};
  if (typeof p.heading === 'string' && p.heading.trim()) return collapse(p.heading).replace(' · ', ': ');
  for (const [k, v] of Object.entries(p)) {
    if (['string', 'number'].includes(typeof v) && KIND_LABELS[`${scene.visual}:${k}=${v}`]) return KIND_LABELS[`${scene.visual}:${k}=${v}`];
  }
  return KIND_LABELS[scene.visual] ?? undefined; // undefined: a scene kind nobody named (a problem)
}

/** chapters.txt -> Map(stem -> [t0, t1, ...]) plus problems. */
export function parseChapters(text) {
  const map = new Map(), problems = [];
  text.split('\n').forEach((raw, i) => {
    const line = raw.trim();
    if (!line || line.startsWith('#')) return;
    const [stem, ...ts] = line.split(/\s+/);
    const times = ts.map(Number);
    if (!ts.length || times.some((t) => !Number.isFinite(t) || t < 0)) { problems.push(`chapters.txt line ${i + 1}: expected "<stem> <t0> <t1> ..." in seconds`); return; }
    if (map.has(stem)) problems.push(`chapters.txt line ${i + 1}: ${stem} is listed twice`);
    if (times[0] !== 0) problems.push(`chapters.txt ${stem}: the first scene must start at 0.0`);
    for (let k = 1; k < times.length; k++) if (!(times[k] > times[k - 1])) problems.push(`chapters.txt ${stem}: time ${k} (${ts[k]}) is not after time ${k - 1} (${ts[k - 1]})`);
    map.set(stem, times);
  });
  return { map, problems };
}

// ---------- the kit, read directly (CLI; sync.mjs passes its own objects) ----------
function tableAfter(md, heading) {
  const at = md.indexOf(heading);
  if (at < 0) throw new Error(`kit README section not found: ${heading}`);
  const next = md.indexOf('\n## ', at + heading.length);
  const rows = [];
  for (const line of md.slice(at, next < 0 ? undefined : next).split('\n').slice(1)) {
    if (line.startsWith('|')) rows.push(line);
    else if (rows.length) break;
  }
  return rows.slice(2).map((r) => r.split('|').slice(1, -1).map((c) => c.trim()));
}
const SKIP_DIRS = new Set(['.git', 'node_modules', '__pycache__', '.venv', 'logs', 'adapters', 'fused', 'models', 'sft_model', 'checkpoints', 'bench', 'results']);

/** The minimal ctx loadCourse needs, built from the kit folder (no sync.mjs). */
export function kitContext(KIT, WEB = HERE_WEB) {
  const read = (rel) => fs.readFileSync(path.join(KIT, rel), 'utf8').replace(/^﻿/, '').replace(/\r\n?/g, '\n');
  const readme = read('README.md');
  const narration = JSON.parse(read('04-video-source/src/narration.json'));
  const videos = tableAfter(readme, '## The 18 videos').map(([num, file, min, what, runNext]) => {
    const fileName = file.replace(/`/g, '');
    const stem = fileName.replace(/\.mp4$/, '');
    const n = narration[stem.replace(/^\d\d-/, '')];
    return { num, fileName, stem, min, what, runNext, title: n?.title ?? stem, subtitle: n?.subtitle ?? '', slug: `videos/${stem}`, route: `/videos/${stem}/` };
  });
  const listFiles = (dir, sub = '') => fs.readdirSync(path.join(dir, sub), { withFileTypes: true }).flatMap((e) => {
    const p = sub ? `${sub}/${e.name}` : e.name;
    if (e.name.startsWith('.') || SKIP_DIRS.has(e.name)) return [];
    return e.isDirectory() ? listFiles(dir, p) : e.isFile() ? [p] : [];
  });
  const lessonsDir = path.join(KIT, '03-labs/lessons');
  const lessons = fs.readdirSync(lessonsDir, { withFileTypes: true })
    .filter((e) => e.isDirectory() && /^\d\d-/.test(e.name) && fs.existsSync(path.join(lessonsDir, e.name, 'README.md')))
    .map((e) => e.name).sort().map((dir) => {
      const rel = `03-labs/lessons/${dir}`;
      const md = read(`${rel}/README.md`);
      return { dir, rel, md, title: md.match(/^# +(.+)$/m)?.[1] ?? dir, files: listFiles(path.join(KIT, rel)).filter((f) => f !== 'README.md').sort(), slug: `lessons/${dir}`, route: `/lessons/${dir}/` };
    });
  const lb = '02-lab-book/field-engineer-lab-book.html';
  const cardIds = new Set(fs.existsSync(path.join(KIT, lb)) ? [...read(lb).matchAll(/\{\s*id:\s*'([FLT]\d)'/g)].map((m) => m[1]) : []);
  return { KIT, WEB, lessons, videos, narration, cardIds, readme, read };
}

// ---------- loading ----------
const META = new WeakMap(); // model -> what validateCourse needs (raw content, README parses, load problems)
const PAGE_KINDS = new Set(['get-the-code', 'product-criticism', 'lesson16-part2']);
const MODES = new Set(['all', 'rewatch', 'optional']);
const OVERVIEW_MIN = 2, WRAPUP_MIN = 10;

/**
 * Load the course. ctx: what sync.mjs has ({ KIT, WEB, lessons, videos, narration, cardIds, readme, read }),
 * plus optional contentDir (default COURSE_CONTENT_DIR or WEB/course/content) and day (validate only that
 * day's content file). Throws only when course.yaml itself cannot be read; everything else becomes a
 * problem for validateCourse, and the model is still built (missing text is null or []).
 */
export function loadCourse(ctx) {
  const WEB = ctx.WEB ?? HERE_WEB;
  const contentDir = path.resolve(ctx.contentDir ?? process.env.COURSE_CONTENT_DIR ?? path.join(WEB, 'course/content'));
  const onlyDay = ctx.day == null ? null : Number(ctx.day);
  const loadProblems = [];
  const P = (m) => loadProblems.push(m);

  const courseYaml = YAML.parse(fs.readFileSync(path.join(WEB, 'course/course.yaml'), 'utf8'));
  if (!Array.isArray(courseYaml?.days)) throw new Error('course/course.yaml has no days list');
  if (onlyDay != null && !courseYaml.days.some((d) => d.n === onlyDay)) throw new Error(`--day ${onlyDay}: course.yaml has no day ${onlyDay}`);

  const chaptersFile = path.join(WEB, 'chapters.txt');
  const chapters = fs.existsSync(chaptersFile) ? parseChapters(fs.readFileSync(chaptersFile, 'utf8')) : { map: new Map(), problems: ['chapters.txt is missing'] };
  chapters.problems.forEach(P);

  const lessonByDir = new Map(ctx.lessons.map((l) => [l.dir, l]));
  const videoByStem = new Map(ctx.videos.map((v) => [v.stem, v]));
  const narrationOf = (stem) => ctx.narration[stem.replace(/^\d\d-/, '')];
  const parsed = new Map(); // lesson dir -> parseReadme result
  const parseOf = (dir) => {
    if (!parsed.has(dir)) parsed.set(dir, parseReadme(lessonByDir.get(dir).md));
    return parsed.get(dir);
  };

  // content files: all that exist are loaded (warm-ups and site-wide checks need other days too)
  const content = new Map(); // day n -> { file, data, errors }
  for (const d of courseYaml.days) {
    const file = `day-${pad2(d.n)}.yaml`;
    const full = path.join(contentDir, file);
    if (!fs.existsSync(full)) { content.set(d.n, { file, data: null, missing: true, errors: [] }); continue; }
    const doc = YAML.parseDocument(fs.readFileSync(full, 'utf8'), { prettyErrors: true, uniqueKeys: true });
    const errors = doc.errors.map((e) => collapse(e.message));
    content.set(d.n, { file, data: errors.length ? null : doc.toJS(), missing: false, errors });
  }

  // chapters of a video: every scene but the EndCard
  const chaptersOf = (stem, from = 0, to = Infinity) => {
    const n = narrationOf(stem), times = chapters.map.get(stem);
    if (!n || !times) return [];
    return n.scenes.map((s, i) => ({ i, t: times[i], label: sceneLabel(stem.slice(3), i, s) }))
      .filter((c) => c.i >= from && c.i < to && c.label && c.t != null).map(({ t, label }) => ({ t, label }));
  };

  // lessons used by more than one step are split (lesson 16): Run commands and checks go by step
  const stepsOfLesson = new Map();
  for (const d of courseYaml.days) for (const s of d.steps ?? []) if (s.lesson) stepsOfLesson.set(s.lesson, [...(stepsOfLesson.get(s.lesson) ?? []), s]);

  const stepInfo = new Map(); // step id -> { yaml, readmeChecks, runCmds, lp, content } for validateCourse
  const days = [];
  const steps = [];
  for (const d of courseYaml.days) {
    const c = content.get(d.n)?.data ?? null;
    const cSteps = isObj(c?.steps) ? c.steps : {};
    const dayObj = {
      n: d.n, part: d.part, title: d.title, cost: d.cost, paid: !!d.paid, long: d.long ?? null, minutes: 0,
      route: `/course/day-${d.n}/`, wrapRoute: `/course/day-${d.n}/wrap-up/`, slug: `course/day-${d.n}`, wrapSlug: `course/day-${d.n}/wrap-up`,
      tile: c?.tile ?? null, overview: c?.overview ?? null, wrapup: c?.wrapup ?? null,
      warmup: [], fields: [], steps: [],
    };
    const ySteps = d.steps ?? [];
    ySteps.forEach((s, i) => {
      const cs = isObj(cSteps[s.id]) ? cSteps[s.id] : {};
      const lesson = s.lesson ? lessonByDir.get(s.lesson) ?? null : null;
      const lp = lesson ? parseOf(lesson.dir) : null;
      // which README checks and Run commands belong to this step
      let readmeChecks = lp?.checks ?? [];
      let runCmds = lp?.run ?? [];
      if (lesson && (stepsOfLesson.get(lesson.dir)?.length ?? 0) > 1) {
        if (Array.isArray(s.checks)) readmeChecks = s.checks.map((k) => lp.checks[k - 1]).filter(Boolean);
        const mine = s.files ?? [], all = stepsOfLesson.get(lesson.dir).flatMap((o) => o.files ?? []);
        runCmds = runCmds.filter((r) => mine.some((f) => r.text.includes(f)) || !all.some((f) => r.text.includes(f)));
      }
      const cChecks = Array.isArray(cs.checks) ? cs.checks : [];
      const step = {
        id: s.id, n: i + 1, of: ySteps.length, day: d.n, title: s.title, minutes: s.minutes, cost: s.cost,
        paid: !!s.paid, optional: s.optional ?? false, pos: 0, total: 0,
        route: s.page ? `/course/day-${d.n}/${s.slug}/` : `/lessons/${s.lesson}/`,
        slug: s.page ? `course/day-${d.n}/${s.slug}` : `lessons/${s.lesson}`,
        lesson, page: s.page ?? null, files: s.files ?? null, cards: s.cards ?? [], download: s.download ?? null,
        videos: (s.videos ?? []).map((v) => {
          const times = chapters.map.get(v.stem) ?? [];
          const [a, b] = Array.isArray(v.scenes) ? v.scenes : [null, null];
          const cv = v.mode === 'all' && isObj(cs.videos?.[v.stem]) ? cs.videos[v.stem] : null;
          return {
            stem: v.stem, mode: v.mode, note: v.note ?? null,
            from: a != null ? times[a] ?? null : null, to: b != null ? times[b] ?? null : null,
            video: videoByStem.get(v.stem) ?? null,
            chapters: a != null ? chaptersOf(v.stem, a, b) : chaptersOf(v.stem),
            in_this_video: cv?.in_this_video ?? null, key_points: Array.isArray(cv?.key_points) ? cv.key_points : [],
          };
        }),
        noVideo: s.no_video ?? null,
        checks: readmeChecks.map((k, j) => {
          const cc = isObj(cChecks[j]) ? cChecks[j] : {};
          return {
            n: j + 1, kitQ: k.kitQ, kitA: k.kitA, q: cc.q ?? null, plain: cc.plain ?? null, picture: cc.picture ?? null,
            numbers_source: cc.numbers_source ?? null, numbers: cc.numbers ?? [], words: cc.words ?? [], more: cc.more ?? null,
          };
        }),
        say: lesson && lp.say ? { line: lp.say, ask: cs.say?.ask ?? null, means: Array.isArray(cs.say?.means) ? cs.say.means : [] } : null,
        why: cs.why ?? null, why_example: cs.why_example ?? null, start_first: cs.start_first ?? null, plain: cs.plain ?? null,
        run: Array.isArray(cs.run) ? cs.run : [], see: cs.see ?? null, fields: Array.isArray(cs.fields) ? cs.fields : [],
        done: cs.done ?? null, stuck: Array.isArray(cs.stuck) ? cs.stuck : [], replace: Array.isArray(cs.replace) ? cs.replace : [],
        body: cs.body ?? null,
        prev: null, next: null,
      };
      stepInfo.set(s.id, { yaml: s, readmeChecks, runCmds, lp, content: cSteps[s.id] });
      dayObj.steps.push(step);
      steps.push(step);
    });
    dayObj.minutes = OVERVIEW_MIN + dayObj.steps.filter((s) => !s.optional).reduce((a, s) => a + (Number(s.minutes) || 0), 0) + WRAPUP_MIN;
    dayObj.fields = dayObj.steps.flatMap((s) => s.fields);
    days.push(dayObj);
  }
  steps.forEach((s, i) => { s.pos = i + 1; s.total = steps.length; });

  // warm-up: the first 3 checks of the previous day. When that day has fewer than 3 (day 2 has 2, the
  // capstone day 10 has none), earlier days top it up with checks the previous day's warm-up did not use,
  // so two days in a row never repeat a card. Optional steps (skippable) never feed a warm-up.
  days.forEach((d, i) => {
    const usedBefore = new Set(i > 0 ? days[i - 1].warmup : []);
    for (let j = i - 1; j >= 0 && d.warmup.length < 3; j--) {
      for (const c of days[j].steps.filter((s) => !s.optional).flatMap((s) => s.checks)) {
        if (d.warmup.length < 3 && (j === i - 1 || !usedBefore.has(c))) d.warmup.push(c);
      }
    }
  });

  // The spine (Next order: home, then per day overview, steps, wrap-up) and each step's prev / next.
  // title names the entry ("Step 2 · KV cache and context length"); label is the text of a Next button
  // that leads to it (spec 5.6). The day overview and wrap-up pages take their Next from the entry after
  // theirs; after the last wrap-up comes home again ("Course complete: back to the start").
  const spine = [{ route: '/', kind: 'home', id: 'home', title: 'Start here', label: 'Course complete: back to the start', minutes: null }];
  for (const d of days) {
    spine.push({ route: d.route, kind: 'day', id: `d${d.n}`, title: `Day ${d.n} · ${d.title}`, label: `${d.n === 1 ? 'Start' : 'Next:'} Day ${d.n} · ${d.title}`, minutes: d.minutes });
    for (const s of d.steps) {
      spine.push({ route: s.route, kind: 'step', id: s.id, title: `Step ${s.n} · ${s.title}`,
        label: s.n === 1 ? `Start step 1: ${s.title} (${minutesText(s.minutes)})` : `Next: Step ${s.n} · ${s.title} (${minutesText(s.minutes)})`, minutes: s.minutes });
    }
    spine.push({ route: d.wrapRoute, kind: 'wrapup', id: `d${d.n}-wrap`, title: `Day ${d.n} · Wrap-up and drill`, label: `Finish Day ${d.n}: wrap-up and drill (${minutesText(WRAPUP_MIN)})`, minutes: WRAPUP_MIN });
  }
  spine.forEach((e, i) => {
    if (e.kind !== 'step') return;
    const s = steps.find((x) => x.id === e.id);
    const p = spine[i - 1], n = spine[i + 1] ?? spine[0];
    s.prev = { route: p.route, label: p.title };
    s.next = { route: n.route, label: n.label, minutes: n.minutes };
  });

  // merged glossary (first definition wins; a different definition of the same term is a problem)
  const gloss = new Map(); // lower-case term -> { entry, day }
  const glossConflicts = [];
  for (const d of days) {
    const g = content.get(d.n)?.data?.glossary;
    if (!Array.isArray(g)) continue;
    g.forEach((e, i) => {
      if (!isObj(e) || typeof e.term !== 'string' || !e.term.trim()) return;
      const k = collapse(e.term).toLowerCase();
      const had = gloss.get(k);
      if (!had) gloss.set(k, { entry: { term: collapse(e.term), def: e.def ?? null, example: e.example ?? null }, day: d.n, i });
      else if (collapse(had.entry.def ?? '') !== collapse(e.def ?? '')) glossConflicts.push({ term: e.term, day: d.n, i, other: had.day });
    });
  }
  const glossary = [...gloss.values()].map((g) => g.entry).sort((a, b) => a.term.localeCompare(b.term, 'en', { sensitivity: 'base' }));

  const videoUses = new Map();
  for (const s of steps) for (const v of s.videos) videoUses.set(v.stem, [...(videoUses.get(v.stem) ?? []), { step: s, mode: v.mode, from: v.from, to: v.to }]);

  const model = { days, steps, spine, glossary, videoUses };
  META.set(model, { ctx, courseYaml, chapters, content, contentDir, onlyDay, loadProblems, stepInfo, parsed, parseOf, lessonByDir, videoByStem, narrationOf, glossConflicts });
  return model;
}

// ---------- validation ----------
const SCHEMA = {
  top: ['day', 'tile', 'overview', 'steps', 'wrapup', 'glossary'],
  overview: ['today', 'example', 'deliverable', 'expected', 'before', 'feeds'],
  before: ['title', 'body', 'command', 'after'],
  step: ['why', 'why_example', 'start_first', 'videos', 'plain', 'run', 'see', 'checks', 'say', 'fields', 'done', 'stuck', 'replace', 'body'],
  start_first: ['command', 'note'],
  video: ['in_this_video', 'key_points'],
  key_point: ['point', 'detail'],
  plain: ['lead', 'picture', 'numbers_source', 'numbers', 'words'],
  word: ['term', 'def'],
  run: ['cmd', 'note'],
  check: ['q', 'plain', 'picture', 'numbers_source', 'numbers', 'words', 'more'],
  say: ['ask', 'means'],
  mean: ['phrase', 'meaning'],
  field: ['id', 'label', 'hint', 'unit', 'meaning', 'example'],
  stuck: ['problem', 'fix'],
  replace: ['find', 'with'],
  wrapup: ['done', 'whiteboards'],
  whiteboard: ['video', 'q', 'given', 'plain', 'picture', 'steps', 'note', 'kit_q', 'kit_a', 'more', 'words'],
  glossary: ['term', 'def', 'example'],
};
// strings that are code or kit text, not learner prose: exempt from the "video N" rule (not from emoji)
const CODE_KEYS = new Set(['find', 'cmd', 'command', 'kit_q', 'kit_a']);

/**
 * Check the loaded course against the rules of spec section 3 (and the structure in course.yaml).
 * Returns a list of problems (strings, each naming the file and the place). opts.warnings, when an
 * array, receives notes that do not fail the build (style-guide lengths, kit quotes not found).
 */
export function validateCourse(model, opts = {}) {
  const meta = META.get(model);
  if (!meta) return ['validateCourse: this model was not made by loadCourse'];
  const { ctx, courseYaml, chapters, content, onlyDay, stepInfo, parseOf, lessonByDir, videoByStem, narrationOf, glossConflicts } = meta;
  const problems = [...meta.loadProblems];
  const warnings = Array.isArray(opts.warnings) ? opts.warnings : [];
  const P = (m) => problems.push(m);
  const W = (m) => warnings.push(m);

  // ----- structure: course.yaml, chapters.txt, the kit READMEs -----
  const ids = new Set();
  courseYaml.days.forEach((d, di) => {
    const where = `course.yaml day ${d.n}`;
    if (d.n !== di + 1) P(`${where}: days must be numbered 1, 2, 3 ... in order (found ${d.n} at position ${di + 1})`);
    for (const k of ['part', 'title', 'cost']) if (d[k] == null || d[k] === '') P(`${where}: missing ${k}`);
    if (!Array.isArray(d.steps) || !d.steps.length) P(`${where}: no steps`);
    for (const s of d.steps ?? []) {
      const w = `course.yaml ${s.id ?? `day ${d.n} step`}`;
      if (!/^d\d+-s\d+$/.test(s.id ?? '')) P(`${w}: id must look like d4-s2`);
      else if (!s.id.startsWith(`d${d.n}-`)) P(`${w}: id is in day ${d.n} but starts with ${s.id.split('-')[0]}`);
      if (ids.has(s.id)) P(`${w}: id used twice`);
      ids.add(s.id);
      if (!s.title) P(`${w}: missing title`);
      if (!Number.isInteger(s.minutes) || s.minutes <= 0) P(`${w}: minutes must be a whole number above 0`);
      if (s.cost == null || s.cost === '') P(`${w}: missing cost`);
      if (s.page) {
        if (!PAGE_KINDS.has(s.page)) P(`${w}: unknown page kind "${s.page}" (get-the-code, product-criticism or lesson16-part2)`);
        if (!/^[a-z0-9-]+$/.test(s.slug ?? '')) P(`${w}: a generated page needs a slug (lowercase, digits, -)`);
      } else if (!s.lesson) P(`${w}: needs a lesson or a page`);
      if (s.lesson && !lessonByDir.has(s.lesson)) P(`${w}: lesson ${s.lesson} is not a folder in 03-labs/lessons`);
      if (ctx.cardIds?.size) for (const c of s.cards ?? []) if (!ctx.cardIds.has(c)) P(`${w}: lab card ${c} is not in the lab book`);
      const lesson = lessonByDir.get(s.lesson);
      if (s.files) for (const f of s.files) if (lesson && !lesson.files.includes(f)) P(`${w}: files: ${f} is not in lessons/${s.lesson}`);
      for (const [i, v] of (s.videos ?? []).entries()) {
        const vw = `${w} videos[${i}] ${v.stem}`;
        if (!videoByStem.has(v.stem)) { P(`${vw}: not a video in the kit README table`); continue; }
        if (!MODES.has(v.mode)) P(`${vw}: mode must be all, rewatch or optional`);
        const n = narrationOf(v.stem);
        if (!n) { P(`${vw}: narration.json has no entry`); continue; }
        if (v.scenes != null) {
          const [a, b] = Array.isArray(v.scenes) ? v.scenes : [];
          if (!Number.isInteger(a) || !Number.isInteger(b) || a < 0 || b <= a || b > n.scenes.length) P(`${vw}: scenes must be [from, to) with 0 <= from < to <= ${n.scenes.length}`);
          if (v.mode === 'all') P(`${vw}: mode all plays the whole video; scenes are for rewatch and optional`);
        }
      }
      for (const k of ['title', 'cost', 'no_video', 'optional']) textRule(s[k], `${w} ${k}`, false);
      for (const [i, v] of (s.videos ?? []).entries()) textRule(v.note, `${w} videos[${i}].note`, false);
    }
    textRule(d.title, `${where} title`, false); textRule(d.cost, `${where} cost`, false); textRule(d.long, `${where} long`, false);
  });
  // split lessons: every README check belongs to exactly one step
  const byLesson = new Map();
  for (const d of courseYaml.days) for (const s of d.steps ?? []) if (s.lesson && lessonByDir.has(s.lesson)) byLesson.set(s.lesson, [...(byLesson.get(s.lesson) ?? []), s]);
  for (const [dir, ss] of byLesson) {
    const count = parseOf(dir).checks.length;
    if (ss.length > 1) {
      const seen = new Map();
      for (const s of ss) {
        if (!Array.isArray(s.checks)) { P(`course.yaml ${s.id}: lesson ${dir} is split over ${ss.map((x) => x.id).join(', ')}, so it needs checks: [...] (README items it owns)`); continue; }
        for (const k of s.checks) {
          if (!Number.isInteger(k) || k < 1 || k > count) P(`course.yaml ${s.id}: checks: ${k} is not a README item (1 to ${count})`);
          else if (seen.has(k)) P(`course.yaml ${s.id}: checks: item ${k} is also claimed by ${seen.get(k)}`);
          else seen.set(k, s.id);
        }
      }
      for (let k = 1; k <= count; k++) if (!seen.has(k)) P(`course.yaml: lesson ${dir} Check yourself item ${k} belongs to none of ${ss.map((x) => x.id).join(', ')}`);
      if (ss.some((s) => !s.files)) P(`course.yaml: lesson ${dir} is split over ${ss.map((x) => x.id).join(', ')}, so each needs files: [...]`);
    } else if (Array.isArray(ss[0].checks)) P(`course.yaml ${ss[0].id}: checks: [...] is only for lessons split over several steps`);
  }
  // chapters: every video has one time per scene, and every chapter a label
  for (const v of ctx.videos) {
    const n = narrationOf(v.stem);
    if (!n) continue;
    const times = chapters.map.get(v.stem);
    if (!times) P(`chapters.txt: no line for ${v.stem}`);
    else if (times.length !== n.scenes.length) P(`chapters.txt ${v.stem}: ${times.length} times, narration.json has ${n.scenes.length} scenes`);
    n.scenes.forEach((s, i) => {
      const label = sceneLabel(v.stem.slice(3), i, s);
      if (label === undefined) P(`course.mjs: no chapter label for ${v.stem} scene ${i} (${s.visual}); add it to KIND_LABELS`);
      else if (label) textRule(label, `chapter label ${v.stem} scene ${i}`, false);
    });
  }
  for (const stem of chapters.map.keys()) if (!videoByStem.has(stem)) P(`chapters.txt: ${stem} is not a video in the kit README table`);
  // every lesson README parses; kit text shown verbatim on course pages follows the page rules
  for (const l of ctx.lessons) {
    const lp = parseOf(l.dir);
    for (const e of lp.errors) P(`${l.rel}/README.md: ${e}`);
    const used = byLesson.has(l.dir);
    if (!used) continue;
    if (!lp.say) P(`${l.rel}/README.md: no "Explain what you learned" line`);
    if (!lp.hasRun) P(`${l.rel}/README.md: no "## Run" section`);
    for (const c of lp.checks) { textRule(c.kitQ, `${l.rel}/README.md Check yourself ${c.n} question`, false); textRule(c.kitA, `${l.rel}/README.md Check yourself ${c.n} answer`, false); }
    textRule(lp.say, `${l.rel}/README.md Say it line`, false);
  }

  // ----- content files -----
  const fieldIds = new Map(); // id -> "day-04.yaml steps.d4-s2.fields[0]"
  for (const d of courseYaml.days) {
    const c = content.get(d.n);
    const inScope = onlyDay == null || onlyDay === d.n;
    if (!c.data) {
      if (!inScope) continue;
      if (c.missing) P(`${c.file}: missing (expected in ${path.relative(ctx.WEB ?? HERE_WEB, meta.contentDir) || '.'}/)`);
      for (const e of c.errors) P(`${c.file}: YAML error: ${e}`);
      continue;
    }
    // field ids are collected from every loaded day, problems reported only for days in scope
    for (const s of d.steps ?? []) {
      const fs2 = stepInfo.get(s.id)?.content?.fields;
      if (!Array.isArray(fs2)) continue;
      fs2.forEach((f, i) => {
        if (!isObj(f) || typeof f.id !== 'string') return;
        const where = `${c.file} steps.${s.id}.fields[${i}]`;
        if (fieldIds.has(f.id)) { if (inScope) P(`${where}: id ${f.id} is also used at ${fieldIds.get(f.id)} (field ids are unique site-wide)`); }
        else fieldIds.set(f.id, where);
      });
    }
    if (!inScope) continue;
    validateDay(d, c);
  }
  for (const g of glossConflicts) {
    if (g.day === g.other) continue; // same file: validateDay reports it
    if (onlyDay != null && onlyDay !== g.day && onlyDay !== g.other) continue;
    P(`${content.get(g.day).file} glossary[${g.i}] "${g.term}": defined differently in ${content.get(g.other).file} (one definition per term, site-wide)`);
  }
  return problems;

  // "video N" and emoji rules on learner-facing text; code and kit quotes only get the emoji rule
  function textRule(v, where, code) {
    if (typeof v !== 'string') return;
    const e = v.match(EMOJI);
    if (e) P(`${where}: contains an emoji (${e[0]})`);
    if (!code) { const m = withoutCode(v).match(VIDEO_N); if (m) P(`${where}: says "${m[0]}"; name the video by its title, never by number`); }
  }
  function walkText(v, where, code = false) {
    if (typeof v === 'string') textRule(v, where, code);
    else if (Array.isArray(v)) v.forEach((x, i) => walkText(x, `${where}[${i}]`, code));
    else if (isObj(v)) {
      for (const [k, x] of Object.entries(v)) {
        // replace[].find quotes the kit README so it can take an emoji or "video N" out: never shown, never checked
        if (k === 'find' && /\.replace\[\d+\]$/.test(where)) continue;
        walkText(x, `${where}${where.endsWith('.yaml') ? ' ' : '.'}${k}`, code || CODE_KEYS.has(k));
      }
    }
  }
  function keys(obj, allowed, where) {
    if (!isObj(obj)) return false;
    for (const k of Object.keys(obj)) if (!allowed.includes(k)) P(`${where}: unknown key "${k}" (allowed: ${allowed.join(', ')})`);
    return true;
  }
  function str(obj, k, where, required = true) {
    const v = obj?.[k];
    if (v == null || v === '') { if (required) P(`${where}.${k}: missing`); return false; }
    if (typeof v !== 'string') { P(`${where}.${k}: must be text`); return false; }
    return true;
  }
  function list(obj, k, where, required = false) {
    const v = obj?.[k];
    if (v == null) { if (required) P(`${where}.${k}: missing`); return null; }
    if (!Array.isArray(v)) { P(`${where}.${k}: must be a list`); return null; }
    return v;
  }
  function wordsList(v, where, max) {
    if (v == null) return;
    if (!Array.isArray(v)) { P(`${where}: must be a list`); return; }
    v.forEach((w, i) => { if (keys(w, SCHEMA.word, `${where}[${i}]`)) { str(w, 'term', `${where}[${i}]`); str(w, 'def', `${where}[${i}]`); } else P(`${where}[${i}]: must be { term, def }`); });
    if (max && v.length > max) W(`${where}: ${v.length} words (the style guide says up to ${max})`);
  }
  function strList(v, where) {
    if (v == null) return;
    if (!Array.isArray(v) || v.some((x) => typeof x !== 'string')) P(`${where}: must be a list of text lines`);
  }

  function validateDay(d, c) {
    const F = c.file, data = c.data;
    if (!isObj(data)) { P(`${F}: must be a mapping (day, tile, overview, steps, wrapup, glossary)`); return; }
    keys(data, SCHEMA.top, F);
    walkText(data, F);
    if (data.day !== d.n) P(`${F}: day: must be ${d.n}`);
    if (str(data, 'tile', F) && words(data.tile) > 12) W(`${F} tile: ${words(data.tile)} words (max 12)`);
    // overview
    if (!isObj(data.overview)) P(`${F} overview: missing`);
    else {
      const o = data.overview, w = `${F} overview`;
      keys(o, SCHEMA.overview, w);
      str(o, 'today', w); str(o, 'deliverable', w);
      for (const k of ['example', 'expected', 'feeds']) str(o, k, w, false);
      (list(o, 'before', w) ?? []).forEach((b, i) => {
        if (!keys(b, SCHEMA.before, `${w}.before[${i}]`)) { P(`${w}.before[${i}]: must be { title, body, command, after }`); return; }
        str(b, 'title', `${w}.before[${i}]`);
        for (const k of ['body', 'command', 'after']) str(b, k, `${w}.before[${i}]`, false);
      });
    }
    // steps
    const cSteps = data.steps;
    if (!isObj(cSteps)) P(`${F} steps: missing`);
    const dayIds = (d.steps ?? []).map((s) => s.id);
    for (const id of Object.keys(isObj(cSteps) ? cSteps : {})) if (!dayIds.includes(id)) P(`${F} steps.${id}: not a step of day ${d.n} (steps: ${dayIds.join(', ')})`);
    for (const s of d.steps ?? []) {
      const cs = isObj(cSteps) ? cSteps[s.id] : undefined;
      const w = `${F} steps.${s.id}`;
      if (cs == null) { P(`${w}: missing`); continue; }
      if (!keys(cs, SCHEMA.step, w)) { P(`${w}: must be a mapping`); continue; }
      validateStep(s, cs, w);
    }
    // wrap-up
    if (!isObj(data.wrapup)) P(`${F} wrapup: missing`);
    else {
      const wu = data.wrapup, w = `${F} wrapup`;
      keys(wu, SCHEMA.wrapup, w);
      str(wu, 'done', w);
      const wbs = list(wu, 'whiteboards', w, true);
      if (wbs && (wbs.length < 1 || wbs.length > 2)) P(`${w}.whiteboards: ${wbs.length} items, expected 1 or 2`);
      const dayStems = new Set((d.steps ?? []).flatMap((s) => (s.videos ?? []).map((v) => v.stem)));
      (wbs ?? []).forEach((b, i) => {
        const ww = `${w}.whiteboards[${i}]`;
        if (!keys(b, SCHEMA.whiteboard, ww)) { P(`${ww}: must be a mapping`); return; }
        if (str(b, 'video', ww) && !dayStems.has(b.video)) P(`${ww}.video: ${b.video} is not a video of day ${d.n} (${[...dayStems].join(', ') || 'none'})`);
        str(b, 'q', ww); str(b, 'plain', ww);
        for (const k of ['given', 'picture', 'note', 'kit_q', 'kit_a', 'more']) str(b, k, ww, false);
        const st = list(b, 'steps', ww, true);
        if (st && !st.length) P(`${ww}.steps: empty`);
        strList(b.steps, `${ww}.steps`);
        wordsList(b.words, `${ww}.words`, 4);
        // kit_q / kit_a quote the video: often several narration fields stitched together ("heading ·
        // scenario", "row: value. answer"), so each longer piece must occur in that video's narration
        const n = videoByStem.has(b.video) ? narrationOf(b.video) : null;
        if (n) {
          const strings = [];
          const collect = (v) => { if (typeof v === 'string' || typeof v === 'number') strings.push(String(v)); else if (v && typeof v === 'object') Object.values(v).forEach(collect); };
          n.scenes.forEach((x) => { collect(x.params); collect(x.text); });
          const hay = collapse(strings.join('\n')).toLowerCase();
          for (const k of ['kit_q', 'kit_a']) {
            if (typeof b[k] !== 'string') continue;
            const missing = collapse(b[k]).split(/\s+·\s+|(?<=[.?!])\s+|:\s+|\s+—\s+/)
              .map((p) => p.trim().replace(/[.,;]$/, '')).filter((p) => p.length >= 12 && !hay.includes(p.toLowerCase()));
            if (missing.length) W(`${ww}.${k}: not verbatim from narration.json (${b.video}): "${missing.slice(0, 2).join('", "')}"${missing.length > 2 ? ` and ${missing.length - 2} more` : ''}`);
          }
        }
      });
    }
    // glossary
    const seen = new Map();
    (list(data, 'glossary', F, true) ?? []).forEach((g, i) => {
      const w = `${F} glossary[${i}]`;
      if (!keys(g, SCHEMA.glossary, w)) { P(`${w}: must be { term, def, example }`); return; }
      if (str(g, 'term', w)) {
        const k = collapse(g.term).toLowerCase();
        if (seen.has(k) && collapse(seen.get(k).def ?? '') !== collapse(g.def ?? '')) P(`${w} "${g.term}": defined twice in this file with different text`);
        seen.set(k, g);
      }
      str(g, 'def', w); str(g, 'example', w, false);
    });
  }

  function validateStep(s, cs, w) {
    const info = stepInfo.get(s.id);
    const lesson = s.lesson ? lessonByDir.get(s.lesson) : null;
    const lp = lesson ? parseOf(lesson.dir) : null;
    str(cs, 'why', w); str(cs, 'done', w);
    str(cs, 'why_example', w, false); str(cs, 'see', w, false);
    if (cs.start_first != null) {
      if (keys(cs.start_first, SCHEMA.start_first, `${w}.start_first`)) { str(cs.start_first, 'command', `${w}.start_first`); str(cs.start_first, 'note', `${w}.start_first`, false); }
      else P(`${w}.start_first: must be { command, note }`);
    }
    if (lesson) { if (cs.body != null) P(`${w}.body: only generated pages without a lesson (get-the-code, product-criticism) have a body`); }
    else str(cs, 'body', w);
    // In plain words
    if (lesson) {
      if (!isObj(cs.plain)) P(`${w}.plain: missing`);
      else {
        keys(cs.plain, SCHEMA.plain, `${w}.plain`);
        str(cs.plain, 'lead', `${w}.plain`);
        for (const k of ['picture', 'numbers_source']) str(cs.plain, k, `${w}.plain`, false);
        strList(cs.plain.numbers, `${w}.plain.numbers`);
        if (Array.isArray(cs.plain.numbers) && (cs.plain.numbers.length < 3 || cs.plain.numbers.length > 6)) W(`${w}.plain.numbers: ${cs.plain.numbers.length} lines (the spec says 3 to 6)`);
        wordsList(cs.plain.words, `${w}.plain.words`, 4);
      }
    } else if (cs.plain != null && !isObj(cs.plain)) P(`${w}.plain: must be a mapping`);
    // videos: one entry per mode-all video, exactly 3 key points
    const allStems = (s.videos ?? []).filter((v) => v.mode === 'all').map((v) => v.stem);
    const cv = cs.videos;
    if (cv != null && !isObj(cv)) P(`${w}.videos: must be a mapping of video stems`);
    for (const k of Object.keys(isObj(cv) ? cv : {})) if (!allStems.includes(k)) P(`${w}.videos.${k}: not a mode-all video of this step (${allStems.join(', ') || 'none'})`);
    for (const stem of allStems) {
      const v = isObj(cv) ? cv[stem] : undefined, vw = `${w}.videos.${stem}`;
      if (v == null) { P(`${vw}: missing (every mode-all video needs in_this_video and 3 key_points)`); continue; }
      if (!keys(v, SCHEMA.video, vw)) { P(`${vw}: must be a mapping`); continue; }
      str(v, 'in_this_video', vw);
      const kp = list(v, 'key_points', vw, true);
      if (kp) {
        if (kp.length !== 3) P(`${vw}.key_points: ${kp.length} items, expected exactly 3`);
        kp.forEach((p, i) => { if (keys(p, SCHEMA.key_point, `${vw}.key_points[${i}]`)) { str(p, 'point', `${vw}.key_points[${i}]`); str(p, 'detail', `${vw}.key_points[${i}]`, false); } else P(`${vw}.key_points[${i}]: must be { point, detail }`); });
      }
    }
    // Run notes: every cmd is a Run command of the lesson (this step's part of it), every Run command has a note
    const run = list(cs, 'run', w);
    const cmds = info.runCmds;
    if (run && !lesson) { if (run.length) P(`${w}.run: this step has no lesson, so no Run block to annotate`); }
    else if (lesson) {
      const have = new Map(); // key -> occurrences in the README
      for (const c of cmds) have.set(c.key, (have.get(c.key) ?? 0) + 1);
      const used = new Map();
      let lastAt = -1, outOfOrder = false;
      (run ?? []).forEach((r, i) => {
        const rw = `${w}.run[${i}]`;
        if (!keys(r, SCHEMA.run, rw)) { P(`${rw}: must be { cmd, note }`); return; }
        if (!str(r, 'cmd', rw)) return;
        str(r, 'note', rw);
        const k = runKey(r.cmd);
        if (!have.has(k)) { P(`${rw}.cmd: "${r.cmd}" is not a Run command of lessons/${s.lesson}${s.files ? ` (${s.files.join(', ')} part)` : ''}. Commands: ${[...have.keys()].map((x) => `"${x}"`).join(', ')}`); return; }
        used.set(k, (used.get(k) ?? 0) + 1);
        if (used.get(k) > have.get(k)) P(`${rw}.cmd: "${k}" has more notes than it has lines in the Run block (${have.get(k)})`);
        const at = cmds.findIndex((c, j) => c.key === k && j > lastAt);
        if (at < 0) outOfOrder = true; else lastAt = at;
      });
      for (const k of have.keys()) if (!used.has(k)) P(`${w}.run: no note for the Run command "${k}" (README line ${cmds.find((c) => c.key === k).line})`);
      if (outOfOrder) W(`${w}.run: notes are not in the Run block's order`);
    }
    // checks: one per README item of this step, same order
    const need = info.readmeChecks.length;
    const checks = cs.checks;
    if (checks != null && !Array.isArray(checks)) P(`${w}.checks: must be a list`);
    else {
      const got = Array.isArray(checks) ? checks.length : 0;
      const src = lesson ? `README${s.checks ? ` items ${s.checks.join(', ')}` : ''}` : 'a page without a lesson';
      if (lesson && need && checks == null) P(`${w}.checks: missing (${src} has ${need})`);
      else if (got !== need) P(`${w}.checks: ${got} items, ${src} has ${need}`);
      (checks ?? []).forEach((q, i) => {
        const qw = `${w}.checks[${i}]`;
        if (!keys(q, SCHEMA.check, qw)) { P(`${qw}: must be a mapping`); return; }
        str(q, 'q', qw); str(q, 'plain', qw);
        for (const k of ['picture', 'numbers_source', 'more']) str(q, k, qw, false);
        strList(q.numbers, `${qw}.numbers`);
        wordsList(q.words, `${qw}.words`, 4);
      });
    }
    // Say it
    if (lesson && lp.say) {
      if (!isObj(cs.say)) P(`${w}.say: missing`);
      else {
        keys(cs.say, SCHEMA.say, `${w}.say`);
        str(cs.say, 'ask', `${w}.say`);
        const means = list(cs.say, 'means', `${w}.say`, true);
        const line = collapse(lp.say).toLowerCase().replace(/[’‘]/g, "'");
        let from = 0;
        (means ?? []).forEach((m, i) => {
          const mw = `${w}.say.means[${i}]`;
          if (!keys(m, SCHEMA.mean, mw)) { P(`${mw}: must be { phrase, meaning }`); return; }
          if (str(m, 'phrase', mw)) {
            const ph = collapse(m.phrase).toLowerCase().replace(/[’‘]/g, "'").replace(/^["“]|["”]$/g, '');
            const at = line.indexOf(ph, from);
            if (at >= 0) from = at + ph.length;
            else W(`${mw}.phrase: "${m.phrase}" is not ${line.includes(ph) ? 'in order in' : 'in'} the kit line`);
          }
          str(m, 'meaning', mw);
        });
      }
    } else if (cs.say != null) P(`${w}.say: this step's lesson has no "Explain what you learned" line`);
    // fields
    (list(cs, 'fields', w) ?? []).forEach((f, i) => {
      const fw = `${w}.fields[${i}]`;
      if (!keys(f, SCHEMA.field, fw)) { P(`${fw}: must be a mapping`); return; }
      if (str(f, 'id', fw)) {
        if (!/^[a-z0-9][a-z0-9-]*$/.test(f.id)) P(`${fw}.id: "${f.id}" must be lowercase letters, digits and -`);
        else if (!f.id.startsWith(`d${s.id.split('-')[0].slice(1)}-`)) W(`${fw}.id: "${f.id}" does not start with d${s.id.split('-')[0].slice(1)}- (keeps ids unique across days)`);
      }
      str(f, 'label', fw);
      for (const k of ['hint', 'unit', 'meaning', 'example']) str(f, k, fw, false);
    });
    (list(cs, 'stuck', w) ?? []).forEach((x, i) => { if (keys(x, SCHEMA.stuck, `${w}.stuck[${i}]`)) { str(x, 'problem', `${w}.stuck[${i}]`); str(x, 'fix', `${w}.stuck[${i}]`); } else P(`${w}.stuck[${i}]: must be { problem, fix }`); });
    // replace: every find occurs in the README
    const reps = list(cs, 'replace', w) ?? [];
    reps.forEach((r, i) => {
      const rw = `${w}.replace[${i}]`;
      if (!keys(r, SCHEMA.replace, rw)) { P(`${rw}: must be { find, with }`); return; }
      if (!str(r, 'find', rw)) return;
      if (typeof r.with !== 'string') P(`${rw}.with: must be text (may be empty)`);
      if (!lesson) P(`${rw}: this step has no lesson README to change`);
      else if (!lesson.md.includes(r.find)) P(`${rw}.find: "${r.find}" does not occur in ${lesson.rel}/README.md`);
    });
    // the README text this lesson page shows must follow the page rules too (replace fixes it)
    if (lesson && !s.page) {
      let fence = null;
      for (const { n, line } of shownReadme(lesson.md, reps)) {
        const f = line.replace(/^\s*>\s?/, '').match(/^\s*(`{3,}|~{3,})/);
        const e = line.match(EMOJI);
        if (e) P(`${w}: the lesson README shown on this page has an emoji (${e[0]}) at line ${n}: "${quoteSnip(line, line.indexOf(e[0]))}"; add a replace`);
        if (fence) { if (f && f[1][0] === fence[0]) fence = null; continue; }
        if (f) { fence = f[1]; continue; }
        const m = withoutCode(line).match(VIDEO_N);
        if (m) P(`${w}: the lesson README shown on this page says "${m[0]}" at line ${n}: "${quoteSnip(line, line.indexOf(m[0]))}"; add a replace`);
      }
    }
  }
}

// ---------- CLI ----------
function cli(argv) {
  const arg = (name) => { const i = argv.indexOf(name); return i >= 0 ? argv[i + 1] : undefined; };
  const check = argv.includes('--check'), dump = argv.includes('--dump');
  if (!check && !dump) {
    console.error('usage: node scripts/course.mjs --check [--day N] [--content DIR]\n       node scripts/course.mjs --dump [--day N] [--content DIR]');
    return 2;
  }
  const day = arg('--day');
  if (day != null && !/^\d+$/.test(day)) { console.error(`--day needs a day number, got "${day}"`); return 2; }
  const KIT = path.resolve(process.env.KIT_DIR ?? path.join(HERE_WEB, '..'));
  const ctx = { ...kitContext(KIT, HERE_WEB), day: day == null ? undefined : Number(day), contentDir: arg('--content') };
  const model = loadCourse(ctx);
  const warnings = [];
  const problems = validateCourse(model, { warnings });
  if (dump) {
    const slim = (k, v) => {
      if (v instanceof Map) return Object.fromEntries(v);
      if (k === 'lesson' && v) return v.dir;
      if (k === 'video' && v) return v.stem;
      if (k === 'step' && v?.id) return v.id;
      return v;
    };
    console.log(JSON.stringify(model, slim, 2));
  }
  const scope = day == null ? `all ${model.days.length} days` : `day ${day}`;
  const out = dump ? console.error : console.log; // --dump keeps stdout for the JSON
  for (const w of warnings) out(`note: ${w}`);
  for (const p of problems) out(`problem: ${p}`);
  out(problems.length
    ? `course: ${problems.length} problem(s) (${scope}, content from ${path.relative(process.cwd(), META.get(model).contentDir) || '.'})`
    : `course: OK (${scope}: ${model.days.length} days, ${model.steps.length} steps, ${warnings.length} note(s))`);
  return problems.length ? 1 : 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  try { process.exitCode = cli(process.argv.slice(2)); }
  catch (e) { console.error(`course: ${e.message}`); process.exitCode = 2; }
}
