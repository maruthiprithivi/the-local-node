import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { repositoryFiles, codeUrl } from './repository.mjs';
import { restrictedPath } from '../../../scripts/check-public-repository.mjs';
import { stepCode, transformReadme } from './course-pages.mjs';

test('shared lab links back to both steps, in course order; regeneration is stable', () => {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), 'tln-links-test-'));
  const rel = '03-labs/lessons/16-training-toy';
  const file = `tracks/ai-field-engineer/${rel}/README.md`;
  fs.mkdirSync(path.dirname(path.join(repo, file)), { recursive: true });
  fs.writeFileSync(path.join(repo, file), '# Training toys\n\n> **Time:** 30 min\n\n## Run\n\nKeep this explanation.\n');
  const lesson = { dir: '16-training-toy', rel, files: ['toy_alignment.py'] };
  const first = { n: 1, title: 'Part 1', route: '/lessons/16-training-toy/', lesson };
  const second = { n: 1, title: 'Part 2', route: '/course/day-12/training-toys-part-2/', lesson };
  const model = { days: [{ n: 11, steps: [first] }, { n: 12, steps: [second] }] };
  try {
    const files = repositoryFiles(model, repo);
    const readme = files.get(file);
    assert.match(readme, /Day 11.*Part 1[\s\S]*Day 12.*Part 2/);
    assert.match(readme, /Keep this explanation\./);
    assert.match(readme, /^# Training toys\n\n> \*\*Time:\*\* 30 min\n\n<!-- course-links:start -->/);
    assert.match(readme, /Full course sequence\]\(https:\/\/github.com\/maruthiprithivi\/the-local-node\/blob\/main\/tracks\/ai-field-engineer\/COURSE.md\)/);
    assert.match(files.get('tracks/ai-field-engineer/COURSE.md'), /training-toys-part-2/);
    fs.writeFileSync(path.join(repo, file), readme);
    assert.equal(repositoryFiles(model, repo).get(file), readme);
    fs.writeFileSync(path.join(repo, file), readme.replace('<!-- course-links:end -->', ''));
    assert.throws(() => repositoryFiles(model, repo), /Malformed generated backlink/);
    const html = stepCode(first, model, { fileBlock: () => 'code' });
    assert.ok(html.includes(codeUrl(rel)));
    assert.ok(!transformReadme(readme, first).includes('Follow this lesson on the website'));
  } finally { fs.rmSync(repo, { recursive: true }); }
});

test('public repository blocks private and credential paths, allowing placeholder examples', () => {
  for (const file of ['.env', 'a/.env.local', 'key.pem', 'keys/id_ed25519', 'secrets/provider.enc.env', 'website/ai-field-engineer/public/media/foundations/code-walkthrough.mp4', 'tracks/ai-field-engineer/04-video-source/foundations/src/index.tsx']) assert.ok(restrictedPath(file), file);
  for (const file of ['tracks/ai-field-engineer/03-labs/.env.example', 'tracks/ai-field-engineer/03-labs/lessons/05-kv-cache/kv_calc.py', 'scripts/check-public-repository.mjs']) assert.equal(restrictedPath(file), false, file);
  assert.throws(() => codeUrl('03-labs/../../private/key'), /public code path/);
});
