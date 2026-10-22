import assert from "node:assert/strict";
import test from "node:test";
import { chartSeries, comparisonSubtitle, formatTotalGb, formatViewerMemory, growthCaption } from "./series.ts";

const MIB = 1024 * 1024;

test("predicted and GPU growth share the shortest context", () => {
  const short = 31.5 * MIB;
  const long = 2016 * MIB;
  const series = chartSeries([
    {
      num_ctx: 32768,
      predicted_kv_bytes: long,
      gpu_memory_bytes: 20176 * MIB,
      gpu_attribution: "new-pid",
      process_rss_bytes: 9 * MIB,
    },
    {
      num_ctx: 512,
      predicted_kv_bytes: short,
      gpu_memory_bytes: 17816 * MIB,
      gpu_attribution: "ollama-pid",
      process_rss_bytes: 1 * MIB,
    },
  ]);
  assert.equal(series.predictedLabel, "predicted (KV cache math)");
  assert.equal(series.measuredLabel, "measured on this machine");
  assert.equal(series.measuredKind, "gpu");
  assert.equal(series.baselineTokens, 512);
  assert.equal(series.predicted[1], 0);
  assert.equal(series.measured[1], 0);
  assert.equal(series.predicted[0], long - short);
  assert.equal(series.measured[0], 2360 * MIB);
  assert.equal(growthCaption(series.predicted[1], "predicted", true), "baseline");
  assert.equal(growthCaption(series.measured[1], "measured", true), "baseline");
  assert.equal(growthCaption(series.predicted[0], "predicted", false), "+1.9 GB predicted");
  assert.equal(growthCaption(series.measured[0], "measured", false), "+2.3 GB measured");
  assert.equal(
    comparisonSubtitle(series.baselineTokens),
    "Extra memory needed as the conversation gets longer, compared with a 512-token chat",
  );
  assert.deepEqual(series.longest, { num_ctx: 32768, predicted_kv_bytes: long });
});

test("macOS rows with gpu_attribution unavailable plot process RSS growth", () => {
  const series = chartSeries([
    {
      num_ctx: 4096,
      predicted_kv_bytes: 400,
      gpu_memory_bytes: null,
      gpu_attribution: "unavailable",
      process_rss_bytes: 1800,
    },
    {
      num_ctx: 512,
      predicted_kv_bytes: 100,
      gpu_memory_bytes: null,
      gpu_attribution: "unavailable",
      process_rss_bytes: 1000,
    },
  ]);
  assert.equal(series.measuredLabel, "measured on this machine");
  assert.equal(series.measuredKind, "rss");
  assert.deepEqual(series.measured, [800, 0]);
  assert.deepEqual(series.predicted, [300, 0]);
});

test("an unattributed or empty GPU column does not invent a measured series", () => {
  const unattributed = chartSeries([
    { num_ctx: 512, predicted_kv_bytes: 10, gpu_memory_bytes: 17816 * MIB, gpu_attribution: "unattributed" },
    { num_ctx: 1024, predicted_kv_bytes: 20, gpu_memory_bytes: 20176 * MIB, gpu_attribution: "" },
  ]);
  assert.equal(unattributed.measuredLabel, null);
  assert.deepEqual(unattributed.measured, [null, null]);
  assert.deepEqual(unattributed.predicted, [0, 10]);

  const sample = chartSeries([
    { num_ctx: 1024, predicted_kv_bytes: 100, gpu_memory_bytes: null, process_rss_bytes: null },
    { num_ctx: 8192, predicted_kv_bytes: 800 },
  ]);
  assert.equal(sample.measuredLabel, null);
  assert.deepEqual(sample.predicted, [0, 700]);
  assert.deepEqual(sample.longest, { num_ctx: 8192, predicted_kv_bytes: 800 });
});

test("a missing shortest rung uses the next context for both series", () => {
  const series = chartSeries([
    { num_ctx: 512, predicted_kv_bytes: 10, gpu_memory_bytes: null, gpu_attribution: "new-pid" },
    { num_ctx: 1024, predicted_kv_bytes: 20, gpu_memory_bytes: 100, gpu_attribution: "new-pid" },
    { num_ctx: 2048, predicted_kv_bytes: 40, gpu_memory_bytes: 140, gpu_attribution: "memory.used" },
  ]);
  assert.deepEqual(series.measured, [null, 0, 40]);
  assert.deepEqual(series.predicted, [-10, 0, 20]);
  assert.deepEqual(series.longest, { num_ctx: 2048, predicted_kv_bytes: 40 });
});

test("viewer labels round to one decimal GB and use MB under 0.1 GB", () => {
  assert.equal(formatViewerMemory(2 * 1024 ** 3), "+2.0 GB");
  assert.equal(formatViewerMemory(2.3046875 * 1024 ** 3), "+2.3 GB");
  assert.equal(formatViewerMemory(32 * MIB), "+32 MB");
  assert.equal(formatViewerMemory(0), "+0.0 GB");
  assert.equal(growthCaption(0, "predicted", true), "baseline");
  assert.equal(growthCaption(-32 * MIB, "measured", false), "-32 MB measured");
  assert.equal(formatTotalGb(16 * 1024 ** 3), "16.0 GB");
  assert.equal(
    comparisonSubtitle(1024),
    "Extra memory needed as the conversation gets longer, compared with a 1,024-token chat",
  );
});
