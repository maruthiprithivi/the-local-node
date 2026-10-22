import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { chartSeries, comparisonSubtitle, formatBarValue, formatTotalGb } from "./series";
import { CAPTION_BAND, FPS, HEIGHT, theme, WIDTH } from "./theme";

export type MeasurementRow = {
  num_ctx: number;
  predicted_kv_bytes: number;
  measured_runtime_bytes?: number | null;
  gpu_memory_bytes?: number | null;
  process_rss_bytes?: number | null;
  gpu_attribution?: string | null;
  ttft_ms?: number | null;
  notes?: string;
};

export type ChartProps = {
  model: string;
  source: string;
  rows: MeasurementRow[];
  shape?: {
    layers: number;
    kv_layers?: number;
    blocks?: number;
    attention_heads: number;
    kv_heads: number;
    head_dim: number;
    bytes_per_value: number;
  };
  os?: string;
  notes?: string[];
  kv_cache_type?: string;
};

const GB = 1e9;
const SAFE_HEIGHT = HEIGHT - CAPTION_BAND;
const INTRO_FRAMES = 28;
const HOLD_SECONDS = 2;
// Extra frames past the 2s hold so the last label is not still landing on the final frames.
const HOLD_PAD = 12;

const LABEL_FONT = 28;
const CAPTION_FONT = 'ui-sans-serif, system-ui, "Segoe UI", sans-serif';

const formatTick = (gib: number): string => {
  if (Math.abs(gib - Math.round(gib)) < 1e-6) return String(Math.round(gib));
  return gib.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
};

/** Nice decimal-GB steps so the axis reads 0, 0.5, 1, 2 rather than fractions of the tallest bar. */
export const roundAxis = (maxBytes: number): { topBytes: number; ticks: number[] } => {
  const maxGb = Math.max(maxBytes, 1) / GB;
  const steps: number[] = [];
  for (const base of [1, 2, 2.5, 5]) {
    for (let exp = -2; exp <= 4; exp++) steps.push(base * 10 ** exp);
  }
  steps.sort((a, b) => a - b);
  let step = steps[steps.length - 1];
  for (const candidate of steps) {
    const intervals = Math.ceil(maxGb / candidate - 1e-9);
    if (intervals >= 3 && intervals <= 6) {
      step = candidate;
      break;
    }
  }
  const intervals = Math.max(1, Math.ceil(maxGb / step - 1e-9));
  const top = intervals * step;
  const ticks = Array.from({ length: intervals + 1 }, (_, index) => index * step);
  return { topBytes: top * GB, ticks };
};

/** Last bar and its label reach full size at least HOLD_SECONDS before the final frame. */
export const barSpan = (rowCount: number, durationInFrames: number, fps: number): number => {
  const rows = Math.max(1, rowCount);
  const hold = Math.round(fps * HOLD_SECONDS);
  const grow = 0.7;
  const denom = rows - 1 + grow;
  const room = durationInFrames - 1 - hold - HOLD_PAD - INTRO_FRAMES;
  return Math.max(8, Math.floor(room / denom));
};

export const chartDuration = (rowCount: number, fps: number = FPS): number => {
  const rows = Math.max(1, rowCount);
  const span = 32;
  const finish = INTRO_FRAMES + (rows - 1 + 0.7) * span;
  return Math.max(fps * 12, Math.ceil(finish + fps * HOLD_SECONDS + HOLD_PAD));
};

const formatContext = (tokens: number): string => tokens.toLocaleString("en-US");

