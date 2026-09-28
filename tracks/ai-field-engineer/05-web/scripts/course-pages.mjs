// Course page templates (docs/course-spec.md sections 5 and 6.3). Pure functions: the course model from
// scripts/course.mjs in, page markdown out, so scripts/sync.mjs decides where each page is written.
//
// Pages stay .md with raw HTML blocks. Rules every function here keeps:
// - A raw HTML chunk starts with a block tag (div, section, details, nav, ol, p) and contains no blank line,
//   so markdown never re-parses its inside. Markdown (headings for the table of contents, fenced code for
//   commands) sits between chunks, separated by blank lines.
// - Every content field goes through inlineMd(): escaped first, then **bold**, *em*, `code` and links.
// - Every reveal is a native <details>, so answers stay hidden and open without JavaScript.
// - Only the data-kit-* attributes of the DOM contract (spec 6.3) are emitted; kit.js adds state.
// - No video file numbers and no lab card ids are printed on course pages.
// Classes are prefixed kc- (styles in src/styles/course.css); each chunk root carries `kc not-content`, so
// Starlight's markdown styles leave it alone.

const LAB_BOOK = '/lab-book/field-engineer-lab-book.html';
const DOWNLOAD_ZIP = '/downloads/03-labs.zip';
// The narrator of these videos ends by naming the next file; the course order differs (spec 5.4 item 4).
const NARRATOR_NEXT = new Set(['01', '02', '04', '05', '06', '07', '08', '13']);
const PART_NAME = { 1: 'Serving', 2: 'Training' };

// ---------- small helpers ----------

