import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

export function restrictedPath(file) {
  const name = path.posix.basename(file);
  return /(^|\/)(secrets|private|study-private|study-lab|interview-prep)(\/|$)/i.test(file)
    || /(^|\/)(\.env(\..+)?|\.envrc|\.netrc|\.npmrc|\.pypirc|\.pgpass|id_(rsa|ed25519|ecdsa))$/i.test(file) && name !== '.env.example'
    || /\.(pem|key|p12|pfx|age|sops)$/i.test(name)
    || /^(credentials|service-account).*\.json$/i.test(name)
    || /^(tracks\/ai-field-engineer\/04-video-source\/foundations|website\/ai-field-engineer\/(course\/content|public\/media)\/foundations)(\/|$)/.test(file);
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const root = path.resolve(import.meta.dirname, '..');
  const git = args => execFileSync('git', args, { cwd: root, encoding: 'utf8', maxBuffer: 20 * 1024 * 1024 });
  const tracked = git(['ls-files', '-z']).split('\0').filter(Boolean);
  const historical = git(['log', '--all', '--format=', '--name-only']).split('\n').filter(Boolean);
  const blocked = [...new Set([...tracked, ...historical].filter(restrictedPath))];
  if (blocked.length) {
    console.error(`Private or credential paths in the public repository (values are not printed):\n${blocked.join('\n')}`);
    process.exitCode = 1;
  } else console.log(`Public path check passed: ${tracked.length} tracked files and fetched Git history. Run Gitleaks separately for credential content.`);
}
