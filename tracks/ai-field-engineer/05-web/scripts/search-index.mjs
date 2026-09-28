// Post-build search index. Replaces the index Starlight wrote, with these changes:
// - code line numbers and file-size notes are left out, so excerpts read as prose
// - each lab card (F1..F7, L1..L9, T1..T3) becomes its own result, linked to #lab-XX, and each day of the
//   lab book's plan one linked to that day of the course (/course/day-N/). Both are built by the lab
//   book's script, so the page's static HTML (all Pagefind sees) does not contain them.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import * as pagefind from 'pagefind';

const WEB = path.resolve(import.meta.dirname, '..');
const DIST = path.join(WEB, 'dist');
const LAB_BOOK = 'field-engineer-lab-book.html';

// An array literal from the lab book's script (`const NAME = [` ... a line starting with `];`), as data.
function arrayLiteral(html, name) {
  const at = html.indexOf(`const ${name} = [`);
  if (at < 0) throw new Error(`lab book: ${name} not found`);
  const start = html.indexOf('[', at);
  const end = html.slice(start).search(/\n\s*\];/) + start;
  return vm.runInNewContext(`(${html.slice(start, end).trimEnd()}\n])`, {}, { timeout: 1000 });
}

const ok = (res) => {
  if (res.errors?.length) throw new Error(`pagefind: ${res.errors.join('; ')}`);
  return res;
};

fs.rmSync(path.join(DIST, 'pagefind'), { recursive: true, force: true }); // Starlight's index, replaced below
const { index } = ok(await pagefind.createIndex({
  excludeSelectors: ['.expressive-code .gutter', '.expressive-code .sr-only', 'details.kit-file > summary > span'],
}));
const { page_count } = ok(await index.addDirectory({ path: DIST }));

const html = fs.readFileSync(path.join(DIST, 'lab-book', LAB_BOOK), 'utf8');
const cards = ['FW_LABS', 'SP_LABS', 'TR_LABS'].flatMap((name) => arrayLiteral(html, name));
for (const c of cards) {
  const steps = (c.steps ?? []).map((s) => s.filter(Boolean).join(': ')).join('\n');
  // The card's commands and code snippet are left out: as excerpts they read as a blob of code.
  ok(await index.addCustomRecord({
    url: `/lab-book/${LAB_BOOK}#lab-${c.id}`,
    language: 'en',
    meta: { title: `Lab card ${c.id} · ${c.title}` },
    content: [c.title, c.goal, c.where, c.time, c.cost, c.repo && `lessons/${c.repo}`, steps, c.say].filter(Boolean).join('\n'),
  }));
}
// The lab book's day plan: each day's record leads to that day of the course (/course/day-N/), whose
// overview is the course's version of the plan. The course day titles come from the spine sync.mjs wrote.
const spineCtx = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(DIST, 'kit-spine.js'), 'utf8'), spineCtx, { timeout: 1000 });
const courseDays = new Map((spineCtx.window.KIT_SPINE ?? []).filter((e) => e.k === 'day').map((e) => [e.day, e]));
const plan = arrayLiteral(html, 'D'); // [title, what to do, what you end up with] per day
for (const [i, [title, todo, result]] of plan.entries()) {
  const day = courseDays.get(i + 1);
  if (!day) throw new Error(`lab book plan day ${i + 1} has no course day in kit-spine.js`);
  ok(await index.addCustomRecord({
    // #_top (the page title) keeps the URL distinct from the day page's own record: one record per URL
    url: `${day.r}#_top`,
    language: 'en',
    meta: { title: `${day.t} · the lab book plan` },
    content: [title, todo, result].join('\n'),
  }));
}

ok(await index.writeFiles({ outputPath: path.join(DIST, 'pagefind') }));
await pagefind.close();
console.log(`search-index: ${page_count} pages + ${cards.length} lab cards + ${plan.length} plan days`);
