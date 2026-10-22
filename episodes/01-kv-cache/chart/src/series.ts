/** Which memory series the chart draws beside the predicted KV cache. */

export const GPU_ATTRIBUTIONS = ["ollama-pid", "new-pid", "only-runner", "memory.used"] as const;

const GPU_ATTRIBUTION_SET = new Set<string>(GPU_ATTRIBUTIONS);

export type SeriesRow = {
  num_ctx: number;
  gpu_memory_bytes?: number | null;
  process_rss_bytes?: number | null;
  gpu_attribution?: string | null;
};

export type MeasuredChoice = {
  /** Honest legend text. Null when the file has neither an attributed GPU column nor process RSS. */
  label: string | null;
  /** Growth from the shortest context that has a number, aligned with `rows`. Null where that row has no figure. */
  growth: Array<number | null>;
};

const isBytes = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);

const gpuBytes = (row: SeriesRow): number | null => {
  const token = (row.gpu_attribution ?? "").trim();
  if (!GPU_ATTRIBUTION_SET.has(token) || !isBytes(row.gpu_memory_bytes)) return null;
  return row.gpu_memory_bytes;
};

const growthFrom = (rows: SeriesRow[], read: (row: SeriesRow) => number | null): Array<number | null> => {
  const present: { index: number; ctx: number; value: number }[] = [];
  rows.forEach((row, index) => {
    const value = read(row);
    if (value != null) present.push({ index, ctx: row.num_ctx, value });
  });
  if (present.length === 0) return rows.map(() => null);
  const baseline = [...present].sort((a, b) => a.ctx - b.ctx || a.index - b.index)[0];
  return rows.map((row) => {
    const value = read(row);
    return value == null ? null : value - baseline.value;
  });
};

/**
 * GB10 rows carry an attributed GPU total (weights plus the cache). Plot the
 * growth from the shortest context so it sits on the same scale as the
 * predicted cache. macOS rows say `unavailable` and have no GPU figure; plot
 * process RSS growth instead. Ollama's reported size stays in the file.
 */
export const chooseMeasured = (rows: SeriesRow[]): MeasuredChoice => {
  if (rows.some((row) => gpuBytes(row) != null)) {
    return { label: "measured GPU memory growth", growth: growthFrom(rows, gpuBytes) };
  }
  if (rows.some((row) => isBytes(row.process_rss_bytes))) {
    return {
      label: "measured process RSS growth",
      growth: growthFrom(rows, (row) => (isBytes(row.process_rss_bytes) ? row.process_rss_bytes : null)),
    };
  }
  return { label: null, growth: rows.map(() => null) };
};
