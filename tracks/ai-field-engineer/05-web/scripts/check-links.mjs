// Post-build check: every same-site link, asset and #anchor in dist resolves, no link leaves the site through
// a backslash or a leading //, and no page repeats an id.
// Media URLs are checked against the kit's 01-videos folder (nginx serves the videos and their posters).
// The course rules of docs/course-spec.md section 7 are checked on the built pages too:
// - every spine page (public/kit-spine.js) has Starlight prev/next links to its spine neighbours, and every
//   other rel="next" link on it (the big Next button) goes to the same place; the spine ends with the last
//   wrap-up, and its next links lead home (at least one next link, pager or big button, all of them to /)
// - no learner-facing text on a course page (home, /course/, lesson pages) says
//   "video <n>" or names Runpod outside <pre> and <code>, and no generated page has an emoji
// - the code download /downloads/03-labs.zip exists and is a zip
// Broken links, the spine and the zip always fail the build. The text rules fail it with STRICT=1 and are
// printed as warnings otherwise (a staging build while the course text is still being written).
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { EMOJI, VIDEO_N } from './course.mjs';

// Runpod stays in the field guide (Reference) only: never on the generated course pages.
const RUNPOD = /runpod|flashboot|secure cloud|community cloud/i;

const WEB = path.resolve(import.meta.dirname, '..');
const DIST = path.join(WEB, 'dist');
const KIT = path.resolve(process.env.KIT_DIR ?? path.join(WEB, '..'));
const STRICT = /^(1|true|yes)$/i.test(process.env.STRICT ?? '');

const walk = (dir) => fs.readdirSync(dir, { withFileTypes: true })
  .flatMap((e) => (e.isDirectory() ? walk(path.join(dir, e.name)) : [path.join(dir, e.name)]));
const urlOf = (file) => '/' + path.relative(DIST, file).split(path.sep).join('/').replace(/(^|\/)index\.html$/, '$1');
const decode = (s) => decodeURIComponent(s.replace(/&amp;/g, '&'));
// An attribute value as a browser reads the URL in it: character references decoded, tabs and line breaks
// dropped, the ends trimmed (percent escapes stay: %5C is not a slash).
const asBrowser = (v) => v
  .replace(/&(?:#x([0-9a-f]+)|#(\d+)|(amp|bsol|sol));?/gi, (all, hex, dec, name) => {
    if (name) return { amp: '&', bsol: '\\', sol: '/' }[name.toLowerCase()];
    const c = hex ? parseInt(hex, 16) : Number(dec);
    return c > 0 && c <= 0x10ffff ? String.fromCodePoint(c) : '�';
  })
  .replace(/[\t\n\r]/g, '').replace(/^[\0- ]+|[\0- ]+$/g, '');
const idsIn = (html) => [...html.matchAll(/\sid="([^"]+)"/g)].map((m) => decode(m[1]));

// Lab book pages are published as-is: their ids count as anchor targets, their own links are not checked.
const all = walk(DIST).filter((f) => f.endsWith('.html'));
const isLabBook = (f) => f.includes(`${path.sep}lab-book${path.sep}`);
const ids = new Map(all.map((f) => [urlOf(f), new Set(idsIn(fs.readFileSync(f, 'utf8')))]));

function target(p) {
  const media = p.match(/^\/media\/(videos\/(.+)\.mp4|posters\/(.+)\.jpg)$/);
  if (media) return fs.existsSync(path.join(KIT, '01-videos', `${media[2] ?? media[3]}.mp4`)) ? 'media' : null;
  const file = path.join(DIST, p);
  if (p.endsWith('/')) return fs.existsSync(path.join(file, 'index.html')) ? p : null;
  if (fs.existsSync(file) && fs.statSync(file).isFile()) return p;
  if (fs.existsSync(path.join(file, 'index.html'))) return `${p}/`;
  if (fs.existsSync(`${file}.html`)) return `${p}.html`; // nginx: try_files ... $uri.html
  return null;
}

