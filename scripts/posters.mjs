import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const root = path.resolve(import.meta.dirname, '..');
const track = path.join(root, 'tracks/ai-field-engineer');
const out = path.join(track, 'assets/posters');
fs.mkdirSync(out, { recursive: true });
const times = new Map(fs.readFileSync(path.join(track, '05-web/posters.txt'), 'utf8')
  .split('\n').filter(line => line.trim() && !line.startsWith('#'))
  .map(line => line.trim().split(/\s+/)));
for (const file of fs.readdirSync(path.join(track, '01-videos')).filter(f => f.endsWith('.mp4'))) {
  const stem = file.slice(0, -4);
  execFileSync('ffmpeg', [
    '-y', '-loglevel', 'error', '-ss', times.get(stem) ?? '9.5',
    '-i', path.join(track, '01-videos', file), '-frames:v', '1',
    '-vf', 'format=rgb24,drawbox=x=0:y=ih*0.8:w=iw:h=ih:color=0x0C0E14:t=fill,scale=960:-2',
    '-q:v', '4', path.join(out, `${stem}.jpg`),
  ]);
  console.log(stem);
}
