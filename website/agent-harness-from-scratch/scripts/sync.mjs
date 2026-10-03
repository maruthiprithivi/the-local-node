// Read canonical track Markdown; only generated website files are replaced.
// Run on an approved build worker before Astro. Never executes Python or live providers.
import fs from 'node:fs';
import path from 'node:path';

const web = path.resolve(import.meta.dirname, '..');
const track = path.resolve(web, '../../tracks/agent-harness-from-scratch');
const docs = path.join(web, 'src/content/docs');
const prefix = '/agent-harness-from-scratch';
const ref = process.env.COURSE_SOURCE_REF ?? 'course/agent-harness-from-scratch-20261003';
const source = `https://github.com/maruthiprithivi/the-local-node/blob/${ref}/tracks/agent-harness-from-scratch`;
const tree = source.replace('/blob/', '/tree/');
const esc = text => String(text).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const entries = dir => fs.readdirSync(path.join(track, dir), { withFileTypes: true });
const read = file => fs.readFileSync(path.join(track, file), 'utf8');
const titleOf = (file, fallback) => /^#\s+(.+)$/m.exec(read(file))?.[1] ?? fallback;
const lessons = entries('03-labs/lessons').filter(entry => entry.isDirectory() && /^\d\d-/.test(entry.name))
  .map(entry => ({ dir: entry.name, number: Number(entry.name.slice(0, 2)), file: `03-labs/lessons/${entry.name}/README.md` }))
  .sort((a, b) => a.number - b.number);
