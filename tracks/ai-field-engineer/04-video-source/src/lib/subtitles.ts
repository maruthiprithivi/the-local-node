/** Split narration into subtitle chunks and time them across the scene's audio. */
export type Cue = { text: string; from: number; dur: number };

const MAX_CHARS = 92;

export const chunkText = (text: string): string[] => {
  const sentences = text.replace(/\s+/g, ' ').trim().match(/[^.!?]+[.!?]*/g) ?? [text];
  const out: string[] = [];
  for (const raw of sentences) {
    const s = raw.trim();
    if (!s) continue;
    if (s.length <= MAX_CHARS) { out.push(s); continue; }
    const parts = s.split(/(?<=[,;:])\s+/);
    let buf = '';
    for (const part of parts) {
      if ((buf + ' ' + part).trim().length <= MAX_CHARS) {
        buf = (buf + ' ' + part).trim();
      } else {
        if (buf) out.push(buf);
        if (part.length <= MAX_CHARS) { buf = part; continue; }
        const words = part.split(' ');
        buf = '';
        for (const w of words) {
          if ((buf + ' ' + w).trim().length <= MAX_CHARS) buf = (buf + ' ' + w).trim();
          else { out.push(buf); buf = w; }
        }
      }
    }
    if (buf) out.push(buf);
  }
  return out;
};

/** Distribute durationInFrames across cues by character count, with a floor per cue. */
export const cuesFor = (text: string, durationInFrames: number, fps: number): Cue[] => {
  const chunks = chunkText(text);
  if (!chunks.length) return [];
  const chars = chunks.map((c) => c.length);
  const total = chars.reduce((a, b) => a + b, 0);
  const minFrames = Math.round(fps * 0.9);
  let frames = chars.map((c) => Math.max(minFrames, Math.round((c / total) * durationInFrames)));
  const sum = frames.reduce((a, b) => a + b, 0);
  if (sum > durationInFrames) {
    const k = durationInFrames / sum;
    frames = frames.map((f) => Math.max(Math.round(fps * 0.6), Math.floor(f * k)));
  }
  let at = 0;
  return chunks.map((text, i) => {
    const from = at;
    at += frames[i];
    const last = i === chunks.length - 1;
    return { text, from, dur: last ? Math.max(frames[i], durationInFrames - from) : frames[i] };
  });
};
