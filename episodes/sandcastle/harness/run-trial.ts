import { mkdir, writeFile, readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import { run, opencode } from "@ai-hero/sandcastle";
import { docker } from "@ai-hero/sandcastle/sandboxes/docker";

const here = dirname(fileURLToPath(import.meta.url));
const episodeRoot = resolve(here, "..");
const taskRepo = process.env.TASK_REPO ?? resolve(episodeRoot, "task-repo");
const imageName = process.env.SANDCASTLE_IMAGE ?? "sandcastle-opencode:0.14.0-local";
const runIndex = process.env.RUN_INDEX ?? "1";
const runId = process.env.RUN_ID ?? `trial-${runIndex}-${new Date().toISOString().replaceAll(":", "")}`;
const outDir = resolve(episodeRoot, "runs", runId);
const configTemplate = resolve(here, "opencode-home/config");
const promptFile = resolve(here, "prompt.md");
const model = process.env.OPENCODE_MODEL ?? "qwen/qwen3.8-27b-nvfp4";
const baseUrl = process.env.OPENCODE_BASE_URL;
if (!baseUrl) {
  throw new Error("OPENCODE_BASE_URL is not set (this kit does not bake in a host address)");
}
const readonlyConfig = process.env.READONLY_OPENCODE_CONFIG === "1";
const capDrop = (process.env.CAP_DROP ?? "").split(",").map((s) => s.trim()).filter(Boolean);
const maxIterations = Number(process.env.MAX_ITERATIONS ?? 8);
const idleTimeoutSeconds = Number(process.env.IDLE_TIMEOUT ?? 1800);
const completionTimeoutSeconds = Number(process.env.COMPLETION_TIMEOUT ?? 180);

const sh = (cmd: string, args: string[], cwd?: string): Promise<{ code: number; stdout: string; stderr: string }> =>
  new Promise((resolveP, reject) => {
    const child = spawn(cmd, args, { cwd, env: process.env });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d) => (stdout += d.toString()));
    child.stderr.on("data", (d) => (stderr += d.toString()));
    child.on("error", reject);
    child.on("close", (code) => resolveP({ code: code ?? 1, stdout, stderr }));
  });

await mkdir(outDir, { recursive: true });
await mkdir(join(outDir, "sandcastle-logs"), { recursive: true });

const baseline = await sh("npm", ["test"], taskRepo);
await writeFile(join(outDir, "baseline-test.txt"), `code=${baseline.code}\nstdout:\n${baseline.stdout}\nstderr:\n${baseline.stderr}\n`, "utf8");

const started = Date.now();
let error: string | null = null;
let result: unknown = null;

// OpenCode 1.19.5 writes .gitignore into ~/.config/opencode at startup.
// A read-only bind mount of that directory fails the agent (see first three trials).
const configDir = join(outDir, "opencode-config");
await mkdir(configDir, { recursive: true });
const copied = await sh("cp", ["-a", `${configTemplate}/.`, configDir]);
if (copied.code !== 0) {
  throw new Error(`failed to copy opencode config: ${copied.stderr}`);
}
const sevenB = model.startsWith("llama/") || model.includes("qwen2.5-coder-7b");
if (sevenB) {
  const seven = await readFile(join(configDir, "opencode.qwen25-coder-7b.json"), "utf8");
  await writeFile(join(configDir, "opencode.json"), seven, "utf8");
}
const cfgPath = join(configDir, "opencode.json");
const cfg = await readFile(cfgPath, "utf8");
await writeFile(
  cfgPath,
  cfg.replaceAll("OPENCODE_BASE_URL_PLACEHOLDER", baseUrl),
  "utf8",
);

try {
  result = await run({
    cwd: taskRepo,
    agent: opencode(model, { captureSessions: true }),
    sandbox: docker({
      imageName,
      mounts: [
        { hostPath: configDir, sandboxPath: "/home/agent/.config/opencode", readonly: readonlyConfig },
      ],
      ...(capDrop.length ? { capDrop } : {}),
    }),
    promptFile,
    branchStrategy: { type: "branch", branch: `agent/slugify-${runId}` },
    maxIterations,
    idleTimeoutSeconds,
    completionTimeoutSeconds,
    logging: { type: "file", path: join(outDir, "sandcastle-logs", "agent.log") },
    name: runId,
  });
} catch (e) {
  error = e instanceof Error ? `${e.name}: ${e.message}\n${e.stack ?? ""}` : String(e);
}

const wallMs = Date.now() - started;

// Evaluate tests on the agent branch if it exists.
const branch = `agent/slugify-${runId}`;
const show = await sh("git", ["show-ref", "--verify", `refs/heads/${branch}`], taskRepo);
let testAfter: { code: number; stdout: string; stderr: string } | null = null;
let worktree: string | null = null;
if (show.code === 0) {
  worktree = join(outDir, "check-wt");
  const add = await sh("git", ["worktree", "add", "--detach", worktree, branch], taskRepo);
  await writeFile(join(outDir, "worktree-add.txt"), `code=${add.code}\n${add.stdout}\n${add.stderr}`, "utf8");
  if (add.code === 0) {
    testAfter = await sh("npm", ["test"], worktree);
  }
}

const commits =
  result && typeof result === "object" && "commits" in result
    ? (result as { commits: unknown }).commits
    : null;
const stdout =
  result && typeof result === "object" && "stdout" in result
    ? (result as { stdout: string }).stdout
    : "";
const iterations =
  result && typeof result === "object" && "iterations" in result
    ? (result as { iterations: unknown[] }).iterations
    : [];

const passed = Boolean(testAfter && testAfter.code === 0);
const record = {
  runId,
  runIndex,
  model,
  imageName,
  startedAt: new Date(started).toISOString(),
  wallMs,
  error,
  baselineTestExit: baseline.code,
  testAfterExit: testAfter?.code ?? null,
  passed,
  commitCount: Array.isArray(commits) ? commits.length : null,
  commits,
  iterationCount: Array.isArray(iterations) ? iterations.length : null,
  branch,
  resultLogPath: `runs/${runId}/sandcastle-logs/agent.log`,
  readonlyConfig,
  capDrop: capDrop.length ? capDrop : undefined,
};

await writeFile(join(outDir, "result.json"), JSON.stringify(record, null, 2), "utf8");
await writeFile(join(outDir, "agent-stdout.txt"), stdout, "utf8");
if (testAfter) {
  await writeFile(join(outDir, "test-after.txt"), `code=${testAfter.code}\nstdout:\n${testAfter.stdout}\nstderr:\n${testAfter.stderr}\n`, "utf8");
}
// Keep a compact iteration dump without assuming private fields.
try {
  await writeFile(join(outDir, "iterations.json"), JSON.stringify(iterations, null, 2), "utf8");
} catch {
  /* ignore */
}

console.log(JSON.stringify({ runId, passed, wallMs, error, testAfterExit: testAfter?.code ?? null, commitCount: Array.isArray(commits) ? commits.length : null, outDir: `runs/${runId}` }, null, 2));
if (error) process.exitCode = 2;
else if (!passed) process.exitCode = 1;