export const Chart: React.FC<ChartProps> = ({ model, rows, shape }) => {
  const frame = useCurrentFrame();
  const { durationInFrames, fps } = useVideoConfig();
  if (!Array.isArray(rows) || rows.length === 0) {
    throw new Error("The measurements file needs a non-empty rows array.");
  }
  const sorted = [...rows].sort((a, b) => a.num_ctx - b.num_ctx);
  const series = chartSeries(sorted);
  const maxBytes = Math.max(
    1,
    ...series.predicted.map((value) => Math.max(0, value ?? 0)),
    ...series.measured.map((value) => Math.max(0, value ?? 0)),
  );
  const axis = roundAxis(maxBytes);
  const axisOpacity = interpolate(frame, [0, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const titleOpacity = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const plot = { left: 156, right: 1840, top: 400, bottom: 700 };
  const plotWidth = plot.right - plot.left;
  const plotHeight = plot.bottom - plot.top;
  const groupWidth = plotWidth / sorted.length;
  const barWidth = Math.min(52, groupWidth * 0.26);
  const span = barSpan(sorted.length, durationInFrames, fps);
  const kvLayers = shape ? (shape.kv_layers ?? shape.layers) : 0;
  const shapeLine = shape
    ? `${
        shape.blocks && shape.blocks !== kvLayers ? `${shape.blocks} blocks, ${kvLayers} KV layers` : `${kvLayers} layers`
      }, ${shape.kv_heads} KV heads, head dim ${shape.head_dim}, ${shape.bytes_per_value} bytes`
    : "";
  const gqaLine =
    shape && shape.attention_heads !== shape.kv_heads
      ? `${shape.attention_heads} attention heads share ${shape.kv_heads} KV heads`
      : "";

  return (
    <AbsoluteFill style={{ backgroundColor: theme.bg, fontFamily: theme.mono, color: theme.ink }}>
      <div style={{ height: SAFE_HEIGHT, overflow: "hidden", position: "relative" }}>
        <div style={{ position: "absolute", left: 72, top: 28, right: 640, opacity: titleOpacity }}>
          <div style={{ fontFamily: theme.serif, fontStyle: "italic", fontSize: 52, lineHeight: 1 }}>
            {series.measuredLabel ? "Predicted vs measured" : "Predicted KV cache growth"}
          </div>
        </div>
        {series.baselineTokens != null ? (
          <div
            style={{
              position: "absolute",
              left: 72,
              right: 72,
              top: 108,
              fontSize: LABEL_FONT,
              lineHeight: 1.2,
              color: theme.ink,
              fontFamily: CAPTION_FONT,
              opacity: titleOpacity,
            }}
          >
            {comparisonSubtitle(series.baselineTokens)}
          </div>
        ) : null}
        <div style={{ position: "absolute", left: 72, top: 152, opacity: titleOpacity }}>
          <div style={{ fontSize: LABEL_FONT, color: theme.muted }}>{model}</div>
          {shapeLine ? <div style={{ marginTop: 6, fontSize: LABEL_FONT, color: theme.muted }}>{shapeLine}</div> : null}
          {gqaLine ? <div style={{ marginTop: 4, fontSize: LABEL_FONT, color: theme.muted }}>{gqaLine}</div> : null}
        </div>

        <div
          style={{
            position: "absolute",
            right: 72,
            top: 32,
            display: "flex",
            flexDirection: "column",
            alignItems: "flex-end",
            gap: 10,
            fontSize: LABEL_FONT,
            opacity: titleOpacity,
          }}
        >
          <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 18, height: 18, background: theme.predicted, display: "inline-block" }} />
            {series.predictedLabel}
          </span>
          {series.measuredLabel ? (
            <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 18, height: 18, background: theme.measured, display: "inline-block" }} />
              {series.measuredLabel}
            </span>
          ) : null}
        </div>

        <div
          style={{
            position: "absolute",
            left: plot.left,
            top: plot.top - 78,
            fontSize: LABEL_FONT,
            lineHeight: 1,
            color: theme.muted,
            fontFamily: theme.mono,
            opacity: axisOpacity,
          }}
        >
          extra memory used (GB)
        </div>

        <svg width={WIDTH} height={SAFE_HEIGHT} style={{ position: "absolute", inset: 0, opacity: axisOpacity }}>
          {axis.ticks.map((tick, index) => {
            const fraction = tick / (axis.topBytes / GB);
            const y = plot.bottom - plotHeight * fraction;
            const label = formatTick(tick);
            return (
              <g key={index}>
                <line x1={plot.left} x2={plot.right} y1={y} y2={y} stroke={theme.grid} strokeWidth={1} />
                <text x={plot.left - 18} y={y + 9} fill={theme.muted} fontSize={LABEL_FONT} textAnchor="end" fontFamily={theme.mono}>
                  {label}
                </text>
              </g>
            );
          })}
          <line x1={plot.left} x2={plot.right} y1={plot.bottom} y2={plot.bottom} stroke={theme.ink} strokeWidth={1.5} />
          <text x={(plot.left + plot.right) / 2} y={820} fill={theme.muted} fontSize={LABEL_FONT} textAnchor="middle" fontFamily={theme.mono}>
            context length (tokens)
          </text>
          <text x={72} y={880} fill={theme.muted} fontSize={LABEL_FONT} fontFamily={theme.mono}>
            2 x layers x kv_heads x head_dim x bytes x tokens
          </text>
          {series.longest ? (
            <text x={plot.right} y={880} fill={theme.muted} fontSize={LABEL_FONT} textAnchor="end" fontFamily={theme.mono}>
              {formatTotalGb(series.longest.predicted_kv_bytes)} predicted at {formatContext(series.longest.num_ctx)} tokens
            </text>
          ) : null}
        </svg>

        {sorted.map((row, index) => {
          const start = 28 + index * span;
          const grow = interpolate(frame, [start, start + span * 0.7], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.out(Easing.cubic),
          });
          const labelOpacity = interpolate(frame, [start + span * 0.45, start + span * 0.7], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const cx = plot.left + groupWidth * index + groupWidth / 2;
          const predictedGrowth = series.predicted[index];
          const measuredGrowth = series.measured[index];
          const onBaseline = index === series.baselineIndex;
          const predictedText = predictedGrowth == null ? null : formatBarValue(predictedGrowth);
          const measuredText = measuredGrowth == null ? null : formatBarValue(measuredGrowth);
          const predictedHeight =
            predictedGrowth == null ? 0 : (Math.max(0, predictedGrowth) / axis.topBytes) * plotHeight * grow;
          const measuredHeight =
            measuredGrowth == null ? 0 : (Math.max(0, measuredGrowth) / axis.topBytes) * plotHeight * grow;
          const predictedX = series.measuredLabel ? cx - barWidth - 6 : cx - barWidth / 2;
          const measuredX = cx + 6;
          return (
            <React.Fragment key={row.num_ctx}>
              <div
                style={{
                  position: "absolute",
                  left: predictedX,
                  top: plot.bottom - predictedHeight,
                  width: barWidth,
                  height: predictedHeight,
                  background: theme.predicted,
                }}
              />
              {measuredGrowth != null ? (
                <div
                  style={{
                    position: "absolute",
                    left: measuredX,
                    top: plot.bottom - measuredHeight,
                    width: barWidth,
                    height: measuredHeight,
                    background: theme.measured,
                  }}
                />
              ) : null}
              <div
                style={{
                  position: "absolute",
                  left: cx - groupWidth / 2,
                  top: plot.bottom + 14,
                  width: groupWidth,
                  textAlign: "center",
                  fontSize: LABEL_FONT,
                  color: theme.ink,
                  fontFamily: theme.mono,
                }}
              >
                {formatContext(row.num_ctx)}
              </div>
              {predictedText != null ? (
                <div
                  style={{
                    position: "absolute",
                    left: predictedX - 24,
                    top: Math.max(plot.top - 36, plot.bottom - predictedHeight - 36),
                    width: barWidth + 48,
                    textAlign: "center",
                    fontSize: LABEL_FONT,
                    lineHeight: 1,
                    color: theme.predicted,
                    fontFamily: CAPTION_FONT,
                    opacity: labelOpacity,
                    whiteSpace: "nowrap",
                  }}
                >
                  {predictedText}
                </div>
              ) : null}
              {measuredText != null ? (
                <div
                  style={{
                    position: "absolute",
                    left: measuredX - 24,
                    top: Math.max(plot.top - 36, plot.bottom - measuredHeight - 36),
                    width: barWidth + 48,
                    textAlign: "center",
                    fontSize: LABEL_FONT,
                    lineHeight: 1,
                    color: theme.measured,
                    fontFamily: CAPTION_FONT,
                    opacity: labelOpacity,
                    whiteSpace: "nowrap",
                  }}
                >
                  {measuredText}
                </div>
              ) : null}
              {onBaseline ? (
                <div
                  style={{
                    position: "absolute",
                    left: cx - groupWidth / 2,
                    top: plot.bottom + 52,
                    width: groupWidth,
                    textAlign: "center",
                    fontSize: LABEL_FONT,
                    color: theme.ink,
                    fontFamily: CAPTION_FONT,
                  }}
                >
                  baseline
                </div>
              ) : null}
            </React.Fragment>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
