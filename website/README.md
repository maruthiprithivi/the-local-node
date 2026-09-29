# The Local Node website

This directory contains the publishing app for [thelocalnode.dev](https://thelocalnode.dev). Learning materials stay in [`../tracks/`](../tracks/); this app turns them into guided pages.

## Run locally

Install Node.js 24 or later, then run these commands from `website/`:

```sh
npm ci
npm run dev
```

`npm run dev` builds the static site and serves it with Wrangler. `npm run build` writes the publishable files to `website/dist/`. The first build also installs the dependencies of `ai-field-engineer/`. To refresh video poster images, install ffmpeg and run `npm run posters`.

## Layout

```text
website/
├── ai-field-engineer/   Astro pages, lesson content, and search indexing
├── scripts/             multi-track build and poster tools
├── package.json         build, local server, and deploy commands
└── wrangler.jsonc       Cloudflare domain and static asset settings
```

The build places each course under its own URL path. For this track, edit the guided lessons in `ai-field-engineer/course/content/` and the runnable labs in `../tracks/ai-field-engineer/03-labs/`. Add another subject by creating its track directory and website source, then add its build step and home-page card in `scripts/build.mjs`.

## Publish

`npm run deploy` builds and publishes the site to Cloudflare from an authenticated Wrangler session. Keep service credentials in your own environment or secret manager. Do not commit them or generated `dist/` files.
