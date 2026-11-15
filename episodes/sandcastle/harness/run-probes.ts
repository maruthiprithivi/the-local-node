import { mkdir, writeFile, rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import { createSandbox } from "@ai-hero/sandcastle";
import { docker } from "@ai-hero/sandcastle/sandboxes/docker";

const here = dirname(fileURLToPath(import.meta.url));
const episodeRoot = resolve(here, "..");
const taskRepo = process.env.TASK_REPO ?? resolve(episodeRoot, "task-repo");
const outDir = process.env.PROBE_OUT ?? resolve(episodeRoot, "runs", "probes");
const imageName = process.env.SANDCASTLE_IMAGE ?? "sandcastle-opencode:0.14.0-local";
const dockerBin = "docker";

const sh = (cmd: string, args: string[]): Promise<{ code: number; stdout: string; stderr: string }> =>
  new Promise((resolveP, reject) => {
    const child = spawn(cmd, args, { env: process.env });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d) => (stdout += d.toString()));
    child.stderr.on("data", (d) => (stderr += d.toString()));
    child.on("error", reject);
    child.on("close", (code) => resolveP({ code: code ?? 1, stdout, stderr }));
  });

const inspectJson = async (container: string): Promise<unknown> => {
  const r = await sh(dockerBin, [
    "inspect",
    container,
    "--format",
    "{{json .}}",
  ]);
  if (r.code !== 0) {
    throw new Error(`docker inspect failed: ${r.stderr || r.stdout}`);
  }
  return JSON.parse(r.stdout);
};

await mkdir(outDir, { recursive: true });

// Host canaries that must NOT be visible or writable from the sandbox.
// sibling-canary.txt sits next to the worktree (task-repo), not inside it.
const canaryDir = resolve(episodeRoot, "runs", "canaries");
await mkdir(canaryDir, { recursive: true });
const siblingCanary = resolve(episodeRoot, "sibling-canary.txt");
const canaries = {
  siblingOfWorktree: siblingCanary,
  hostTmp: "/tmp/sandcastle-canary.txt",
  untrackedInCheckout: join(taskRepo, "secret-untracked-canary.txt"),
};
const canaryToken = "CANARY_TOKEN_NOT_A_SECRET";
await writeFile(canaries.siblingOfWorktree, canaryToken + "\n", "utf8");
await writeFile(canaries.hostTmp, canaryToken + "\n", "utf8");
await writeFile(canaries.untrackedInCheckout, canaryToken + "\n", "utf8");

// Prove from the host that the sibling canary exists, before the sandbox runs.
const hostLs = await sh("ls", ["-l", siblingCanary]);
const hostCat = await sh("cat", [siblingCanary]);
const hostProof = [
  "host proof: sibling-canary.txt sits next to the worktree",
  hostLs.stdout.trim() || hostLs.stderr.trim(),
  "---",
  hostCat.stdout,
].join("\n");
await writeFile(join(outDir, "host-sibling-canary.txt"), hostProof, "utf8");
process.stdout.write(hostProof + "\n");

const started = Date.now();
const sandbox = await createSandbox({
  cwd: taskRepo,
  branch: "probe/enforcement",
  sandbox: docker({ imageName }),
});

let inspect: unknown = null;
let execResult: { exitCode: number; stdout: string; stderr: string } | null = null;
let error: string | null = null;

try {
  if (!sandbox.sandboxId) {
    throw new Error("createSandbox did not return a docker sandboxId");
  }
  inspect = await inspectJson(sandbox.sandboxId);

  // Run in-sandbox probes. The script is copied via stdin.
  const probeBody = await (await import("node:fs/promises")).readFile(
    join(here, "probe-inside.sh"),
    "utf8",
  );
  const gw = process.env.LLM_GATEWAY ?? "";
  const probeScript =
    `export LLM_GATEWAY=${JSON.stringify(gw)}\n` +
    `export HOST_SIBLING_PATH=${JSON.stringify(siblingCanary)}\n` +
    probeBody;
  execResult = await sandbox.exec("bash -s", { stdin: probeScript });
} catch (e) {
  error = e instanceof Error ? e.message : String(e);
} finally {
  await sandbox.close().catch(() => {});
}

const rawInspect = inspect as {
  Config?: { User?: string; Image?: string };
  HostConfig?: {
    Privileged?: boolean;
    CapDrop?: string[] | null;
    CapAdd?: string[] | null;
    NetworkMode?: string;
    CgroupParent?: string;
    Binds?: string[] | null;
    ReadonlyRootfs?: boolean;
    SecurityOpt?: string[] | null;
    PidMode?: string;
    Runtime?: string;
  };
  NetworkSettings?: { Networks?: Record<string, { IPAddress?: string; Gateway?: string; NetworkID?: string }> };
  State?: { Running?: boolean };
  Name?: string;
} | null;

const networks = rawInspect?.NetworkSettings?.Networks ?? {};
const networkNames = Object.keys(networks);
const binds = rawInspect?.HostConfig?.Binds ?? [];

const summary = {
  runId: process.env.RUN_ID ?? `probes-${new Date().toISOString()}`,
  wallMs: Date.now() - started,
  error,
  sandboxIdPresent: Boolean(rawInspect),
  dockerInspect: rawInspect
    ? {
        name: rawInspect.Name,
        image: rawInspect.Config?.Image,
        user: rawInspect.Config?.User,
        privileged: rawInspect.HostConfig?.Privileged ?? null,
        capDrop: rawInspect.HostConfig?.CapDrop ?? null,
        capAdd: rawInspect.HostConfig?.CapAdd ?? null,
        networkMode: rawInspect.HostConfig?.NetworkMode ?? null,
        networkNames,
        cgroupParent: rawInspect.HostConfig?.CgroupParent ?? null,
        binds,
        readonlyRootfs: rawInspect.HostConfig?.ReadonlyRootfs ?? null,
        securityOpt: rawInspect.HostConfig?.SecurityOpt ?? null,
        pidMode: rawInspect.HostConfig?.PidMode ?? null,
      }
    : null,
  documentedExpectations: {
    bindMount: "worktree bind-mounted into the container",
    user: "numeric --user, default host uid:gid",
    network: "no --network flag; Docker default bridge",
    capDrop: "omitted; container keeps Docker default capabilities",
    privileged: "no --privileged in startContainer",
  },
  exec: execResult
    ? {
        exitCode: execResult.exitCode,
        stdout: execResult.stdout,
        stderr: execResult.stderr,
      }
    : null,
  hostCanaries: canaries,
};

const outPath = join(outDir, "probes.json");
await writeFile(outPath, JSON.stringify(summary, null, 2), "utf8");
await writeFile(join(outDir, "probes.stdout.txt"), execResult?.stdout ?? "", "utf8");
await writeFile(join(outDir, "probes.stderr.txt"), execResult?.stderr ?? "", "utf8");
if (inspect) {
  await writeFile(join(outDir, "docker-inspect.raw.json"), JSON.stringify(inspect, null, 2), "utf8");
}

// Cleanup canaries (leave the JSON evidence).
await rm(canaries.untrackedInCheckout, { force: true });
await rm(canaries.hostTmp, { force: true });

console.log(JSON.stringify({ ok: !error && execResult?.exitCode === 0, outPath, wallMs: summary.wallMs, error }, null, 2));
