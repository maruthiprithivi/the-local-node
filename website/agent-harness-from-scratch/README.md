# Harness course website

Astro/Starlight integration for `tracks/agent-harness-from-scratch`, published by
the root website build at `/agent-harness-from-scratch/`. The dependency versions
and theme follow the existing AI Field Engineer site. There is no new framework.

`scripts/sync.mjs` reads the canonical optional foundations module, lessons 1–32 (29–32 are optional extensions),
and lab-book Markdown. It generates navigation, lesson pages, source/lab links,
video transcript alternatives, and local device progress. It refuses a missing or
duplicate lesson number in 00–32 and broken local Markdown links. The generated directory
is disposable; it never modifies learner code or canonical course materials.

The runnable lab source remains independently available on GitHub. No credentials,
state databases, environment files, or learner-generated output are copied into the
website. Recordings are optional; the reading and examples provide the required
learning path. Progress is a learner self-check, not a claim that tests passed.

## Approved Linux worker commands

Use Node.js 24 or later. From this directory:

```sh
npm ci --no-audit --no-fund
npm run build
```

Run the root `website/` build as well to check assembled local links and the home
card. Set `COURSE_SOURCE_REF` to the reviewed source ref when publishing a later
version. Update `validation.json` only from recorded validation evidence.

No builds, tests, lint, hooks, package installation, or preview were run on the
source-only Mac. Publication and deployment remain separate decisions.