export function esc(s) {
  return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
/**
 * Plain text for a markdown heading (## ...): escaped as esc() does, then markdown's own characters
 * backslash-escaped, so a title shows as written, as it does in the HTML around it (no emphasis, code,
 * links or raw HTML).
 */
export function mdPlain(s) {
  return esc(String(s ?? '').replace(/\s+/g, ' ').trim()).replace(/[\\`*_[\]{}()#+!|~-]/g, '\\$&');
}

// One raw HTML chunk: drop empty lines (a blank line would end the HTML block) and falsy parts.
function raw(...parts) {
  return parts.flat(Infinity).filter((p) => typeof p === 'string' && p !== '')
    .join('\n').split('\n').map((l) => l.trimEnd()).filter((l) => l.trim()).join('\n');
}
// A page body: chunks (raw HTML or markdown) separated by one blank line.
function body(...chunks) {
  return chunks.flat(Infinity).filter((c) => typeof c === 'string' && c.trim()).map((c) => c.trim()).join('\n\n');
}
const fence = (src) => '`'.repeat(Math.max(3, ...[...String(src).matchAll(/`+/g)].map((m) => m[0].length + 1)));
function codeFence(src, lang = 'bash', meta = '') {
  const s = String(src).replace(/\s+$/, '');
  const f = fence(s);
  return `${f}${lang}${meta ? ` ${meta}` : ''}\n${s}\n${f}`;
}
// Fields shown as a paragraph of their own start with a capital letter (the content files often continue
// a label: "Why this step: you make..."). Command-like first words are left alone.
const KEEP_LOWER = new Set(['pip', 'python', 'python3', 'bash', 'make', 'cd', 'ollama', 'firectl', 'llama', 'mlx', 'npm', 'git', 'brew', 'curl', 'sh']);
function capFirst(text) {
  const s = String(text ?? '');
  const m = s.match(/^([a-z][a-z']*)(?=[\s,;:])/);
  return m && !KEEP_LOWER.has(m[1]) ? s[0].toUpperCase() + s.slice(1) : s;
}

const CODE_SPAN = /(?<!`)(`+)(?!`)([\s\S]*?[^`])\1(?!`)/g; // CommonMark: closes on a run of the same length
// A browser reads a backslash as a slash ("/\host" is "//host", another site): no backslash anywhere.
const SAFE_HREF = /^(\/(?![/\\])[^\s\\]*|#[^\s\\]*|https:\/\/[^\s\\]+)$/;

// Course links to the lab book carry ?from=<route> so its back bar returns here (spec 5.8).
function withFrom(href, from) {
  if (!from || !href.startsWith('/lab-book/') || /[?&]from=/.test(href)) return href;
  const m = href.match(/^([^?#]*)(\?[^#]*)?(#.*)?$/);
  return `${m[1]}${m[2] ? `${m[2]}&` : '?'}from=${from}${m[3] ?? ''}`;
}

// Straight quotes to curly ones, as Astro's smartypants does for the markdown around these blocks.
function smartQuotes(s) {
  // A quote that opens a **bold** or *em* run ("**"Where does ...?"**") opens too: markdown stars come first.
  return s
    .replace(/(^|[\s([{—–/-])(\*{0,2})"/g, '$1$2“').replace(/"/g, '”')
    .replace(/(^|[\s([{—–/-])(\*{0,2})'/g, '$1$2‘').replace(/'/g, '’');
}

/**
 * Inline markdown to safe HTML: the text is escaped first, then `code`, [text](href), **bold** and *em*
 * become tags. Links are kept only for same-site paths, #anchors and https URLs (other targets keep their
 * text). Line breaks become spaces, a blank line a <br>, so the result never ends a raw HTML block.
 * opts.from adds ?from=<route> to lab book links; opts.links === false keeps link text only (inside <a>).
 */
export function inlineMd(text, opts = {}) {
  if (text === null || text === undefined) return '';
  let s = String(text).replace(/\r\n?/g, '\n').trim();
  if (!s) return '';
  const codes = [];
  const links = [];
  s = s.replace(CODE_SPAN, (_, ticks, code) => {
    const c = ticks.length > 1 ? code.trim() : code;
    return `\u0001${codes.push(`<code>${esc(c.replace(/\s*\n\s*/g, ' '))}</code>`) - 1}\u0001`;
  });
  s = s.replace(/\[([^\]\n]+)\]\(\s*<?((?:[^()\s<>]|\([^()\s]*\))+)>?\s*\)/g, (all, label, href) => {
    if (opts.links === false || !SAFE_HREF.test(href)) return label;
    return `\u0002${links.push(withFrom(href, opts.from)) - 1}\u0002${label}\u0003`;
  });
  s = esc(smartQuotes(s));
  s = s.replace(/\*\*(?=\S)([\s\S]*?\S)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^\w*])\*(?=[^\s*])([^*\n]*?[^\s*])\*(?![\w*])/g, '$1<em>$2</em>');
  s = s.replace(/[ \t]*\n[ \t]*\n\s*/g, '<br>').replace(/\s*\n\s*/g, ' ');
  s = s.replace(/\u0002(\d+)\u0002/g, (_, i) => `<a href="${esc(links[Number(i)])}">`).replace(/\u0003/g, '</a>');
  return s.replace(/\u0001(\d+)\u0001/g, (_, i) => codes[Number(i)]);
}
const md = inlineMd;

/** Minutes as "45 min", "1 h 05", "2 h". */
export function fmtMin(m) {
  const n = Math.max(0, Math.round(Number(m) || 0));
  if (n < 60) return `${n} min`;
  const h = Math.floor(n / 60);
  const r = n % 60;
  return r ? `${h} h ${String(r).padStart(2, '0')}` : `${h} h`;
}
/** A total rounded to 5 minutes: "about 1 h 55", "about 45 min" (spec 2.1). */
export function aboutMin(m) {
  return `about ${fmtMin(Math.max(5, Math.round((Number(m) || 0) / 5) * 5))}`;
}
/** Seconds as "1:05". */
export function fmtTime(t) {
  const s = Math.max(0, Math.floor(Number(t) || 0));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}
const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s);
const costText = (c) => (!c ? '' : /^free$/i.test(String(c).trim()) ? 'Free' : cap(String(c).trim()));
const mbText = (bytes) => (bytes ? `${(bytes / 1e6).toFixed(1)} MB` : '');
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
const idOf = (s) => String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

function dayOf(step, model) {
  if (step.day && typeof step.day === 'object') return step.day;
  return model.days.find((d) => d.n === Number(step.day)) ?? { n: Number(step.day), part: 1, title: '', route: '/', steps: [] };
}
const dayLabel = (day, model) => `Part ${day.part} · Day ${day.n} of ${model.days.length}`;
const stepVideos = (step) => (step.videos ?? []).filter((v) => v && v.video);
const allVideos = (step) => stepVideos(step).filter((v) => v.mode === 'all');
const segVideos = (step) => stepVideos(step).filter((v) => v.mode !== 'all');

// Where a lesson runs, from the kit README's lessons table ("Mac → FW", "FW **$**", "Spark", "anywhere").
const PLACE = [[/\bmac\b/i, 'Mac'], [/\bfw\b|fireworks/i, 'Fireworks'], [/spark/i, 'DGX Spark'], [/anywhere/i, 'Anywhere']];
function placesOf(runsOn) {
  if (!runsOn) return [];
  return PLACE.filter(([re]) => re.test(runsOn)).map(([, name]) => name);
}
// Generated steps have no README row: getting the code runs on the Mac, the criticism is writing.
const PAGE_PLACE = { 'get-the-code': 'Mac', 'product-criticism': 'anywhere' };
const stepRunsOn = (s) => s.lesson?.info?.runsOn ?? PAGE_PLACE[s.page];
function runsOnText(step) {
  const p = placesOf(stepRunsOn(step));
  if (!p.length) return '';
  return p.length === 2 && p[0] === 'Mac' && p[1] === 'Fireworks' ? 'Mac, then Fireworks' : p.join(' and ');
}
function dayPlaces(day) {
  const set = new Set(day.steps.filter((s) => !s.optional).flatMap((s) => placesOf(stepRunsOn(s))));
  if (set.size > 1) set.delete('Anywhere');
  return [...set].join(' and ');
}
// Big model downloads: course.yaml `download` when set (new downloads only), else the lesson README's
// own figure ("≈17 GB download").
function downloadGb(step) {
  if (step.download != null) return Number(step.download);
  const m = step.lesson?.md?.match(/≈\s*([\d.]+)\s*GB download/);
  return m ? Number(m[1]) : 0;
}
const dayDownloadGb = (day) => Math.max(0, ...day.steps.filter((s) => !s.optional).map(downloadGb));

function skipLabel(optional) {
  const m = String(optional ?? '').match(/^needs (an?|the) (.+?)\.?$/i);
  return m ? `Skip: I don't have ${m[1].toLowerCase()} ${m[2]}` : 'Skip this step';
}

// The day a video is first played in full (for "Rewatch from Day 3: ...").
function firstFullUse(stem, model) {
  const uses = model.videoUses?.get?.(stem);
  if (uses) {
    for (const u of uses) {
      if (u.mode !== 'all') continue;
      const st = typeof u.step === 'object' ? u.step : model.steps.find((s) => s.id === u.step);
      if (st) return st;
    }
  }
  return model.steps.find((s) => stepVideos(s).some((v) => v.stem === stem && v.mode === 'all')) ?? null;
}
function usesOf(stem, model) {
  const out = [];
  for (const s of model.steps) for (const v of stepVideos(s)) if (v.stem === stem) out.push({ step: s, mode: v.mode, from: v.from, to: v.to });
  return out;
}

// ---------- shared components ----------

function chip(cls, text, extra = '') {
  return text ? `<span class="kc-chip ${cls}"${extra}>${text}</span>` : '';
}
function costChip(cost, paid) {
  if (!cost) return '';
  return chip(paid ? 'kc-chip-cost kc-chip-paid' : /^free/i.test(cost) ? 'kc-chip-cost kc-chip-free' : 'kc-chip-cost',
    `${paid && !String(cost).includes('$') ? '<span class="kc-dollar" aria-hidden="true">$</span>' : ''}${esc(costText(cost))}`);
}
function doneButton(id) {
  return `<button type="button" class="kc-btn kc-mark" data-kit-done="${esc(id)}" aria-pressed="false">Mark done</button>`;
}
function skipButton(step) {
  return step.optional ? `<button type="button" class="kc-btn kc-skip" data-kit-skip="${esc(step.id)}">${esc(skipLabel(step.optional))}</button>` : '';
}

function wordsBlock(words, cls = '') {
  if (!words?.length) return '';
  return raw(`<div class="kc-words ${cls}">`, '<p class="kc-label">Words to know</p>', '<dl>',
    words.map((w) => `<div><dt>${md(w.term)}</dt><dd>${md(capFirst(w.def))}</dd></div>`), '</dl>', '</div>');
}
function numbersBlock(c, opts) {
  if (!c.numbers?.length) return '';
  return raw('<div class="kc-numbers">',
    `<p class="kc-label-row"><span class="kc-label kc-accent">With real numbers</span>${c.numbers_source ? `<span class="kc-source">${md(c.numbers_source, opts)}</span>` : ''}</p>`,
    '<ul>', c.numbers.map((n) => `<li>${md(n, opts)}</li>`), '</ul>', '</div>');
}
function pictureBlock(text, opts) {
  return text ? raw('<div class="kc-picture">', '<p class="kc-label kc-warm">Picture it</p>', `<p>${md(capFirst(text), opts)}</p>`, '</div>') : '';
}
function plainBox(text, label = 'In plain words', opts) {
  return text ? raw('<div class="kc-plainbox">', `<p class="kc-label kc-accent">${label}</p>`, `<p>${md(capFirst(text), opts)}</p>`, '</div>') : '';
}
const stripMore = (s) => String(s ?? '').replace(/^\s*\**more detail:?\**:?\s*/i, '');
function deeperBlock({ kitQ, kitA, more, given }, opts) {
  if (!kitQ && !kitA && !more) return '';
  return raw('<details class="kc-deeper">', '<summary>Go deeper: the engineer version</summary>', '<div class="kc-deeper-body">',
    kitQ && `<p class="kc-label">The kit's question</p><p class="kc-kitq">${md(kitQ, opts)}</p>`,
    given && `<p class="kc-kit-given">${md(given, opts)}</p>`,
    kitA && `<p class="kc-label">The kit's answer</p><blockquote class="kc-kita"><p>${md(kitA, opts)}</p></blockquote>`,
    more && `<p class="kc-more"><strong>More detail:</strong> ${md(stripMore(more), opts)}</p>`,
    '</div>', '</details>');
}
// The layers under a check: In plain words, Picture it, With real numbers, Words to know, Go deeper.
function checkLayers(c, opts) {
  return raw(plainBox(c.plain, 'In plain words', opts),
    '<div class="kc-layers">', '<div class="kc-layers-main">', pictureBlock(c.picture, opts), numbersBlock(c, opts), '</div>',
    wordsBlock(c.words), '</div>',
    deeperBlock({ kitQ: c.kitQ, kitA: c.kitA, more: c.more }, opts));
}

const toggle = (closed, open) =>
  `<span class="kc-toggle"><span class="kc-when-closed">${closed}</span><span class="kc-when-open">${open}</span></span>`;

// One "Check yourself" item: question in the summary, all layers behind it.
function checkDetails(c, i, opts, { id } = {}) {
  return raw(`<details class="kc-check"${id ? ` id="${esc(id)}"` : ''}>`,
    `<summary><span class="kc-check-n" aria-hidden="true">${i + 1}</span><span class="kc-check-q">${md(c.q ?? c.kitQ, opts)}</span>${toggle('Show answer', 'Hide')}</summary>`,
    '<div class="kc-check-body">', checkLayers(c, opts), '</div>', '</details>');
}

/**
 * The big Next link (spec 5.6). Takes a step (uses step.next), a day (the overview's Next: its first step),
 * or a ready { route, label } target. opts: { sub, eyebrow }.
 */
export function nextButton(x, model, opts = {}) {
  let next = null;
  if (x && Array.isArray(x.steps)) next = dayNext(x);
  else if (x && x.next !== undefined) next = x.next;
  else if (x && x.route) next = x;
  if (!next || !next.route) return '';
  const label = String(next.label ?? '');
  const eyebrow = opts.eyebrow ?? (/^next\b/i.test(label) ? '' : 'Next');
  // data-kit-next: kit.js's Skip follows this link (the page's own Next) before it falls back to the spine
  return `<a class="kc-next" href="${esc(next.route)}" rel="next" data-kit-next>` +
    `<span class="kc-next-text">${eyebrow ? `<span class="kc-next-k">${esc(eyebrow)}</span>` : ''}` +
    `<span class="kc-next-t">${esc(label)}</span>${opts.sub ? `<span class="kc-next-s">${md(opts.sub, { links: false })}</span>` : ''}</span></a>`;
}
function dayNext(day) {
  const first = day.steps?.[0];
  if (!first) return null;
  return { route: first.route, label: `Start step 1: ${first.title} (${fmtMin(first.minutes)})` };
}
function wrapupNext(day, model) {
  const nextDay = model.days.find((d) => d.n === day.n + 1);
  if (!nextDay) return { target: { route: '/', label: 'Course complete: back to the start' }, sub: '' };
  const sub = `${cap(aboutMin(nextDay.minutes))}, ${costText(nextDay.cost).toLowerCase() === 'free' ? 'free' : nextDay.cost}.`;
  return { target: { route: nextDay.route, label: `Next: Day ${nextDay.n} · ${nextDay.title}` }, sub };
}

// ---------- videos ----------

function playerTag(v, { from, to } = {}) {
  const frag = Number.isFinite(from) ? `#t=${Math.round(from * 10) / 10}${Number.isFinite(to) ? `,${Math.round(to * 10) / 10}` : ''}` : '';
  return `<video class="kc-player" controls playsinline preload="metadata" poster="${esc(v.poster)}"><source src="${esc(v.src)}${frag}" type="video/mp4"></video>`;
}
function chaptersBlock(chapters) {
  if (!chapters?.length) return '';
  return raw('<div class="kc-chapters">', '<p class="kc-label">Chapters</p>', '<ol>',
    chapters.map((c) => `<li><button type="button" data-kit-seek="${esc(Math.round(Number(c.t) * 10) / 10)}"><span class="kc-time">${fmtTime(c.t)}</span><span class="kc-ch-label">${md(c.label, { links: false })}</span></button></li>`),
    '</ol>', '</div>');
}
function keyPointsBlock(points, opts) {
  if (!points?.length) return '';
  return raw('<div class="kc-keypoints">', `<p class="kc-label kc-accent">${points.length} key points</p>`, '<ol>',
    points.map((p, i) => `<li><span class="kc-kp-n" aria-hidden="true">${i + 1}</span><div><p class="kc-kp-point">${md(capFirst(p.point ?? p), opts)}</p>${p.detail ? `<p class="kc-kp-detail">${md(capFirst(p.detail), opts)}</p>` : ''}</div></li>`),
    '</ol>', '</div>');
}
function downloadLink(v) {
  return `<a class="kc-dl" href="${esc(v.src)}" download="${esc(v.fileName)}">Download mp4${v.size ? ` (${mbText(v.size)})` : ''}</a>`;
}

// A whole video, open, with chapters and key points (mode: all).
function videoFull(sv, opts) {
  const v = sv.video;
  const narr = NARRATOR_NEXT.has(String(sv.stem ?? v.stem).slice(0, 2));
  return raw('<div class="kc-video kc not-content" data-kit-video>',
    '<div class="kc-video-head">',
    `<p class="kc-video-title"><strong>${esc(v.title)}</strong><span class="kc-dim"> · ${esc(v.min)}</span></p>`,
    downloadLink(v), '</div>',
    sv.note && `<p class="kc-video-note">${md(capFirst(sv.note), opts)}</p>`,
    `<div class="kc-video-grid${sv.chapters?.length ? '' : ' kc-no-chapters'}">`,
    `<div class="kc-frame">${playerTag(v)}</div>`,
    chaptersBlock(sv.chapters), '</div>',
    sv.in_this_video && `<p class="kc-in-video"><span class="kc-label">In this video</span> ${md(sv.in_this_video, opts)}</p>`,
    narr && '<p class="kc-narrator">The narrator’s “next video” is the file order. Your next step is below.</p>',
    keyPointsBlock(sv.key_points, opts),
    '</div>');
}
// A rewatch or optional segment: collapsed; the player starts at `from` and stops at `to`.
function videoSegment(sv, step, model, opts) {
  const v = sv.video;
  const first = firstFullUse(sv.stem ?? v.stem, model);
  const firstDay = first ? dayOf(first, model).n : null;
  const range = Number.isFinite(sv.from) ? `${fmtTime(sv.from)} to ${Number.isFinite(sv.to) ? fmtTime(sv.to) : v.min}` : v.min;
  const fromDay = firstDay && firstDay !== dayOf(step, model).n ? `from Day ${firstDay}: ` : '';
  const text = sv.mode === 'rewatch' ? `Rewatch ${fromDay}${v.title}, ${range}` : `Optional: ${v.title}${fromDay ? ` (${fromDay.replace(/: $/, '')})` : ''}, ${range}`;
  const attrs = [Number.isFinite(sv.from) && ` data-kit-from="${esc(sv.from)}"`, Number.isFinite(sv.to) && ` data-kit-to="${esc(sv.to)}"`].filter(Boolean).join('');
  return raw(`<details class="kc-segment kc not-content" data-kit-video${attrs}>`,
    `<summary><span class="kc-seg-icon" aria-hidden="true"></span><span class="kc-seg-text">${esc(text)}</span>${toggle('Show', 'Hide')}</summary>`,
    '<div class="kc-segment-body">', `<div class="kc-frame">${playerTag(v, sv)}</div>`,
    sv.note && `<p class="kc-video-note">${md(capFirst(sv.note), opts)}</p>`, '</div>', '</details>');
}

// ---------- step pages ----------

/** Step header (spec 5.4 item 1): breadcrumb, course position, title, lesson small print, chips, Mark done. */
export function stepHeader(step, model) {
  const day = dayOf(step, model);
  const pct = step.total ? Math.round((step.pos / step.total) * 1000) / 10 : 0;
  const lesson = step.lesson;
  const small = lesson ? `lesson ${lesson.dir.slice(0, 2)} · lessons/${lesson.dir}` : '';
  const smallHtml = small && step.page && lesson.route ? `<a href="${esc(lesson.route)}">${esc(small)}</a>` : esc(small);
  return raw('<div class="kc-head kc-step-head kc not-content">',
    '<div class="kc-head-row">',
    `<nav class="kc-crumbs" aria-label="Breadcrumb"><a href="/">Course</a><span aria-hidden="true">/</span><a href="${esc(day.route)}">Day ${day.n}</a><span aria-hidden="true">/</span><span aria-current="page">Step ${step.n} of ${step.of}</span></nav>`,
    step.total ? `<p class="kc-pos"><span>course ${step.pos} of ${step.total}</span><span class="kc-bar" role="progressbar" aria-label="Course position" aria-valuemin="0" aria-valuemax="${step.total}" aria-valuenow="${step.pos}"><span style="width:${pct}%"></span></span></p>` : '',
    '</div>',
    `<p class="kc-title" aria-hidden="true">${esc(step.title)}</p>`,
    small && `<p class="kc-small">${smallHtml}</p>`,
    '<div class="kc-head-actions">',
    '<p class="kc-chips">',
    chip('kc-chip-time', esc(fmtMin(step.minutes))),
    costChip(step.cost, step.paid),
    chip('kc-chip-where', esc(runsOnText(step))),
    step.optional ? chip('kc-chip-optional', `Optional: ${esc(String(step.optional).replace(/^needs/i, 'needs'))}`) : '',
    '</p>',
    '<p class="kc-head-buttons">', doneButton(step.id), skipButton(step), '</p>',
    '</div>',
    '</div>');
}

/** Before the README (spec 5.4 items 2 to 5): why, start first, watch, in plain words. */
export function stepBeforeReadme(step, model) {
  const opts = { from: step.route };
  const out = [];
  if (step.why || step.why_example) {
    out.push(raw('<div class="kc-why kc not-content">', '<p class="kc-label kc-accent">What you will do and why</p>',
      step.why && `<p class="kc-why-text">${md(capFirst(step.why), opts)}</p>`,
      step.why_example && `<p class="kc-why-example"><strong>Why it matters:</strong> ${md(step.why_example, opts)}</p>`,
      step.done && `<p class="kc-why-example"><strong>You are done when:</strong> ${md(step.done, opts)}</p>`, '</div>'));
  }
  if (step.start_first?.command || step.start_first?.note) {
    out.push(raw('<div class="kc-card kc-start kc not-content">', '<p class="kc-label kc-warm">Start this first</p>',
      step.start_first.note && `<p>${md(capFirst(step.start_first.note), opts)}</p>`, '</div>'));
    if (step.start_first.command) out.push(codeFence(step.start_first.command, 'bash', 'wrap'));
  }
  const full = allVideos(step);
  const segs = segVideos(step);
  if (full.length || segs.length) {
    out.push('## Watch');
    for (const sv of full) out.push(videoFull(sv, opts));
    for (const sv of segs) out.push(videoSegment(sv, step, model, opts));
  } else if (step.noVideo) {
    out.push(raw('<div class="kc-novideo kc not-content">', `<p>${md(typeof step.noVideo === 'string' ? step.noVideo : 'No video for this step.', opts)}</p>`, '</div>'));
  }
  const p = step.plain;
  if (p && (p.lead || p.picture || p.numbers?.length || p.words?.length)) {
    out.push('## In plain words');
    out.push(raw('<div class="kc-plain kc not-content">',
      p.lead && `<p class="kc-lead">${md(capFirst(p.lead), opts)}</p>`,
      (p.picture || p.numbers?.length || p.words?.length) && raw('<div class="kc-card kc-plain-card">',
        pictureBlock(p.picture, opts), numbersBlock(p, opts), wordsBlock(p.words, 'kc-words-table'), '</div>'),
      '</div>'));
  }
  return body(out);
}

// ----- the lesson README, reshaped for the course page -----

const cmdKey = (line) => String(line).trim().replace(/\s+#.*$/, '').replace(/\s*\\$/, '').replace(/\s+/g, ' ').trim();

// Logical commands in a Run code block (spec 3): continuation lines joined, loops up to `done`, no cd lines
// or comment lines. Returns [{ key, start, end }] as line indexes into `lines`.
function commandsIn(lines) {
  const out = [];
  for (let i = 0; i < lines.length; i++) {
    const t = lines[i].trim();
    if (!t || t.startsWith('#')) continue;
    let j = i;
    while (/\\\s*$/.test(lines[j]) && j + 1 < lines.length) j++;
    if (/^(for|while|until)\b/.test(t) && !/(^|[;&\s])done\b/.test(lines.slice(i, j + 1).join(' '))) {
      let depth = 1;
      while (j + 1 < lines.length && depth > 0) {
        j++;
        const u = lines[j].trim();
        if (/^(for|while|until)\b/.test(u) && !/(^|[;\s])done\b/.test(u)) depth++;
        if (/(^|[;\s])done\b/.test(u)) depth--;
      }
    }
    const key = cmdKey(t);
    if (!/^cd(\s|$)/.test(key)) out.push({ key, start: i, end: j });
    i = j;
  }
  return out;
}

// Per-line structure of a markdown file: fenced code and headings (outside fences).
function scan(lines) {
  const info = [];
  let open = null;
  let openAt = -1;
  lines.forEach((line, i) => {
    const f = line.match(/^ {0,3}(`{3,}|~{3,})(.*)$/);
    if (open) {
      const closes = !!f && f[1][0] === open[0] && f[1].length >= open.length && !f[2].trim();
      info.push({ code: true, close: closes, openAt });
      if (closes) open = null;
      return;
    }
    if (f) { open = f[1]; openAt = i; info.push({ code: true, open: true, openAt: i }); return; }
    const h = line.match(/^(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$/);
    info.push({ code: false, h: h ? h[1].length : 0, title: h ? h[2].replace(/\*+/g, '').trim() : '' });
  });
  return info;
}
// [start, end) of the section under the h2 at `at` (up to the next h1/h2).
function sectionEnd(info, at) {
  for (let i = at + 1; i < info.length; i++) if (!info[i].code && info[i].h && info[i].h <= 2) return i;
  return info.length;
}
function fencedBlocks(info, from, to) {
  const out = [];
  for (let i = from; i < to; i++) {
    if (info[i].open) {
      let j = i + 1;
      while (j < info.length && !info[j].close) j++;
      out.push({ open: i, close: Math.min(j, info.length - 1) });
      i = j;
    }
  }
  return out;
}
const mentions = (text, file) => new RegExp(`(^|[^\\w.-])${file.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}($|[^\\w-])`).test(text);

// The step's `replace` entries (find -> with), as the README text gets them. Run notes name the README's own
// commands (course.mjs checks them against it), so their command is shown through this too.
function applyReplace(text, step) {
  let s = String(text ?? '');
  for (const r of step.replace ?? []) if (r?.find) s = s.split(r.find).join(r.with ?? '');
  return s;
}

// notes: [{ cmd, note }] with cmd as the page shows it (replace applied)
function runNotesBlock(notes, opts) {
  return raw('<div class="kc-run-notes kc not-content">', '<p class="kc-label">What each command does</p>', '<ol>',
    notes.map((n) => `<li><p class="kc-run-cmd"><code>${esc(n.cmd)}</code></p><p>${md(n.note, opts)}</p></li>`), '</ol>', '</div>');
}

/**
 * The lesson README as shown on a course page (spec 5.4 item 6): `replace` applied; the H1, the header
 * quote (Lab book / Watch / Time / Cost), "**Next →**" lines and the "Check yourself" and "Explain what
 * you learned" sections removed; the plain run notes after the Run block (after the code block that holds each
 * command, else as one list after the last block); `see` right under "What you should see". For split
 * lessons (step.files), Run commands and "Read the code first" items that name only the other part's files
 * are left out. rewrite (optional) is the site's link rewriter, applied to the README text only.
 */
export function transformReadme(mdText, step, rewrite) {
  const text = applyReplace(String(mdText ?? '').replace(/^﻿/, '').replace(/\r\n?/g, '\n'), step);
  let lines = text.split('\n');
  let info = scan(lines);
  const drop = new Set();

  // H1, then the header quote right under it
  const h1 = info.findIndex((x) => !x.code && x.h === 1);
  if (h1 >= 0) {
    drop.add(h1);
    let i = h1 + 1;
    while (i < lines.length && !lines[i].trim()) i++;
    if (i < lines.length && lines[i].startsWith('>')) {
      let j = i;
      while (j < lines.length && lines[j].startsWith('>')) j++;
      if (lines.slice(i, j).every((l) => /^> ?\*\*[^*]+:\*\*/.test(l))) for (let k = i; k < j; k++) drop.add(k);
    }
  }
  info.forEach((x, i) => {
    if (x.code) return;
    if (/^\s*\*\*Next\b[^*]*\*\*/.test(lines[i])) drop.add(i);
    if (x.h === 2 && /^(check yourself|explain what you learned)\b/i.test(x.title)) {
      for (let k = i; k < sectionEnd(info, i); k++) drop.add(k);
    }
  });

  // split lessons: leave out the other part's commands and code notes
  const other = step.files?.length && step.lesson?.files
    ? step.lesson.files.filter((f) => !f.endsWith('.md') && !step.files.includes(f)).map((f) => f.split('/').pop()) : [];
  const own = (step.files ?? []).map((f) => f.split('/').pop());
  const foreign = (s) => other.some((f) => mentions(s, f)) && !own.some((f) => mentions(s, f));
  if (other.length) {
    info.forEach((x, i) => {
      if (x.code || x.h !== 2) return;
      const end = sectionEnd(info, i);
      if (/^run\b/i.test(x.title)) {
        for (const b of fencedBlocks(info, i + 1, end)) {
          const inner = lines.slice(b.open + 1, b.close);
          for (const c of commandsIn(inner)) {
            if (foreign(inner.slice(c.start, c.end + 1).join('\n'))) for (let k = c.start; k <= c.end; k++) drop.add(b.open + 1 + k);
          }
        }
      } else if (/^read the code first\b/i.test(x.title)) {
        for (let k = i + 1; k < end; k++) {
          if (!/^[-*+] /.test(lines[k])) continue;
          let e = k + 1;
          while (e < end && lines[e].trim() && !/^[-*+] /.test(lines[e])) e++;
          if (foreign(lines.slice(k, e).join('\n'))) for (let d = k; d < e; d++) drop.add(d);
          k = e - 1;
        }
      }
    });
  }

  // keep what is left; no runs of blank lines, none just inside a code fence
  const kept = [];
  lines.forEach((l, i) => { if (!drop.has(i)) kept.push(l); });
  lines = [];
  for (let i = 0; i < kept.length; i++) {
    const blank = !kept[i].trim();
    if (blank && (!lines.length || !lines.at(-1).trim())) continue;
    lines.push(kept[i]);
  }
  info = scan(lines);
  for (let i = lines.length - 1; i >= 0; i--) {
    if (!lines[i].trim() && ((info[i + 1]?.close) || (info[i - 1]?.open))) { lines.splice(i, 1); info.splice(i, 1); }
  }
  info = scan(lines);
  while (lines.length && !lines.at(-1).trim()) { lines.pop(); info.pop(); }

  // where the plain notes go: after line index -> html chunks
  const inserts = new Map();
  const add = (at, html) => inserts.set(at, [...(inserts.get(at) ?? []), html]);
  const opts = { from: step.route };
  info.forEach((x, i) => {
    if (x.code || x.h !== 2) return;
    const end = sectionEnd(info, i);
    if (/^run\b/i.test(x.title) && step.run?.length) {
      const blocks = fencedBlocks(info, i + 1, end).map((b) => ({ ...b, keys: commandsIn(lines.slice(b.open + 1, b.close)).map((c) => c.key) }));
      // each note's command as the code block shows it, so a replaced command finds its block and is shown new
      const left = step.run.map((r) => ({ ...r, cmd: applyReplace(r.cmd, step) }));
      for (const b of blocks) {
        const mine = [];
        for (const key of b.keys) {
          const n = left.findIndex((r) => cmdKey(r.cmd) === key);
          if (n >= 0) mine.push(...left.splice(n, 1));
        }
        if (mine.length) add(b.close, runNotesBlock(mine, opts));
      }
      if (left.length) add(blocks.length ? blocks.at(-1).close : end - 1, runNotesBlock(left, opts));
    }
    if (/^what you should see\b/i.test(x.title) && step.see) {
      add(i, raw('<div class="kc-see kc not-content">', '<p class="kc-label kc-accent">How to read it</p>', `<p>${md(capFirst(step.see), opts)}</p>`, '</div>'));
    }
  });

  // rewrite links in the README text only, then weave the notes in
  let readmeLines = lines;
  if (typeof rewrite === 'function') {
    const rewritten = String(rewrite(lines.join('\n'))).split('\n');
    if (rewritten.length === lines.length) readmeLines = rewritten;
    else {
      // the rewriter changed the line count: insert first, then rewrite everything
      return fromLab(rewrite(weave(lines, inserts)), step.route);
    }
  }
  return fromLab(weave(readmeLines, inserts), step.route, scan(readmeLines));
}
function weave(lines, inserts) {
  const out = [];
  lines.forEach((l, i) => {
    out.push(l);
    for (const html of inserts.get(i) ?? []) {
      if (out.length && out.at(-1).trim()) out.push('');
      out.push(html, '');
    }
  });
  return out.join('\n').replace(/\n{3,}/g, '\n\n').trim();
}
// Lab book links in the README prose get ?from=<route> (spec 5.8).
function fromLab(text, route) {
  const lines = String(text).split('\n');
  const info = scan(lines);
  return lines.map((l, i) => (info[i]?.code ? l : l.replace(/\]\((\/lab-book\/[^)\s]+)\)/g, (_, href) => `](${withFrom(href, route)})`))).join('\n');
}

/** After the README (spec 5.4 items 7 to 11): checks, say + fields, fw-check, done + Next, stuck. */
export function stepAfterReadme(step, model, ctx = {}) {
  const opts = { from: step.route };
  const day = dayOf(step, model);
  const out = [];
  if (step.checks?.length) {
    out.push('## Check yourself');
    out.push(raw('<div class="kc-checks kc not-content">',
      `<p class="kc-intro">${plural(step.checks.length, 'question')}. Say your answer out loud, then tap to check it.</p>`,
      step.checks.map((c, i) => checkDetails(c, i, opts, { id: `check-${i + 1}` })), '</div>'));
  }
  const say = step.say;
  if (say?.line || step.fields?.length) {
    out.push('## Explain what you learned');
    out.push(raw('<div class="kc-card kc-say kc not-content">',
      say?.ask && `<p class="kc-ask"><span class="kc-label">When they ask</span> <em>${md(say.ask, opts)}</em></p>`,
      say?.line && `<p class="kc-label kc-warm">You say</p><blockquote class="kc-you-say"><p>${md(say.line, opts)}</p></blockquote>`,
      say?.means?.length && raw('<div class="kc-means">', '<p class="kc-label">What this means</p>', '<ul>',
        say.means.map((m) => `<li><strong>“${md(m.phrase, opts)}”</strong>: ${md(m.meaning, opts)}</li>`), '</ul>', '</div>'),
      fieldsBlock(step.fields, day, opts),
      '</div>'));
  }
  if (step.paid) {
    out.push(raw('<div class="kc-fwcheck kc not-content">',
      '<p><strong>Run <code>make fw-check</code> now: it should list nothing.</strong> It lists anything on Fireworks that is still billing, so an empty list means nothing is costing you money.</p>',
      '</div>'));
  }
  out.push('## Done when');
  out.push(raw('<div class="kc-done kc not-content">',
    step.done && `<p class="kc-done-text">${md(capFirst(step.done), opts)}</p>`,
    '<div class="kc-done-row">', doneButton(step.id), nextButton(step, model), '</div>',
    step.optional ? `<p class="kc-skip-row">${skipButton(step)}</p>` : '',
    '</div>'));
  const labHref = (id) => (typeof ctx.labBookHref === 'function' ? ctx.labBookHref(step.route, id) : `${LAB_BOOK}?from=${step.route}#lab-${id}`);
  const cards = step.cards ?? [];
  if (step.stuck?.length || cards.length) {
    out.push('## Stuck?');
    const kind = { F: 'Fireworks lab', L: 'local lab', T: 'training lab' };
    out.push(raw('<div class="kc-stuck kc not-content">',
      step.stuck?.length && raw('<dl class="kc-card kc-stuck-list">',
        step.stuck.map((s) => `<div><dt>${md(capFirst(s.problem), opts)}</dt><dd>${md(capFirst(s.fix), opts)}</dd></div>`), '</dl>'),
      raw('<p class="kc-deeper-links">',
        cards.map((id) => `<a href="${esc(labHref(id))}">Go deeper: the lab book's ${kind[id[0]] ?? 'lab'} for this step</a>`),
        '<a href="/reference/troubleshooting/">All fixes</a>', '</p>'),
      '</div>'));
  }
  return body(out);
}

// "Your numbers" on a step page: label, hint, input.
function fieldsBlock(fields, day, opts) {
  if (!fields?.length) return '';
  return raw('<div class="kc-fields">',
    `<p class="kc-label-row"><span class="kc-label">Your numbers</span><span class="kc-source">Saved on this device and collected in the <a href="${esc(day.wrapRoute)}">Day ${day.n} wrap-up</a>.</span></p>`,
    fields.map((f, i) => fieldRow(f, `${i + 1}. `, f.hint && `Hint: ${f.hint}`, opts)), '</div>');
}
function fieldRow(f, prefix, hintText, opts, extra = '') {
  const id = `kf-${idOf(f.id)}`;
  const hint = hintText ? `<p class="kc-hint" id="${id}-hint">${md(hintText, opts)}</p>` : '';
  return raw('<div class="kc-field">',
    `<div class="kc-field-text"><label for="${id}">${esc(prefix)}${md(f.label, { ...opts, links: false })}</label>${hint}${extra}</div>`,
    `<div class="kc-input"><input id="${id}" type="text" data-kit-field="${esc(f.id)}" autocomplete="off" spellcheck="false"${hint ? ` aria-describedby="${id}-hint"` : ''}>${f.unit ? `<span class="kc-unit" aria-hidden="true">${esc(f.unit)}</span>` : ''}</div>`,
    '</div>');
}

/** The Fireworks spend-cap checklist for d1-s2 (the lab book's guardrail items), mirrored to flb-guard. */
export function spendCapChecklist(items) {
  if (!items?.length) return '';
  return body('## The spend-cap checklist', raw('<div class="kc-card kc-guard kc not-content">',
    '<p class="kc-intro">From the lab book. Tick each one as you do it; the lab book shows the same ticks.</p>',
    '<ul class="kc-ticks">',
    items.map((t, i) => `<li><label><input type="checkbox" data-kit-guard="${i}"><span>${md(t)}</span></label></li>`),
    '</ul>',
    '<p class="kc-trap"><strong>The trap:</strong> a LoRA fine-tune can only be served on a dedicated deployment, which bills by the hour whether or not you use it, so delete it in the same sitting.</p>',
    '</div>'));
}

/** "Code in this step" (spec 5.4 item 12): the file blocks, filtered by step.files for split lessons. */
export function stepCode(step, model, ctx) {
  const l = step.lesson;
  if (!l || typeof ctx?.fileBlock !== 'function') return '';
  const files = (step.files?.length ? l.files.filter((f) => step.files.includes(f) || step.files.includes(f.split('/').pop())) : l.files) ?? [];
  const docs = typeof ctx.docBlock === 'function' ? files.filter((f) => f.endsWith('.md')) : [];
  const code = files.filter((f) => !f.endsWith('.md'));
  if (!docs.length && !code.length) return '';
  const rctx = readmeCtx(step);
  return body('## Code in this step',
    docs.map((f) => ctx.docBlock(`${l.rel}/${f}`, f, rctx)),
    code.map((f, i) => ctx.fileBlock(`${l.rel}/${f}`, f, i === 0 && 'first', 0.5)));
}
function readmeCtx(step) {
  const l = step.lesson;
  const files = step.files?.length ? l.files.filter((f) => step.files.includes(f) || step.files.includes(f.split('/').pop())) : l.files;
  return { src: `${l.rel}/README.md`, srcDir: l.rel, files, route: step.route };
}

function fromTheLesson(step, ctx) {
  const l = step.lesson;
  if (!l?.md) return '';
  const rctx = typeof ctx?.readmeCtx === 'function' ? ctx.readmeCtx(step) : readmeCtx(step);
  const rw = typeof ctx?.rewrite === 'function' ? (m) => ctx.rewrite(m, rctx) : undefined;
  const text = transformReadme(l.md, step, rw);
  return body(raw('<div class="kc-from-lesson kc not-content">', `<p class="kc-label">From the lesson</p>`,
    `<p class="kc-small">${esc(`lessons/${l.dir}/README.md`)}</p>`, '</div>'), text);
}

/**
 * A whole step page body. Lesson steps: header, before, the README, the d1-s2 checklist
 * (ctx.guardItems), after, code. Generated steps (step.page) go through generatedStepPage.
 * ctx: { esc, fileBlock, rewrite, labBookHref, docBlock?, guardItems? }
 */
export function stepPage(step, model, ctx = {}) {
  if (step.page) return generatedStepPage(step, model, ctx);
  return body(stepHeader(step, model), stepBeforeReadme(step, model), fromTheLesson(step, ctx),
    ctx.guardItems && step.id === 'd1-s2' ? spendCapChecklist(ctx.guardItems) : '',
    stepAfterReadme(step, model, ctx), stepCode(step, model, ctx));
}

/**
 * Generated step pages (spec 2): get-the-code (d1-s1: the code zip), product-criticism (d10-s2), and
 * lesson16-part2 (d12-s1: lesson 16's second half, its checks and toy_alignment.py). step.body is markdown.
 */
export function generatedStepPage(step, model, ctx = {}) {
  const parts = [stepHeader(step, model), stepBeforeReadme(step, model)];
  const bodyMd = step.body ? String(step.body).trim() : '';
  if (step.page === 'get-the-code' && !bodyMd.includes(DOWNLOAD_ZIP)) {
    parts.push(raw('<div class="kc-card kc-zip kc not-content">', '<p class="kc-label kc-accent">The code</p>',
      '<p>Every lesson, the shared toolkit and the offline practice server, in one zip. Unzip it and open a terminal in the <code>03-labs</code> folder.</p>',
      `<p><a class="kc-btn kc-btn-primary" href="${DOWNLOAD_ZIP}" download="03-labs.zip">Download the code (03-labs.zip)</a></p>`, '</div>'));
  }
  if (bodyMd) parts.push(bodyMd);
  if (step.page === 'lesson16-part2') parts.push(fromTheLesson(step, ctx));
  parts.push(stepAfterReadme(step, model, ctx));
  if (step.page === 'lesson16-part2') parts.push(stepCode(step, model, ctx));
  return body(parts);
}

// ---------- home ----------

const HOW = [
  ['Overview · 2 min', 'What today is for', 'The goal, what you need first, and what you will have at the end.'],
  ['One to three steps', 'Watch, do, check, explain', 'The video plays inside the step. Then run the lab, check your result and explain what it means.'],
  ['Wrap-up · 10 min', 'Drill and record your numbers', 'Answer the day’s questions out loud and note your numbers, then on to the next day.'],
];

/** Home (spec 5.2): headline, the big Start/Continue button, how a day works, the 12 day tiles, what you need. */
export function homePage(model) {
  const days = model.days;
  const total = days.reduce((a, d) => a + (d.minutes || 0), 0);
  const long = days.filter((d) => d.long).map((d) => d.n);
  const first = days[0];
  const tiles = days.map((d) => raw(
    `<li><a class="kc-tile" href="${esc(d.route)}" data-kit-status="d${d.n}">`,
    `<span class="kc-tile-top"><span class="kc-tile-day">Day ${d.n}</span><span class="kc-state"></span></span>`,
    `<span class="kc-tile-title">${esc(d.title)}</span>`,
    d.tile && `<span class="kc-tile-sub">${md(d.tile, { links: false })}</span>`,
    `<span class="kc-tile-meta">${esc(aboutMin(d.minutes).replace(/^about /, ''))} · ${d.paid && !String(d.cost).includes('$') ? '<span class="kc-dollar" aria-hidden="true">$</span>' : ''}${esc(String(d.cost).replace(/^about /i, ''))}${d.part > 1 ? '<span class="kc-tile-part"> · Part 2</span>' : ''}</span>`,
    '</a></li>'));
  const downloads = days.map((d) => [d.n, dayDownloadGb(d)]).filter(([, gb]) => gb > 0);
  const optional = model.steps.filter((s) => s.optional);
  const need = model.home?.need ?? [
    'An Apple-silicon Mac (the examples use one with 36 GB).',
    downloads.length && `Disk for model downloads: ${downloads.map(([n, gb], i) => `${i && i === downloads.length - 1 ? 'and ' : ''}${i ? '' : 'about '}${gb} GB on Day ${n}`).join(downloads.length > 2 ? ', ' : ' ').replace(', and', ' and')}.`,
    'A Fireworks account with a payment method, for the steps marked $. Day 1 sets a spend cap first.',
    ...optional.map((s) => {
      const m = String(s.optional).match(/^needs (an?|the) (.+?)\.?$/i);
      return m ? `${cap(m[1])} ${m[2]}, only for the optional Day ${dayOf(s, model).n} · Step ${s.n}.` : '';
    }),
  ].filter(Boolean);
  return body(
    raw('<div class="kc-head kc-home kc not-content">',
      '<p class="kc-eyebrow">AI Engineering Field Kit</p>',
      '<p class="kc-home-title" aria-hidden="true">Learn to build, measure and explain AI systems with your own results.</p>',
      '<p class="kc-lede">Twelve guided days for new AI engineers and field engineers. Start with one model reply, then learn how to serve, test, improve and recommend a real system. Fireworks is one of the hands-on platforms used in the labs.</p>',
      '<div class="kc-cta">',
      `<a class="kc-big" href="${esc(first?.route ?? '/course/day-1/')}" data-kit-continue>Start Day 1</a>`,
      `<p class="kc-cta-note"><span data-kit-days-done>0 of ${days.length} days done</span><span class="kc-cta-more">. Your progress is saved on this device.</span></p>`,
      '</div>', '</div>'),
    '## How a day works',
    raw('<div class="kc-how kc not-content">', '<ol>',
      HOW.map(([k, t, s], i) => `<li><span class="kc-how-n" aria-hidden="true">${i + 1}</span><div><p class="kc-label kc-accent">${esc(k)}</p><p class="kc-how-t">${esc(t)}</p><p class="kc-how-s">${esc(s)}</p></div></li>`),
      '</ol>', '<p class="kc-how-note">Your laptop runs the code. Your phone is for the videos and the practice.</p>', '</div>'),
    `## Your ${days.length} days`,
    raw('<div class="kc-days kc not-content">',
      `<p class="kc-intro">${cap(aboutMin(total))} in all.${long.length ? ` ${long.length > 1 ? `Days ${long.slice(0, -1).join(', ')} and ${long.at(-1)} are long` : `Day ${long[0]} is long`}.` : ''}</p>`,
      '<ol class="kc-tiles">', tiles, '</ol>', '</div>'),
    '## What you need',
    raw('<div class="kc-need kc not-content">', '<ul>', need.map((n) => `<li>${md(n)}</li>`), '</ul>',
      '<div class="kc-side">',
      '<nav class="kc-card kc-ref" aria-label="Reference">', '<p class="kc-label">Reference</p>',
      '<p class="kc-ref-t">For looking things up. The course links to what you need.</p>',
      '<p class="kc-ref-links"><a href="/videos/">Videos</a><a href="/lessons/">Lessons and code</a>',
      `<a href="${LAB_BOOK}?from=/">Lab book</a><a href="/lab-book/inference-field-guide.html?from=/">Field guide</a>`,
      '<a href="/reference/glossary/">Glossary</a><a href="/reference/troubleshooting/">Troubleshooting</a></p>', '</nav>', '</div>', '</div>'),
    raw('<details class="kc-sync kc not-content">',
      '<summary>Move your progress to another device</summary>',
      '<div class="kc-sync-body">',
      '<p>Progress lives in this browser only. Copy the code here, then paste it on the other device.</p>',
      '<label for="kc-export-code">Your progress code</label>',
      '<textarea id="kc-export-code" data-kit-export readonly rows="2" spellcheck="false"></textarea>',
      '<p><button type="button" class="kc-btn" data-kit-export>Copy my progress code</button></p>',
      '<label for="kc-import-code">Paste a progress code</label>',
      '<textarea id="kc-import-code" data-kit-import rows="2" spellcheck="false" autocomplete="off"></textarea>',
      '<p><button type="button" class="kc-btn" data-kit-import>Replace my progress with this code</button></p>',
      '</div>', '</details>'));
}

// ---------- day overview ----------

/** Day overview (spec 5.3). */
export function dayPage(day, model) {
  const opts = { from: day.route };
  const ov = day.overview ?? {};
  const gb = dayDownloadGb(day);
  const downloadStep = gb && day.steps.find((s) => downloadGb(s) === gb);
  const where = dayPlaces(day);
  const prev = model.days.find((d) => d.n === day.n - 1);
  const checks = day.steps.flatMap((s) => s.checks ?? []);
  const says = day.steps.filter((s) => s.say?.line).length;
  const wbs = day.wrapup?.whiteboards?.length ?? 0;
  const out = [];
  out.push(raw('<div class="kc-head kc-day-head kc not-content">',
    '<div class="kc-head-row">', `<p class="kc-eyebrow">${esc(dayLabel(day, model))}</p>`,
    `<p class="kc-pos"><span data-kit-days-done>0 of ${model.days.length} days done</span></p>`, '</div>',
    `<p class="kc-title" aria-hidden="true">${esc(day.title)}</p>`,
    '<p class="kc-chips">',
    chip('kc-chip-time', esc(cap(aboutMin(day.minutes)))),
    downloadStep ? `<a class="kc-chip kc-chip-download" href="${esc(downloadStep.route)}">${gb} GB model download · See Step ${downloadStep.n}</a>` : '',
    costChip(day.cost, day.paid),
    chip('kc-chip-where', esc(where)),
    '</p>',
    day.long && `<p class="kc-long"><strong>Long day.</strong> ${md(capFirst(day.long), opts)}</p>`,
    '</div>'));
  if (ov.today || ov.example) {
    out.push(raw(`<div class="kc-today kc not-content${ov.example ? '' : ' kc-today-solo'}">`,
      ov.today && `<p class="kc-today-text"><strong>Today:</strong> ${md(ov.today, opts)}</p>`,
      ov.example && `<div class="kc-card kc-example"><p class="kc-label kc-accent">Example</p><p>${md(capFirst(ov.example), opts)}</p></div>`,
      '</div>'));
  }
  // By the end (+ expected, the numbers you write down) and Before you start, side by side on wide screens
  const byEnd = raw('<section class="kc-card kc-byend" aria-label="By the end you’ll have">',
    '<p class="kc-label kc-accent">By the end you’ll have</p>',
    ov.deliverable && `<p class="kc-deliverable">${md(capFirst(ov.deliverable), opts)}</p>`,
    ov.expected && `<p class="kc-expected"><strong>Expected:</strong> ${md(ov.expected, opts)}</p>`,
    day.fields?.length && raw('<div class="kc-writedown">',
      `<p class="kc-sub">The ${plural(day.fields.length, 'number')} you write down</p>`, '<ol>',
      day.fields.map((f, i) => `<li><span class="kc-wd-n" aria-hidden="true">${i + 1}</span><div><p class="kc-wd-label">${md(f.label, opts)}</p>${f.meaning ? `<p class="kc-wd-meaning">${md(capFirst(f.meaning), opts)}</p>` : ''}${f.example ? `<p class="kc-wd-example"><strong>Example:</strong> ${md(f.example, opts)}</p>` : ''}</div></li>`),
      '</ol>', '</div>'),
    ov.feeds && `<p class="kc-feeds"><strong>How you will use this:</strong> ${md(ov.feeds, opts)}</p>`,
    '</section>');
  const before = ov.before?.length ? ov.before : [];
  // Before-you-start commands are fenced code (copy button), so the section is split around them.
  const beforeParts = [];
  if (before.length) {
    beforeParts.push(raw('<section class="kc-card kc-before" aria-label="Before you start">', '<p class="kc-label kc-accent">Before you start</p>', '<ol>'));
    // Say where a command runs once: many item texts already end "from the 03-labs folder:", and a
    // command that starts with cd says it itself.
    const saysWhere = (b) => /\b03-labs\b/i.test(b.body ?? '') || /^\s*cd\s/.test(b.command ?? '');
    before.forEach((b, i) => {
      beforeParts.push(raw(`<li><span class="kc-wd-n" aria-hidden="true">${i + 1}</span><div class="kc-before-item">`,
        `<p class="kc-before-t">${md(b.title, opts)}</p>`, b.body && `<p>${md(capFirst(b.body), opts)}</p>`,
        b.command && !saysWhere(b) ? '<p class="kc-before-cmd">From the <code>03-labs</code> folder:</p>' : ''));
      if (b.command) beforeParts.push(codeFence(b.command, 'bash', 'frame="none" wrap'));
      beforeParts.push(raw(b.after ? `<p>${md(capFirst(b.after), opts)}</p>` : '', '</div></li>'));
    });
    beforeParts.push(raw('</ol>', '</section>'));
  }
  out.push(raw(`<div class="kc-day-grid kc not-content${before.length ? '' : ' kc-day-grid-solo'}">`), byEnd, ...beforeParts, raw('</div>'));

  if (day.warmup?.length && prev) {
    out.push(`## Warm-up from Day ${prev.n}`);
    out.push(raw('<div class="kc-warmup kc-checks kc not-content" data-pagefind-ignore>',
      `<p class="kc-intro">About 2 minutes. Say your answer out loud, then tap to check it. From <a href="${esc(prev.route)}">Day ${prev.n} · ${esc(prev.title)}</a>.</p>`,
      day.warmup.map((c, i) => checkDetails(c, i, opts)), '</div>'));
  }
  out.push('## Today’s steps');
  const rows = day.steps.map((s) => {
    const v = allVideos(s)[0]?.video ?? stepVideos(s)[0]?.video;
    const vids = allVideos(s).map((x) => `${x.video.title} ${x.video.min}`);
    return raw(`<li><a class="kc-step-row" href="${esc(s.route)}" data-kit-status="${esc(s.id)}">`,
      `<span class="kc-step-n" aria-hidden="true">${s.n}</span>`,
      v ? `<span class="kc-step-thumb"><img src="${esc(v.poster)}" alt="" loading="lazy" decoding="async" width="960" height="540"></span>` : '<span class="kc-step-thumb kc-thumb-none" aria-hidden="true"></span>',
      '<span class="kc-step-body">',
      `<span class="kc-step-meta">Step ${s.n} · ${esc(fmtMin(s.minutes))} · ${s.paid && !String(s.cost).includes('$') ? '<span class="kc-dollar" aria-hidden="true">$</span>' : ''}${esc(costText(s.cost))}${s.optional ? ' · <span class="kc-opt">Optional</span>' : ''}</span>`,
      `<span class="kc-step-title">${esc(s.title)}</span>`,
      s.why && `<span class="kc-step-why">${md(capFirst(s.why), { links: false })}</span>`,
      vids.length ? `<span class="kc-step-videos">${vids.length > 1 ? 'Videos' : 'Video'}: ${esc(vids.join(' · '))}</span>` : '',
      '</span>', '<span class="kc-state"></span>', '</a></li>');
  });
  rows.push(raw(`<li><a class="kc-step-row kc-wrap-row" href="${esc(day.wrapRoute)}" data-kit-status="d${day.n}-wrap">`,
    '<span class="kc-step-n kc-step-flag" aria-hidden="true"></span>',
    `<span class="kc-step-thumb kc-thumb-cards" aria-hidden="true"><span>${plural(checks.length, 'card')}</span></span>`,
    '<span class="kc-step-body">', '<span class="kc-step-meta">Wrap-up · 10 min · works on your phone</span>',
    '<span class="kc-step-title">Wrap-up and drill</span>',
    `<span class="kc-step-why">Put your numbers in one table, answer ${plural(checks.length, 'question')} out loud${says ? `, explain ${plural(says, 'result')}` : ''}${wbs ? ` and work ${plural(wbs, 'example')}` : ''}.</span>`,
    '</span>', '<span class="kc-state"></span>', '</a></li>'));
  const opt = day.steps.filter((s) => s.optional);
  out.push(raw('<div class="kc-steplist kc not-content">',
    `<p class="kc-intro">${plural(day.steps.length - opt.length, 'step')}, then the wrap-up.${opt.length ? ` Optional steps are not in the day’s time.` : ''}</p>`,
    '<ol class="kc-steps">', rows, '</ol>', '</div>'));
  const next = dayNext(day);
  if (next) {
    out.push(raw('<div class="kc-cta kc not-content">',
      `<a class="kc-big" href="${esc(next.route)}" data-kit-continue="${day.n}">${esc(next.label)}</a>`,
      '<p class="kc-cta-note">Your progress is saved on this device.</p>', '</div>'));
  }
  return body(out);
}

// ---------- wrap-up ----------

/** Wrap-up (spec 5.5): done when, your numbers, drill, say it out loud, whiteboard, feeds, Mark day done + Next. */
export function wrapupPage(day, model) {
  const opts = { from: day.wrapRoute };
  const w = day.wrapup ?? {};
  const cards = day.steps.flatMap((s) => (s.checks ?? []).map((c) => ({ s, c })));
  const sayers = day.steps.filter((s) => s.say?.line);
  const out = [];
  out.push(raw('<div class="kc-head kc-wrap-head kc not-content">',
    `<nav class="kc-crumbs" aria-label="Breadcrumb"><a href="/">Course</a><span aria-hidden="true">/</span><a href="${esc(day.route)}">Day ${day.n} · ${esc(day.title)}</a><span aria-hidden="true">/</span><span aria-current="page">Wrap-up and drill</span></nav>`,
    `<p class="kc-title" aria-hidden="true">Day ${day.n} wrap-up</p>`,
    '<ol class="kc-stepper" aria-label="Today">',
    `<li><a href="${esc(day.route)}">Overview</a></li>`,
    day.steps.map((s) => `<li data-kit-status="${esc(s.id)}"><a href="${esc(s.route)}">Step ${s.n}</a></li>`),
    '<li aria-current="step"><span>Wrap-up</span></li>', '</ol>',
    '<p class="kc-lede">About 10 minutes, free, and it works on your phone. Lock in today before you move on.</p>',
    '</div>'));
  if (w.done) {
    out.push(raw('<div class="kc-card kc-wrap-done kc not-content">', '<p class="kc-label kc-accent">Done when</p>',
      `<p class="kc-done-text">${md(capFirst(w.done), opts)}</p>`,
      `<label class="kc-check-box"><input type="checkbox" data-kit-check="d${day.n}-wrap"><span>I have it</span></label>`, '</div>'));
  }
  if (day.fields?.length) {
    out.push('## Your numbers');
    out.push(raw('<div class="kc-wrap-numbers kc not-content">',
      '<div class="kc-numbers-top">', '<p class="kc-intro">Fields you filled in on the step pages are already here. Nothing leaves this browser.</p>',
      `<button type="button" class="kc-btn kc-copy" data-kit-copy-fields="${day.n}">Copy all</button>`, '</div>',
      day.steps.filter((s) => s.fields?.length).map((s) => raw('<section class="kc-card kc-numbers-step" aria-label="' + esc(`Step ${s.n} · ${s.title}`) + '">',
        `<p class="kc-label kc-accent">Step ${s.n} · ${esc(s.title)}</p>`,
        s.fields.map((f) => fieldRow(f, '', f.meaning || f.hint, opts, f.example ? `<p class="kc-hint"><strong>Example:</strong> ${md(f.example, opts)}</p>` : '')),
        '</section>')),
      '</div>'));
  }
  if (cards.length) {
    out.push(`## Drill: ${plural(cards.length, 'card')}`);
    out.push(raw('<div class="kc-drill kc not-content" data-pagefind-ignore>',
      `<p class="kc-intro">Every question from today’s steps. Say your answer out loud, then show the answer and rate yourself. <span class="kc-drill-count" data-kit-drill-count>${plural(cards.length, 'card')}</span></p>`,
      cards.map(({ s, c }) => raw(`<article class="kc-card kc-drill-card" data-kit-card="${esc(`${s.id}-c${c.n}`)}">`,
        `<p class="kc-drill-from"><span class="kc-label">Question</span><a href="${esc(s.route)}#check-${(s.checks ?? []).indexOf(c) + 1}">Step ${s.n} · ${esc(s.title)}</a></p>`,
        `<p class="kc-drill-q">${md(c.q ?? c.kitQ, opts)}</p>`,
        '<details class="kc-reveal">', `<summary>${toggle('Show answer', 'Hide answer')}</summary>`,
        '<div class="kc-reveal-body">', checkLayers(c, opts),
        '<div class="kc-rate"><p>How did you do?</p><button type="button" class="kc-btn kc-again" data-kit-rate="again">Again</button><button type="button" class="kc-btn kc-got" data-kit-rate="got">Got it</button></div>',
        '</div>', '</details>', '</article>')),
      '</div>'));
  }
  if (sayers.length) {
    out.push('## Say it out loud');
    out.push(raw('<div class="kc-say-grid kc not-content">',
      '<p class="kc-intro">Under 20 seconds each. Record yourself once and listen back.</p>',
      sayers.map((s) => raw('<article class="kc-card kc-say kc-say-card">',
        `<div class="kc-say-top"><p class="kc-label kc-accent">Step ${s.n} · ${esc(s.title)}</p><label class="kc-check-box kc-said"><input type="checkbox" data-kit-said="${esc(s.id)}"><span>Said it</span></label></div>`,
        s.say.ask && `<p class="kc-ask"><span class="kc-label">When they ask</span> <em>${md(s.say.ask, opts)}</em></p>`,
        `<p class="kc-label kc-warm">You say</p><blockquote class="kc-you-say"><p>${md(s.say.line, opts)}</p></blockquote>`,
        s.say.means?.length && raw('<details class="kc-means-more">', '<summary>What this means</summary>', '<ul>',
          s.say.means.map((m) => `<li><strong>“${md(m.phrase, opts)}”</strong>: ${md(m.meaning, opts)}</li>`), '</ul>', '</details>'),
        '</article>')),
      '</div>'));
  }
  if (w.whiteboards?.length) {
    out.push('## Whiteboard');
    const n = w.whiteboards.length;
    out.push(raw('<div class="kc-wbs kc not-content">',
      `<p class="kc-intro">${n > 1 ? `${n} worked examples` : 'A worked example'} from today’s videos. Work ${n > 1 ? 'each' : 'it'} on paper, then reveal.</p>`,
      w.whiteboards.map((b, i) => whiteboard(b, i, n, model, opts)), '</div>'));
  }
  if (day.overview?.feeds) {
    out.push(raw('<div class="kc-feeds-bar kc not-content">', '<p class="kc-label kc-warm">How you will use this</p>', `<p>${md(day.overview.feeds, opts)}</p>`, '</div>'));
  }
  const nx = wrapupNext(day, model);
  out.push(raw('<div class="kc-done-row kc-wrap-end kc not-content">',
    `<button type="button" class="kc-btn kc-mark" data-kit-day-done="${day.n}" aria-pressed="false">Mark Day ${day.n} done</button>`,
    nextButton(nx.target, model, { sub: nx.sub }), '</div>'));
  return body(out);
}

function whiteboard(b, i, n, model, opts) {
  const v = b.video && (model.steps.flatMap(stepVideos).find((x) => x.stem === b.video)?.video);
  const note = b.note ? String(b.note) : '';
  const nm = note.match(/^([A-Z][^:.]{2,40}):\s+([\s\S]+)$/);
  return raw('<article class="kc-card kc-wb">',
    '<div class="kc-wb-top">',
    v ? `<p class="kc-wb-video"><span>From the video:</span> <strong>${esc(v.title)}</strong> <span class="kc-dim">${esc(v.min)}</span></p>` : '<p></p>',
    `<p class="kc-label">Whiteboard ${i + 1} of ${n}</p>`, '</div>',
    `<p class="kc-wb-q">${md(b.q, opts)}</p>`,
    b.given && `<div class="kc-given"><p class="kc-label">Given, in plain words</p><p>${md(capFirst(b.given), opts)}</p></div>`,
    '<details class="kc-reveal kc-wb-reveal">', `<summary>${toggle('Reveal the answer', 'Hide the answer')}</summary>`,
    '<div class="kc-reveal-body">',
    '<div class="kc-wb-grid">', '<div>',
    plainBox(b.plain, 'Answer · in plain words', opts),
    pictureBlock(b.picture, opts),
    note && `<div class="kc-caution"><p class="kc-label kc-warm">${esc(nm ? nm[1] : 'Careful')}</p><p>${md(capFirst(nm ? nm[2] : note), opts)}</p></div>`,
    '</div>',
    b.steps?.length && raw('<div class="kc-wb-steps">', '<p class="kc-label">Worked answer, step by step</p>', '<ol>',
      b.steps.map((s) => `<li>${md(s, opts)}</li>`), '</ol>', '</div>'),
    '</div>',
    deeperBlock({ kitQ: b.kit_q, kitA: b.kit_a, more: b.more }, opts),
    wordsBlock(b.words),
    '</div>', '</details>', '</article>');
}

// ---------- reference pages ----------

/** Videos library (spec 5.7): every video in course order, grouped by the day it is first played. */
export function videoLibraryPage(model, videos) {
  const firstDay = new Map();
  for (const v of videos) {
    const st = firstFullUse(v.stem, model);
    firstDay.set(v.stem, st ? dayOf(st, model) : null);
  }
  const groups = model.days.map((d) => ({ d, vs: videos.filter((v) => firstDay.get(v.stem)?.n === d.n) }));
  const order = new Map(model.steps.flatMap((s, i) => allVideos(s).map((x, j) => [x.stem, i * 10 + j])));
  for (const g of groups) g.vs.sort((a, b) => (order.get(a.stem) ?? 0) - (order.get(b.stem) ?? 0));
  const rest = videos.filter((v) => !firstDay.get(v.stem));
  const card = (v) => {
    const uses = usesOf(v.stem, model);
    return raw('<article class="kc-vcard">',
      `<a class="kc-vcard-thumb" href="${esc(v.route)}" tabindex="-1" aria-hidden="true"><img src="${esc(v.poster)}" alt="" loading="lazy" decoding="async" width="960" height="540"><span class="kc-dur">${esc(v.min)}</span></a>`,
      '<div class="kc-vcard-body">',
      `<p class="kc-vcard-title"><a href="${esc(v.route)}">${esc(v.title)}</a></p>`,
      v.what && `<p class="kc-vcard-what">${md(v.what, { links: false })}</p>`,
      uses.length ? `<p class="kc-vcard-used"><span>Used in:</span> ${uses.map((u) => `<a href="${esc(u.step.route)}">Day ${dayOf(u.step, model).n} · Step ${u.step.n}${u.mode === 'all' ? '' : ` (${u.mode})`}</a>`).join(' ')}</p>` : '',
      '</div>', '</article>');
  };
  return body(
    raw('<p class="kc-intro kc not-content">Every video, in the order the course plays them. Each one plays inside its step; here you can find one again.</p>'),
    groups.filter((g) => g.vs.length).map((g) => body(`## Day ${g.d.n} · ${mdPlain(g.d.title)}`,
      raw('<div class="kc-vlib kc not-content">', g.vs.map(card), '</div>'))),
    rest.length ? body('## Not in the course', raw('<div class="kc-vlib kc not-content">', rest.map(card), '</div>')) : '');
}

/** A video page body (spec 5.7): small print, player with chapters, what it explains, key points, used in. */
export function videoPageExtras(video, model) {
  const uses = usesOf(video.stem, model);
  const full = uses.map((u) => stepVideos(u.step).find((x) => x.stem === video.stem && x.mode === 'all')).find(Boolean);
  const chapters = full?.chapters ?? uses.map((u) => stepVideos(u.step).find((x) => x.stem === video.stem)?.chapters).find((c) => c?.length);
  return body(
    raw('<div class="kc-vpage kc not-content">',
      `<p class="kc-small">file ${esc(video.num)} · ${esc(video.min)} · subtitles burned in</p>`,
      '<div class="kc-video" data-kit-video>',
      `<div class="kc-video-grid${chapters?.length ? '' : ' kc-no-chapters'}">`, `<div class="kc-frame">${playerTag(video)}</div>`, chaptersBlock(chapters), '</div>',
      full?.in_this_video && `<p class="kc-in-video"><span class="kc-label">In this video</span> ${md(full.in_this_video)}</p>`,
      video.what && `<p class="kc-what"><strong>What it explains:</strong> ${md(video.what)}</p>`,
      keyPointsBlock(full?.key_points),
      '</div>',
      uses.length && raw('<div class="kc-card kc-used">', '<p class="kc-label">Used in the course</p>', '<ul>',
        uses.map((u) => {
          const d = dayOf(u.step, model);
          const range = Number.isFinite(u.from) ? `, ${fmtTime(u.from)} to ${Number.isFinite(u.to) ? fmtTime(u.to) : video.min}` : '';
          return `<li><a href="${esc(u.step.route)}">Day ${d.n} · Step ${u.step.n} · ${esc(u.step.title)}</a>${u.mode === 'all' ? '' : ` <span class="kc-dim">(${u.mode}${range})</span>`}</li>`;
        }), '</ul>', '</div>'),
      `<p class="kc-note">The title card in the video says “Video ${esc(Number(video.num))} of 18”: that is the file order. The course plays the videos in the order of its days.</p>`,
      `<p>${downloadLink(video)}</p>`,
      '</div>'));
}

/** Glossary (spec 5.7): every merged term, alphabetical, each with its example. */
export function glossaryPage(model) {
  const terms = [...(model.glossary ?? [])].sort((a, b) => String(a.term).localeCompare(String(b.term), 'en', { sensitivity: 'base', numeric: true }));
  const groups = new Map();
  for (const t of terms) {
    const c = String(t.term).trim()[0]?.toUpperCase() ?? '#';
    const k = /[A-Z]/.test(c) ? c : '#';
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(t);
  }
  const keys = [...groups.keys()].sort((a, b) => (a === '#' ? -1 : b === '#' ? 1 : a.localeCompare(b)));
  const gid = (k) => (k === '#' ? 'gl-0-9' : `gl-${k.toLowerCase()}`);
  return body(raw('<div class="kc-gloss kc not-content">',
    `<p class="kc-intro">${plural(terms.length, 'term')} from the course, each with an example.</p>`,
    '<nav class="kc-letters" aria-label="Jump to a letter">', keys.map((k) => `<a href="#${gid(k)}">${k === '#' ? '0-9' : k}</a>`), '</nav>',
    keys.map((k) => raw(`<section class="kc-gl-group" id="${gid(k)}" aria-label="${k === '#' ? '0 to 9' : k}">`, `<p class="kc-gl-letter" aria-hidden="true">${k === '#' ? '0-9' : k}</p>`, '<dl>',
      groups.get(k).map((t) => `<div class="kc-term" id="term-${idOf(t.term)}"><dt>${md(t.term)}</dt><dd><p>${md(capFirst(t.def))}</p>${t.example ? `<p class="kc-gl-example"><strong>Example:</strong> ${md(t.example)}</p>` : ''}</dd></div>`),
      '</dl>', '</section>')),
    '</div>'));
}
