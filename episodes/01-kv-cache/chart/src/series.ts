/** Growth series the chart draws from one shared baseline context. */

export const GPU_ATTRIBUTIONS = ["ollama-pid", "new-pid", "only-runner", "memory.used"] as const;

const GPU_ATTRIBUTION_SET = new Set<string>(GPU_ATTRIBUTIONS);

export type SeriesRow = {
  num_ctx: number;
  predicted_kv_bytes?: number | null;
  gpu_memory_bytes?: number | null;
  process_rss_bytes?: number | null;
  gpu_attribution?: string | null;
};

export const PREDICTED_LABEL = "predicted KV cache growth";

export type MeasuredChoice = {
  /** Honest legend text. Null when the file has neither an attributed GPU column nor process RSS. */
  label: string | null;
  /** Growth from the shared baseline, aligned with `rows`. Null where that row has no figure. */
  growth: Array<number | null>;
  /** Index of the baseline row. Null when this series has no figure. */
  baselineIndex: number | null;
};

export type ChartSeries = {
  predictedLabel: typeof PREDICTED_LABEL;
  predicted: Array<number | null>;
  measuredLabel: string | null;
  measured: Array<number | null>;
  /** Absolute predicted cache at the longest context, for the formula line. */
  longest: { num_ctx: number; predicted_kv_bytes: number } | null;
};

const isBytes = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);

const gpuBytes = (row: SeriesRow): number | null => {
  const token = (row.gpu_attribution ?? "").trim();
  if (!GPU_ATTRIBUTION_SET.has(token) || !isBytes(row.gpu_memory_bytes)) return null;
  return row.gpu_memory_bytes;
};

const presentValues = (
  rows: SeriesRow[],
  read: (row: SeriesRow) => number | null,
): { index: number; ctx: number; value: number }[] => {
  const present: { index: number; ctx: number; value: number }[] = [];
  rows.forEach((row, index) => {
    const value = read(row);
    if (value != null) present.push({ index, ctx: row.num_ctx, value });
  });
  return present;
};

const growthFrom = (rows: SeriesRow[], read: (row: SeriesRow) => number | null): MeasuredChoice => {
  const present = presentValues(rows, read);
  if (present.length === 0) return { label: null, growth: rows.map(() => null), baselineIndex: null };
  const baseline = [...present].sort((a, b) => a.ctx - b.ctx || a.index - b.index)[0];
  return {
    label: null,
    baselineIndex: baseline.index,
    growth: rows.map((row) => {
      const value = read(row);
      return value == null ? null : value - baseline.value;
    }),
  };
};

const predictedBytes = (row: SeriesRow): number | null =>
  isBytes(row.predicted_kv_bytes) ? row.predicted_kv_bytes : null;

const rssBytes = (row: SeriesRow): number | null => (isBytes(row.process_rss_bytes) ? row.process_rss_bytes : null);

/**
 * Both series use one baseline. That row is the shortest context with an
 * attributed GPU figure, or with process RSS when the GPU column is empty.
 * Predicted growth is the formula at each context minus the formula at that
 * same row. With no measured column, the baseline is the shortest context.
 * `longest` keeps the absolute prediction at the longest context.
 */
export const chartSeries = (rows: SeriesRow[]): ChartSeries => {
  const gpu = growthFrom(rows, gpuBytes);
  const rss = growthFrom(rows, rssBytes);
  const measured = gpu.baselineIndex != null ? gpu : rss;
  const measuredLabel =
    gpu.baselineIndex != null
      ? "measured GPU memory growth"
      : rss.baselineIndex != null
        ? "measured process RSS growth"
        : null;
  const predictedPresent = presentValues(rows, predictedBytes);
  const predictedBaseline =
    measured.baselineIndex != null && predictedBytes(rows[measured.baselineIndex]) != null
      ? measured.baselineIndex
      : predictedPresent.sort((a, b) => a.ctx - b.ctx || a.index - b.index)[0]?.index;
  const baselinePredicted = predictedBaseline == null ? null : predictedBytes(rows[predictedBaseline]);
  const predicted = rows.map((row) => {
    const value = predictedBytes(row);
    return value == null || baselinePredicted == null ? null : value - baselinePredicted;
  });
  const longest = predictedPresent.sort((a, b) => b.ctx - a.ctx || b.index - a.index)[0];
  return {
    predictedLabel: PREDICTED_LABEL,
    predicted,
    measuredLabel,
    measured: measured.growth,
    longest: longest ? { num_ctx: longest.ctx, predicted_kv_bytes: longest.value } : null,
  };
};
