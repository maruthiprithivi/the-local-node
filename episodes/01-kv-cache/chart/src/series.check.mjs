import assert from "node:assert/strict";
import test from "node:test";
import { chooseMeasured } from "./series.ts";

const MIB = 1024 * 1024;

test("attributed GPU memory is plotted as growth from the shortest context", () => {
  const chosen = chooseMeasured([
    {
      num_ctx: 32768,
      gpu_memory_bytes: 20176 * MIB,
      gpu_attribution: "new-pid",
      process_rss_bytes: 9 * MIB,
    },
    {
      num_ctx: 512,
      gpu_memory_bytes: 17816 * MIB,
      gpu_attribution: "ollama-pid",
      process_rss_bytes: 1 * MIB,
    },
  ]);
  assert.equal(chosen.label, "measured GPU memory growth");
  assert.equal(chosen.growth[1], 0);
  assert.equal(chosen.growth[0], 2360 * MIB);
});

test("macOS rows with gpu_attribution unavailable plot process RSS growth", () => {
  const chosen = chooseMeasured([
    { num_ctx: 4096, gpu_memory_bytes: null, gpu_attribution: "unavailable", process_rss_bytes: 1800 },
    { num_ctx: 512, gpu_memory_bytes: null, gpu_attribution: "unavailable", process_rss_bytes: 1000 },
  ]);
  assert.equal(chosen.label, "measured process RSS growth");
  assert.deepEqual(chosen.growth, [800, 0]);
});

test("an unattributed or empty GPU column does not invent a measured series", () => {
  const unattributed = chooseMeasured([
    { num_ctx: 512, gpu_memory_bytes: 17816 * MIB, gpu_attribution: "unattributed" },
    { num_ctx: 1024, gpu_memory_bytes: 20176 * MIB, gpu_attribution: "" },
  ]);
  assert.equal(unattributed.label, null);
  assert.deepEqual(unattributed.growth, [null, null]);

  const sample = chooseMeasured([
    { num_ctx: 1024, gpu_memory_bytes: null, process_rss_bytes: null },
    { num_ctx: 8192 },
  ]);
  assert.equal(sample.label, null);
});

test("a missing shortest rung uses the next context that has a figure", () => {
  const chosen = chooseMeasured([
    { num_ctx: 512, gpu_memory_bytes: null, gpu_attribution: "new-pid" },
    { num_ctx: 1024, gpu_memory_bytes: 100, gpu_attribution: "new-pid" },
    { num_ctx: 2048, gpu_memory_bytes: 140, gpu_attribution: "memory.used" },
  ]);
  assert.deepEqual(chosen.growth, [null, 0, 40]);
});