if (lessons.length !== 33 || lessons.some((lesson, i) => lesson.number !== i)) {
  throw new Error('Expected optional foundation 00 and lessons 01–32 exactly once; refusing a partial course build.');
}
const pages = lessons.map(lesson => ({
  ...lesson, slug: `lessons/${lesson.dir}`, title: titleOf(lesson.file, lesson.dir), id: `lesson-${String(lesson.number).padStart(2, '0')}`,
}));
pages.push({ file: '01-videos/README.md', slug: 'videos/recordings', title: titleOf('01-videos/README.md', 'Videos and reading alternatives') });
for (const dir of ['02-lab-book', '04-video-source']) {
  for (const entry of entries(dir)) {
    if (entry.isFile() && entry.name.endsWith('.md')) {
      const file = `${dir}/${entry.name}`;
      pages.push({ file, slug: `${dir === '02-lab-book' ? 'lab-book' : 'videos'}/${entry.name.replace(/\.md$/, '').toLowerCase()}`, title: titleOf(file, entry.name) });
    }
  }
}
const routeOf = page => `${prefix}/${page.slug}/`;
const routes = new Map(pages.map(page => [page.file, routeOf(page)]));
routes.set('README.md', `${prefix}/`);
const rewriteLinks = (markdown, file) => markdown.replace(/\[([^\]]*)\]\(([^\s)]+)\)/g, (original, label, href) => {
  if (/^(?:[a-z][a-z\d+.-]*:|\/|#)/i.test(href)) return original;
  const [target, fragment] = href.split('#', 2);
  const relative = path.posix.normalize(path.posix.join(path.posix.dirname(file), target));
  const suffix = fragment ? `#${fragment}` : '';
  if (routes.has(relative)) return `[${label}](${routes.get(relative)}${suffix})`;
  // Runnable source files remain canonical on GitHub; the site never executes them.
  if (relative.startsWith('../')) return original;
  const abs = path.join(track, relative);
  if (!fs.existsSync(abs)) throw new Error(`Broken source link in ${file}: ${href}`);
  return `[${label}](${fs.statSync(abs).isDirectory() ? tree : source}/${relative}${suffix})`;
});
const validation = JSON.parse(fs.readFileSync(path.join(web, 'validation.json'), 'utf8'));
const note = `<aside class="harness-note"><strong>Validation status</strong><p>${esc(validation.summary)}</p><p>Offline fake responses and synthetic fixtures are the default. Live providers require explicit opt-in. These exercises do not establish a production security guarantee.</p></aside>`;
const progress = '<div class="harness-progress" data-harness-progress><p>Self-check progress is stored on this device when browser storage is available. Without JavaScript, use the lesson links below.</p></div>';
const write = (slug, title, body) => {
  const file = path.join(docs, `${slug}.md`);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `---\ntitle: ${JSON.stringify(title)}\n---\n\n${body}\n`);
};
fs.rmSync(docs, { recursive: true, force: true });
fs.mkdirSync(docs, { recursive: true });
fs.mkdirSync(path.join(web, 'src/generated'), { recursive: true });
const lessonPages = pages.filter(page => page.id);
for (const page of pages) {
  const markdown = rewriteLinks(read(page.file).replace(/^#\s+.+\n/, ''), page.file);
  let navigation = '';
  if (page.id) {
    const i = lessonPages.indexOf(page);
    const before = lessonPages[i - 1], after = lessonPages[i + 1];
    navigation = `<nav class="harness-navigation" aria-label="Lesson order">${before ? `<a href="${routeOf(before)}">Previous: ${esc(before.title)}</a>` : `<a href="${prefix}/">Course map</a>`}${after ? `<a href="${routeOf(after)}">Next: ${esc(after.title)}</a>` : `<a href="${prefix}/">Return to the course map</a>`}</nav>`;
  }
  const lab = page.id ? `[Open the runnable lesson and exercises](${tree}/03-labs/lessons/${page.dir}/) · ` : '';
  const media = page.id ? `\n\n**Video alternative:** Read this lesson and its worked examples. [Recording availability](${prefix}/videos/recordings/) and [narration sources](${prefix}/videos/readme/) describe optional aids; no recording is required for the checks.\n` : '';
  write(page.slug, page.title, `${note}\n\n${page.id ? progress : ''}\n\n${lab}[View canonical source](${source}/${page.file})\n\n${markdown}${media}\n${navigation}`);
}
const list = modules => modules.map(page => `- [${page.title}](${routeOf(page)})`).join('\n');
const books = pages.filter(page => page.slug.startsWith('lab-book/'));
const map = pages.find(page => page.file === '02-lab-book/course-map.md');
if (!map) throw new Error('Missing canonical course-map.md');
if (!pages.some(page => page.file === '04-video-source/README.md')) throw new Error('Missing transcript/video source index');
write('index', 'Build an agent harness from scratch', `${note}\n\nBuild one small Python package from a deterministic response to bounded coding, synthetic SRE, and resident automation. Follow the lessons at your own pace. Every stage extends the same harness; there is no final project requirement.\n\n${progress}\n\n[Course map and checkpoint guide](${routeOf(map)}) · [Runnable labs](${tree}/03-labs/) · [Videos and reading alternatives](${prefix}/videos/recordings/)\n\n## Optional foundations\n\n${list(lessonPages.slice(0, 1))}\n\n## Core: lessons 1–14\n\n${list(lessonPages.slice(1, 15))}\n\n## Advanced: lessons 15–28\n\n${list(lessonPages.slice(15, 29))}\n\n## Optional advanced extensions: lessons 29–32\n\nContinue into optional framework integration, mention-triggered work, shared memory, and collaboration between separate harnesses. The core remains framework-free, and all required extension checks use offline fixtures.\n\n${list(lessonPages.slice(29))}\n\n## Lab book\n\n${list(books)}\n\n## Five shared provider helpers\n\nOpenAI, Gemini, DeepSeek, Ollama, and NVIDIA adapters share a small contract while retaining provider-specific capabilities. Required exercises use recorded synthetic responses without keys, downloads, or paid calls.\n\n[Browse all course source](${tree}/)\n`);
fs.writeFileSync(path.join(web, 'src/generated/sidebar.json'), JSON.stringify([
  // Starlight prefixes its sidebar links with the configured base. Authored body
  // links and the browser progress spine above already carry the complete URL.
  { label: 'Course map', link: '/' },
  { label: 'Optional foundations', items: lessonPages.slice(0, 1).map(page => ({ label: page.title, link: `/${page.slug}/` })) },
  { label: 'Core · lessons 1–14', items: lessonPages.slice(1, 15).map(page => ({ label: page.title, link: `/${page.slug}/` })) },
  { label: 'Advanced · lessons 15–28', items: lessonPages.slice(15, 29).map(page => ({ label: page.title, link: `/${page.slug}/` })) },
  { label: 'Optional extensions · lessons 29–32', items: lessonPages.slice(29).map(page => ({ label: page.title, link: `/${page.slug}/` })) },
  { label: 'Lab book', items: books.map(page => ({ label: page.title, link: `/${page.slug}/` })) },
  { label: 'Videos and transcripts', items: [
    { label: 'Recording availability and reading alternatives', link: '/videos/recordings/' },
    { label: 'Narration and transcript sources', link: '/videos/readme/' },
  ] },
]));
fs.writeFileSync(path.join(web, 'public/course-spine.js'), `window.HARNESS_SPINE = ${JSON.stringify(lessonPages.map(page => ({ id: page.id, title: page.title, route: routeOf(page), optional: page.number === 0 || page.number >= 29 }))).replaceAll('<', '\\u003c')};\n`);
console.log(`Harness course: ${lessonPages.length} modules, ${books.length} lab-book pages; ${validation.summary}`);
