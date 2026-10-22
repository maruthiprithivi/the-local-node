import assert from "node:assert/strict";
import test from "node:test";
import {
  CHART_PLOT,
  LABEL_FONT_PX,
  boxesIntersect,
  chartSeries,
  comparisonSubtitle,
  formatBarValue,
  formatTotalGb,
  placeRungLabels,
  rungBars,
} from "./series.ts";

const MIB = 1024 * 1024;

test("predicted and GPU growth share the shortest context", () => {
  const predicted512 = 32 * MIB;
  const predicted32k = 2048 * MIB;
  const series = chartSeries([
    {
      num_ctx: 32768,
      predicted_kv_bytes: predicted32k,
      gpu_memory_bytes: 20176 * MIB,
      gpu_attribution: "new-pid",
      process_rss_bytes: 9 * MIB,
    },
    {
      num_ctx: 512,
      predicted_kv_bytes: predicted512,
      gpu_memory_bytes: 17816 * MIB,
      gpu_attribution: "ollama-pid",
      process_rss_bytes: 1 * MIB,
    },
  ]);
  assert.equal(series.predictedLabel, "predicted (KV cache math)");
  assert.equal(series.measuredLabel, "measured on this machine");
  assert.equal(series.measuredKind, "gpu");
  assert.equal(series.baselineTokens, 512);
  assert.equal(series.baselineIndex, 1);
  assert.equal(series.predicted[1], 0);
  assert.equal(series.measured[1], 0);
  assert.equal(series.predicted[0], 2016 * MIB);
  assert.equal(series.measured[0], 2360 * MIB);
  assert.equal(formatBarValue(series.predicted[1]), "0");
  assert.equal(formatBarValue(series.measured[1]), "0");
  assert.equal(formatBarValue(series.predicted[0]), "2.1");
  assert.equal(formatBarValue(series.measured[0]), "2.5");
  assert.equal(formatTotalGb(series.longest.predicted_kv_bytes), "2.1 GB");
  assert.equal(
    comparisonSubtitle(series.baselineTokens),
    "Extra memory needed as the conversation gets longer, compared with a 512-token chat",
  );
  assert.deepEqual(series.longest, { num_ctx: 32768, predicted_kv_bytes: predicted32k });
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

test("viewer labels use decimal GB and MB, and exact zero stays 0", () => {
  assert.equal(formatBarValue(2.1 * 1e9), "2.1");
  assert.equal(formatBarValue(2.47463936 * 1e9), "2.5");
  assert.equal(formatBarValue(32 * 1e6), "32 MB");
  assert.equal(formatBarValue(0), "0");
  assert.equal(formatBarValue(-32 * 1e6), "-32 MB");
  assert.equal(formatBarValue(2016 * MIB), "2.1");
  assert.equal(formatBarValue(2360 * MIB), "2.5");
  assert.equal(formatTotalGb(2048 * MIB), "2.1 GB");
  assert.equal(formatBarValue(0).includes("+"), false);
  assert.equal(
    comparisonSubtitle(1024),
    "Extra memory needed as the conversation gets longer, compared with a 1,024-token chat",
  );
});

const llamaFixtures = [
  { num_ctx: 512, predicted: 0, measured: 0 },
  { num_ctx: 1024, predicted: 17e6, measured: 18e6 },
  { num_ctx: 2048, predicted: 50e6, measured: 65e6 },
  { num_ctx: 4096, predicted: 200e6, measured: 260e6 },
  { num_ctx: 8192, predicted: 800e6, measured: 1.1e9 },
];

test("llama rung labels do not overlap", () => {
  assert.equal(formatBarValue(17e6), "17 MB");
  assert.equal(formatBarValue(18e6), "18 MB");
  assert.equal(formatBarValue(50e6), "50 MB");
  assert.equal(formatBarValue(65e6), "65 MB");

  const plotHeight = CHART_PLOT.bottom - CHART_PLOT.top;
  const topBytes = 2.5e9;
  const fontSize = LABEL_FONT_PX;
  for (const [index, rung] of llamaFixtures.entries()) {
    const bars = rungBars(llamaFixtures.length, index, true);
    const predictedText = formatBarValue(rung.predicted);
    const measuredText = formatBarValue(rung.measured);
    const predictedHeight = (Math.max(0, rung.predicted) / topBytes) * plotHeight;
    const measuredHeight = (Math.max(0, rung.measured) / topBytes) * plotHeight;
    const tops = {
      predictedTop: Math.max(CHART_PLOT.top - 36, CHART_PLOT.bottom - predictedHeight - 36),
      measuredTop: Math.max(CHART_PLOT.top - 36, CHART_PLOT.bottom - measuredHeight - 36),
    };
    const naive = placeRungLabels({
      predictedText,
      measuredText,
      predictedX: bars.predictedX,
      measuredX: bars.measuredX,
      ...tops,
      barWidth: bars.barWidth,
      fontSize,
      minTop: CHART_PLOT.top - 36,
      avoidCollision: false,
    });
    const placed = placeRungLabels({
      predictedText,
      measuredText,
      predictedX: bars.predictedX,
      measuredX: bars.measuredX,
      ...tops,
      barWidth: bars.barWidth,
      fontSize,
      minTop: CHART_PLOT.top - 36,
    });
    assert.ok(placed.predicted);
    assert.ok(placed.measured);
    assert.equal(boxesIntersect(placed.predicted, placed.measured), false);
    if (rung.num_ctx === 1024 || rung.num_ctx === 2048) {
      assert.equal(boxesIntersect(naive.predicted, naive.measured), true);
      assert.ok(placed.measured.y + placed.measured.h <= placed.predicted.y);
    }
  }
});
