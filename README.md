# The Local Node

Open learning materials for people who build and explain technology. Each track lives in `tracks/` so future subjects can be added without changing the first one.

## Learning tracks

| Track | Start online | Source |
| --- | --- | --- |
| AI Field Engineer | [Start the course](https://thelocalnode.dev/ai-field-engineer/) | [`tracks/ai-field-engineer/`](tracks/ai-field-engineer/) |

## Build the website

Install Node.js 24 or later. Then:

```sh
npm ci
npm run build
npm run dev
```

The build writes `dist/`, with one directory per learning track. `npm run deploy` publishes it with Cloudflare Wrangler when your Cloudflare account is authenticated. The AI Field Engineer track uses Astro Starlight and builds its pages from the Markdown, YAML, lab code, and videos in its directory.

## Extend the site

Add a directory under `tracks/` for another subject, add its build step to `scripts/build.mjs`, and add a card to the landing page in `scripts/build.mjs`. Keep any service credentials in environment variables or a private secret manager. Never add them to this repository.

Brand concepts and editable generation prompts live in [`assets/brand/`](assets/brand/). They can be adapted for website, repository, and video artwork.

To refresh the video posters, install ffmpeg and run `npm run posters`. You do not need ffmpeg to build the site.
