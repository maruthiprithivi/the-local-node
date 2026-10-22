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

export const PREDICTED_LABEL = "predicted (KV cache math)";
export const MEASURED_LABEL = "measured on this machine";

const GIB = 1024 ** 3;
const MIB = 1024 ** 2;

/** Bytes are GiB. The chart labels that unit GB. Under 0.1 GB, switch to whole MB. */
export const formatViewerMemory = (bytes: number): string => {
  const sign = bytes < 0 ? "-" : "+";
  const abs = Math.abs(bytes);
  if (abs === 0) return "+0.0 GB";
  const gb = abs / GIB;
  if (gb < 0.1) return `${sign}${Math.round(abs / MIB)} MB`;
  return `${sign}${(Math.round(gb * 10) / 10).toFixed(1)} GB`;
};

/** The shortest rung says baseline. Every later rung names the series. */
export const growthCaption = (bytes: number, role: "predicted" | "measured", isBaseline: boolean): string => {
  if (isBaseline) return "baseline";
  const noun = role === "predicted" ? "predicted" : "measured";
  return `${formatViewerMemory(bytes)} ${noun}`;
};

export const comparisonSubtitle = (baselineTokens: number): string => {
  const count = baselineTokens.toLocaleString("en-US");
  return `Extra memory needed as the conversation gets longer, compared with a ${count}-token chat`;
};

export const formatTotalGb = (bytes: number): string => `${(Math.round(Math.abs(bytes) / GIB * 10) / 10).toFixed(1)} GB`;

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
  measuredLabel: typeof MEASURED_LABEL | null;
  /** Which measured column was drawn. The legend text stays the same either way. */
  measuredKind: "gpu" | "rss" | null;
  measured: Array<number | null>;
  /** Context the growth is compared with. */
  baselineTokens: number | null;
  /** Index of that context in `rows`, when the file has a prediction or a measurement. */
  baselineIndex: number | null;
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
  const measuredKind = gpu.baselineIndex != null ? "gpu" : rss.baselineIndex != null ? "rss" : null;
  const measured = measuredKind === "gpu" ? gpu : rss;
  const predictedPresent = presentValues(rows, predictedBytes);
  const predictedBaseline =
    measured.baselineIndex != null && predictedBytes(rows[measured.baselineIndex]) != null
      ? measured.baselineIndex
      : predictedPresent.sort((a, b) => a.ctx - b.ctx || a.index - b.index)[0]?.index;
  const baselineIndex = predictedBaseline ?? measured.baselineIndex ?? null;
  const baselinePredicted = predictedBaseline == null ? null : predictedBytes(rows[predictedBaseline]);
  const predicted = rows.map((row) => {
    const value = predictedBytes(row);
    return value == null || baselinePredicted == null ? null : value - baselinePredicted;
  });
  const longest = predictedPresent.sort((a, b) => b.ctx - a.ctx || b.index - a.index)[0];
  return {
    predictedLabel: PREDICTED_LABEL,
    predicted,
    measuredLabel: measuredKind ? MEASURED_LABEL : null,
    measuredKind,
    measured: measured.growth,
    baselineTokens: baselineIndex == null ? null : rows[baselineIndex].num_ctx,
    baselineIndex,
    longest: longest ? { num_ctx: longest.ctx, predicted_kv_bytes: longest.value } : null,
  };
};