const errors = [];
const textProblems = [];
let checked = 0;
for (const f of all.filter((f) => !isLabBook(f))) {
  const here = urlOf(f);
  const html = fs.readFileSync(f, 'utf8');
  const dupes = idsIn(html).filter((id, i, a) => a.indexOf(id) !== i);
  if (dupes.length) errors.push(`${here}: duplicate id ${[...new Set(dupes)].join(', ')}`);
  for (const m of html.matchAll(/\s(?:href|src|poster)="([^"]+)"/g)) {
    const raw = decode(m[1]);
    // A browser reads a backslash as a slash, so "/\host" and "//host" both leave the site: never a same-site
    // link, and not a deliberate external one either.
    const seen = asBrowser(m[1]);
    if (seen.includes('\\') || seen.startsWith('//')) { errors.push(`${here}: link ${raw} leaves the site (${seen.includes('\\') ? 'a backslash reads as /' : 'it starts with //'})`); continue; }
    if (/^[a-z]+:/i.test(raw)) continue;
    const url = new URL(raw, `http://site${here}`);
    const hash = url.hash.slice(1);
    checked++;
    const t = url.pathname === here && !raw.split('#')[0] ? here : target(url.pathname);
    if (!t) { errors.push(`${here}: broken link ${raw}`); continue; }
    if (hash && t !== 'media' && ids.has(t) && !ids.get(t).has(hash)) {
      // Lab cards are created by the lab book's script; their ids only exist at runtime.
      if (!(isLabBook(path.join(DIST, t)) && /^lab-[FLT]\d$/.test(hash))) errors.push(`${here}: missing anchor ${raw}`);
    }
  }
}

