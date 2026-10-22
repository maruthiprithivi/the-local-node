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

const GB = 1e9;
const MB = 1e6;

/** Decimal GB (bytes / 1e9). Under 0.1 GB, whole MB (bytes / 1e6). Exact 0 stays "0". */
export const formatBarValue = (bytes: number): string => {
  if (bytes === 0) return "0";
  const sign = bytes < 0 ? "-" : "";
  const abs = Math.abs(bytes);
  const gb = abs / GB;
  if (gb < 0.1) {
    const mb = Math.round(abs / MB);
    if (mb === 0) return "0";
    return `${sign}${mb} MB`;
  }
  return `${sign}${(Math.round(gb * 10) / 10).toFixed(1)}`;
};

export const comparisonSubtitle = (baselineTokens: number): string => {
  const count = baselineTokens.toLocaleString("en-US");
  return `Extra memory needed as the conversation gets longer, compared with a ${count}-token chat`;
};

export const formatTotalGb = (bytes: number): string => `${(Math.round(Math.abs(bytes) / GB * 10) / 10).toFixed(1)} GB`;

export const CHART_PLOT = { left: 156, right: 1840, top: 400, bottom: 700 };
export const LABEL_FONT_PX = 28;

export type LabelBox = { x: number; y: number; w: number; h: number };

/** Wide enough to cover the glyphs at this size, so a pass here means the text does not touch. */
export const labelTextWidth = (text: string, fontSize: number): number => {
  let em = 0;
  for (const char of text) {
    if (char === " ") em += 0.33;
    else if (char === "." || char === ",") em += 0.32;
    else if (char === "-") em += 0.4;
    else if (char >= "0" && char <= "9") em += 0.62;
    else em += 0.72;
  }
  return Math.ceil(em * fontSize);
};

export const boxesIntersect = (a: LabelBox, b: LabelBox): boolean =>
  a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;

export const rungBars = (rowCount: number, index: number, hasMeasured: boolean) => {
  const plotWidth = CHART_PLOT.right - CHART_PLOT.left;
  const groupWidth = plotWidth / Math.max(1, rowCount);
  const barWidth = Math.min(52, groupWidth * 0.26);
  const cx = CHART_PLOT.left + groupWidth * index + groupWidth / 2;
  const predictedX = hasMeasured ? cx - barWidth - 6 : cx - barWidth / 2;
  const measuredX = cx + 6;
  return { barWidth, predictedX, measuredX, cx, groupWidth };
};

const boxOnBar = (text: string, barX: number, barWidth: number, top: number, fontSize: number): LabelBox => {
  const w = labelTextWidth(text, fontSize);
  return { x: barX + barWidth / 2 - w / 2, y: top, w, h: fontSize };
};

/**
 * One number sits on top of each bar. When the two boxes in a rung would
 * meet, the measured label moves above the predicted one.
 */
export const placeRungLabels = (opts: {
  predictedText: string | null;
  measuredText: string | null;
  predictedX: number;
  measuredX: number;
  predictedTop: number;
  measuredTop: number;
  barWidth: number;
  fontSize: number;
  minTop: number;
  avoidCollision?: boolean;
}): { predicted: LabelBox | null; measured: LabelBox | null } => {
  const { fontSize } = opts;
  let predicted = opts.predictedText
    ? boxOnBar(opts.predictedText, opts.predictedX, opts.barWidth, opts.predictedTop, fontSize)
    : null;
  let measured = opts.measuredText
    ? boxOnBar(opts.measuredText, opts.measuredX, opts.barWidth, opts.measuredTop, fontSize)
    : null;
  if (opts.avoidCollision === false || !predicted || !measured || !boxesIntersect(predicted, measured)) {
    return { predicted, measured };
  }
  const gap = 6;
  measured = { ...measured, y: predicted.y - fontSize - gap };
  if (measured.y < opts.minTop) {
    const shift = opts.minTop - measured.y;
    measured = { ...measured, y: measured.y + shift };
    predicted = { ...predicted, y: predicted.y + shift };
  }
  return { predicted, measured };
};

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
