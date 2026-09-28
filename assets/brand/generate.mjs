import fs from 'node:fs/promises';
import path from 'node:path';

const key = process.env.GEMINI_API_KEY;
if (!key) throw new Error('GEMINI_API_KEY is required');

const concepts = {
  signal: 'A premium editorial banner background for THE LOCAL NODE, an open learning publication about practical technology. Wide 16:9 composition. Deep midnight navy field, a single precise warm amber signal line traveling through a sparse network of small geometric nodes, subtly becoming paths and branching into new topics. Material feeling of screenprinted ink and fine technical drafting, exceptional restrained composition, lots of calm negative space in the central safe area for typography. No people, no robots, no brains, no logos, no letters, no words, no UI, no watermark.',
  workshop: 'A premium editorial banner background for THE LOCAL NODE, an open learning publication about practical technology. Wide 16:9 composition. Tactile modern workshop still life: an elegant modular system of tiny physical blocks, transparent acrylic layers and fine wires on a warm off-white desk, one vivid vermilion connector bridging modules. Sunlight and architectural shadows, photographed with art direction of a high-end design magazine. Evokes learning by building and room for many future subjects. Keep the center clear for typography. No people, no computers, no logos, no letters, no words, no UI, no watermark.',
  atlas: 'A premium editorial banner background for THE LOCAL NODE, an open learning publication about practical technology. Wide 16:9 composition. Abstract cartographic field of thin cobalt-blue contour lines, quiet grids and small navigational marks on warm ivory paper. A bold coral-red circular node sits off-center, with several clean pathways expanding across the map. Sophisticated visual system for an educational publisher, precise and optimistic, printed-paper texture, generous clean central space for typography. No people, no robots, no logos, no letters, no words, no UI, no watermark.',
};

const out = path.resolve(import.meta.dirname, 'concepts');
await fs.mkdir(out, { recursive: true });

for (const [name, prompt] of Object.entries(concepts)) {
  const response = await fetch('https://generativelanguage.googleapis.com/v1beta/interactions', {
    method: 'POST',
    headers: { 'x-goog-api-key': key, 'content-type': 'application/json' },
    body: JSON.stringify({
      model: 'gemini-3.1-flash-image',
      input: prompt,
      response_format: { type: 'image', aspect_ratio: '16:9', image_size: '2K' },
    }),
  });
  if (!response.ok) throw new Error(`${name}: Gemini returned HTTP ${response.status}: ${(await response.text()).slice(0, 500)}`);
  const result = await response.json();
  const image = result.output_image ?? result.steps?.flatMap(s => s.content ?? []).find(c => c.type === 'image');
  if (!image?.data) throw new Error(`${name}: Gemini returned no image`);
  const ext = image.mime_type === 'image/jpeg' ? 'jpg' : 'png';
  const file = path.join(out, `${name}.${ext}`);
  await fs.writeFile(file, Buffer.from(image.data, 'base64'));
  console.log(`${name}: ${file}`);
}
