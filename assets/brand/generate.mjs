import fs from 'node:fs/promises';
import path from 'node:path';

const key = process.env.GEMINI_API_KEY;
if (!key) throw new Error('GEMINI_API_KEY is required');

const concepts = {
  signal: 'A premium editorial banner background for THE LOCAL NODE, an open learning publication about practical technology. Wide 16:9 composition. Deep midnight navy field, a single precise warm amber signal line traveling through a sparse network of small geometric nodes, subtly becoming paths and branching into new topics. Material feeling of screenprinted ink and fine technical drafting, exceptional restrained composition, lots of calm negative space in the central safe area for typography. No people, no robots, no brains, no logos, no letters, no words, no UI, no watermark.',
  workshop: 'A premium editorial banner background for THE LOCAL NODE, an open learning publication about practical technology. Wide 16:9 composition. Tactile modern workshop still life: an elegant modular system of tiny physical blocks, transparent acrylic layers and fine wires on a warm off-white desk, one vivid vermilion connector bridging modules. Sunlight and architectural shadows, photographed with art direction of a high-end design magazine. Evokes learning by building and room for many future subjects. Keep the center clear for typography. No people, no computers, no logos, no letters, no words, no UI, no watermark.',
  atlas: 'A premium editorial banner background for THE LOCAL NODE, an open learning publication about practical technology. Wide 16:9 composition. Abstract cartographic field of thin cobalt-blue contour lines, quiet grids and small navigational marks on warm ivory paper. A bold coral-red circular node sits off-center, with several clean pathways expanding across the map. Sophisticated visual system for an educational publisher, precise and optimistic, printed-paper texture, generous clean central space for typography. No people, no robots, no logos, no letters, no words, no UI, no watermark.',
  relay: 'Create a premium 16:9 editorial brand background for The Local Node, an open publication where people learn technology by building. Art direction: a dramatic but restrained dark ink-blue photographic scene, with a few large translucent smoked-glass discs and one vivid warm-orange cable or light path connecting them. The objects live near the left and right outer edges; the middle 55 percent is a nearly uniform deep-blue quiet field reserved for a large white title. Sophisticated architectural lighting, tactile materials, subtle grain, believable depth. Make it feel like a publisher with many future subjects, not a specific AI course. Absolutely no text, letters, digits, logos, humans, screens, robots, brains, interface elements, or watermark.',
  folio: 'Create a premium 16:9 editorial brand background for The Local Node, an open publication where people learn technology by building. Art direction: bold contemporary print design on warm uncoated ivory paper, with oversized cropped cobalt-blue and vermilion geometric forms and a few precise fine-line paths, like a beautiful design annual. Strong flat shapes, subtle ink texture, confident asymmetric composition. Place the visual forms around the outside and keep the central horizontal 55 percent calm and light so dark typography can sit there. The visual language must extend naturally to book covers and YouTube thumbnails on many subjects. Absolutely no text, letters, digits, logos, humans, screens, robots, brains, interface elements, or watermark.',
  modules: 'Create a premium 16:9 editorial brand background for The Local Node, an open publication where people learn technology by building. Art direction: an elegant physical still life of a few large matte cobalt, terracotta, and cream wooden modules, connected by a single fine orange line. Photographed against a warm pale-grey seamless studio background with long soft daylight shadows, sophisticated and striking at small size. Put the objects toward both outer thirds, leaving the central horizontal 55 percent calm, bright and clear for dark typography. Suggest assembly, curiosity, and practical learning without depicting a particular subject. Absolutely no text, letters, digits, logos, humans, screens, robots, brains, interface elements, or watermark.',
};

const out = path.resolve(import.meta.dirname, 'concepts');
await fs.mkdir(out, { recursive: true });

const selected = process.argv.slice(2);
for (const name of selected.length ? selected : Object.keys(concepts)) {
  const prompt = concepts[name];
  if (!prompt) throw new Error(`Unknown concept: ${name}`);
  if (await fs.stat(path.join(out, `${name}.jpg`)).then(() => true, () => false)) {
    console.log(`${name}: already exists, skipping`);
    continue;
  }
  const response = await fetch('https://generativelanguage.googleapis.com/v1beta/interactions', {
    method: 'POST',
    headers: { 'x-goog-api-key': key, 'content-type': 'application/json' },
    body: JSON.stringify({
      model: name === 'signal' || name === 'workshop' || name === 'atlas' ? 'gemini-3.1-flash-image' : 'gemini-3-pro-image',
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
