# Keep lessons and code aligned

The public companion repository is [maruthiprithivi/the-local-node](https://github.com/maruthiprithivi/the-local-node). The [website](https://thelocalnode.dev/) teaches the sequence; this repository holds the runnable examples. Start with the [course-to-code index](tracks/ai-field-engineer/COURSE.md). Each lab README links back to its exact website step, including both parts when a lab spans multiple days. Website code sections link to the same folder and individual files on GitHub.

## Change a lesson

1. Edit the lab code and README under `tracks/ai-field-engineer/03-labs/lessons/`.
2. Update its explanation in `website/ai-field-engineer/course/content/day-NN.yaml`. Change ordering in `course/course.yaml`, preserving published progress IDs and routes.
3. From the repository root, run `node website/ai-field-engineer/scripts/repository.mjs --write`. Commit the generated `COURSE.md` and README backlinks with the lesson change.
4. Run `node website/ai-field-engineer/scripts/repository.mjs --check`, `node --test website/ai-field-engineer/scripts/repository.test.mjs`, and the appropriate lab checks. Build the website with `cd website && npm run build` when changing course content or rendering.
5. Submit a pull request. Keep code, explanations, expected results and website links in the same change. After merge, the production website still needs its normal deployment.

Install website dependencies from its lockfile first: `cd website/ai-field-engineer && npm ci --ignore-scripts`. The root GitHub Actions workflow checks link alignment and scans fetched history with a checksum-pinned [Gitleaks](https://github.com/gitleaks/gitleaks) release. It uses a read-only token and does not execute dependency lifecycle scripts.

## Before the first push

Install Gitleaks (`brew install gitleaks` on macOS), then enable the repository's local hook:

```sh
git config --local core.hooksPath .githooks
node scripts/check-public-repository.mjs
gitleaks git . --redact --no-banner --log-opts=--all
```

The pre-push hook fails if Gitleaks is unavailable, links are stale, or private/credential paths are tracked. CI runs the checks again. Enable GitHub push protection in repository security settings where available; CI runs after upload and cannot prevent a first disclosure. Hooks can be bypassed and scanners are not proof that arbitrary content is safe, so review the exact staged diff before every public push.

Keep real keys, tokens, cookies, account exports, private study/interview materials, personal datasets, run logs and machine-specific state outside the public commit. `.env.example` contains names and placeholders only; learners supply their own credentials locally. Private materials are not safe to commit merely because the deployed website hides them. Do not add private data to screenshots, recordings or downloadable archives either.

If a real credential reaches GitHub, treat it as exposed: revoke/rotate it through the owning provider, then coordinate history cleanup. Do not post the value in an issue. Report sensitive material privately through [GitHub's vulnerability reporting](https://github.com/maruthiprithivi/the-local-node/security/advisories/new) if enabled, rather than a public issue.

## Existing dependency audit · 18 October 2026

The current lockfiles were audited without changing dependency versions. The course build reports 3 high and 11 moderate affected packages; the publishing tools report 4 high affected packages (counts include transitive dependents). These results are not a clean dependency audit.

The high findings concern [HTTP cache semantics](https://github.com/advisories/GHSA-ch52-4w7c-c8xp), [Sharp's SVG dependency](https://github.com/advisories/GHSA-wq5f-xc86-pv6w), [source-map parsing](https://github.com/advisories/GHSA-68fv-2mgg-jv7q), and Undici through local Wrangler/Miniflare tooling. They are deferred from this lesson-link change: the site exports static files, these Node packages are not shipped as the public request handler, and this change adds no upload, proxy, image-processing or shared authenticated cache endpoint. Build and local development tools remain affected; process reviewed inputs and keep development servers local. Review compatible dependency updates separately by 1 November 2026, and before introducing server rendering or untrusted asset processing. Do not apply the audit's suggested major Starlight downgrade automatically.