// ---------- the course rules (spec 7) ----------
const pageFile = (route) => path.join(DIST, route, 'index.html');
const norm = (href) => {
  const u = new URL(decode(href), 'http://site/');
  let p = u.pathname;
  if (!p.endsWith('/') && !/\.[a-z0-9]+$/i.test(p)) p += '/';
  return p;
};
const ENTITY = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };
// The text a reader sees: no scripts, styles, templates, code or tags; entities decoded. Tags are matched
// with their quoted attributes, since an attribute (a code block's copy button holds the code) may hold ">".
const TAG = /<\/?[a-zA-Z][^\s/>]*(?:\s+(?:[^\s"'>/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'>]+))?|\/))*\s*>/g;
// Block boundaries become " | ", so words from two blocks (a label, then a list) never read as one phrase.
// Spans count too: the templates use them for labels ("In this video") set next to their text.
const BLOCK = /^<\/?(p|div|span|li|ul|ol|dl|dt|dd|h[1-6]|br|hr|tr|td|th|table|section|article|aside|nav|header|footer|main|summary|details|figure|figcaption|blockquote|label|button)\b/i;
const visibleText = (html) => html
  .replace(/<!--[\s\S]*?-->/g, ' ')
  .replace(/<(script|style|template|pre|code|svg)\b(?:[^>"']|"[^"]*"|'[^']*')*>[\s\S]*?<\/\1>/gi, ' ')
  .replace(TAG, (t) => (BLOCK.test(t) ? ' | ' : ' '))
  .replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => (e[0] === '#' ? String.fromCodePoint(e[1] === 'x' || e[1] === 'X' ? parseInt(e.slice(2), 16) : Number(e.slice(1))) : ENTITY[e.toLowerCase()] ?? m))
  .replace(/\s+/g, ' ');
const around = (text, at, len) => text.slice(Math.max(0, at - 40), at + len + 40).trim();

// The spine, as kit.js reads it.
let spine = [];
try {
  const ctx = { window: {} };
  vm.runInNewContext(fs.readFileSync(path.join(DIST, 'kit-spine.js'), 'utf8'), ctx, { timeout: 1000 });
  spine = Array.isArray(ctx.window.KIT_SPINE) ? ctx.window.KIT_SPINE : [];
  if (!spine.length) errors.push('kit-spine.js: window.KIT_SPINE is empty');
} catch (e) {
  errors.push(`kit-spine.js: missing or unreadable (${e.message})`);
}
const kinds = spine.reduce((a, e) => ({ ...a, [e.k]: (a[e.k] ?? 0) + 1 }), {});
if (spine.length) {
  const lastWrap = spine.map((e) => e.k).lastIndexOf('wrapup');
  if (lastWrap !== spine.length - 1) errors.push('spine: the course must end at the last wrap-up');
}
spine.forEach((e, i) => {
  const file = pageFile(e.r);
  if (!fs.existsSync(file)) { errors.push(`spine: ${e.r} (${e.id}) has no page`); return; }
  const html = fs.readFileSync(file, 'utf8');
  const pager = html.match(/<div class="pagination-links[^"]*"[^>]*>([\s\S]*?)<\/div>/)?.[1] ?? '';
  const rel = (name, where) => [...where.matchAll(new RegExp(`<a\\s[^>]*rel="${name}"[^>]*>`, 'g'))].map((m) => m[0].match(/href="([^"]*)"/)?.[1]).filter((h) => h != null);
  const want = { prev: spine[i - 1]?.r ?? null, next: spine[i + 1]?.r ?? null };
  const isLast = i === spine.length - 1;
  for (const name of ['prev', 'next']) {
    if (name === 'next' && isLast) continue; // the last page leads home: checked with its Next button below
    const got = rel(name, pager);
    if (want[name] === null) { if (got.length) errors.push(`spine: ${e.r} is first in the spine but has a ${name} link (${got[0]})`); continue; }
    if (!got.length) errors.push(`spine: ${e.r} has no ${name} link (want ${want[name]})`);
    else if (got.some((h) => norm(h) !== norm(want[name]))) errors.push(`spine: ${e.r} ${name} link goes to ${got.join(', ')}, the spine says ${want[name]}`);
  }
  // any other rel="next" on the page (the big Next button) agrees with the spine
  const body = html.replace(/<div class="pagination-links[\s\S]*?<\/div>/, '');
  const buttons = rel('next', body);
  if (isLast) {
    // the last page: at least one next link, pager or big button, and all of them home
    const got = [...rel('next', pager), ...buttons];
    if (!got.length) errors.push(`spine: ${e.r} is last in the spine but has no next link (want one to /)`);
    for (const h of got) if (norm(h) !== '/') errors.push(`spine: ${e.r} is last; its next links must go home, not ${h}`);
  } else {
    for (const h of buttons) if (norm(h) !== norm(want.next)) errors.push(`spine: ${e.r} has a Next button to ${h}, the spine says ${want.next}`);
  }
});

// Course pages: home, /course/... and the lesson pages (all of them are course steps).
// Runpod stays in the field guide (Reference) only: never on these pages.
const coursePage = (url) => url === '/' || url.startsWith('/course/') || /^\/lessons\/[^/]+\/$/.test(url);
let runpodPages = 0;
for (const f of all.filter((x) => !isLabBook(x))) {
  const url = urlOf(f);
  const html = fs.readFileSync(f, 'utf8');
  const bodyHtml = html.slice(html.search(/<body[\s>]/i));
  if (coursePage(url)) {
    const text = visibleText(bodyHtml);
    for (const m of text.matchAll(new RegExp(VIDEO_N.source, 'gi'))) textProblems.push(`${url}: says "${m[0]}" (name the video by its title): "${around(text, m.index, m[0].length)}"`);
    // anywhere in the page's HTML (a hidden answer or an attribute counts too), not only the visible text
    const rp = bodyHtml.replace(/<script\b[\s\S]*?<\/script>/gi, ' ').match(new RegExp(RUNPOD.source, 'gi'));
    if (rp) {
      runpodPages++;
      const at = text.search(new RegExp(RUNPOD.source, 'i'));
      textProblems.push(`${url}: names ${[...new Set(rp.map((x) => x.toLowerCase()))].join(', ')} (Runpod stays in the field guide): "${at >= 0 ? around(text, at, 12) : 'in the markup'}"`);
    }
  }
  // emoji: anywhere in the visible text of a generated page (kit code in <pre> is the kit's, shown as is)
  const text = visibleText(bodyHtml);
  const e = text.match(new RegExp(EMOJI.source, 'gu'));
  if (e) {
    const at = text.search(new RegExp(EMOJI.source, 'u'));
    textProblems.push(`${url}: contains emoji ${[...new Set(e)].join(' ')}: "${around(text, at, 2)}"`);
  }
}

// The code download
{
  const zip = path.join(DIST, 'downloads', '03-labs.zip');
  if (!fs.existsSync(zip)) errors.push('downloads/03-labs.zip is missing');
  else {
    const head = fs.readFileSync(zip).subarray(0, 4);
    if (fs.statSync(zip).size < 1000 || head[0] !== 0x50 || head[1] !== 0x4b) errors.push('downloads/03-labs.zip is not a zip');
  }
}

console.log(`check-links: ${checked} links in ${all.length} pages; spine: ${spine.length} pages (${Object.entries(kinds).map(([k, n]) => `${n} ${k}`).join(', ')}); Runpod on ${runpodPages} course page(s)`);
for (const p of textProblems) console.error(`check-links: ${STRICT ? '' : 'warning: '}${p}`);
if (errors.length) for (const e of errors) console.error(`check-links: ${e}`);
if (errors.length || (STRICT && textProblems.length)) process.exit(1);
