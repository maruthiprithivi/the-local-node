import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { chooseMeasured } from "./series";
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

const GIB = 1024 ** 3;
const SAFE_HEIGHT = HEIGHT - CAPTION_BAND;
const INTRO_FRAMES = 28;
const HOLD_SECONDS = 2;
// Extra frames past the 2s hold so the last label is not still landing on the final frames.
const HOLD_PAD = 12;

const formatGib = (bytes: number): string => {
  const gib = bytes / GIB;
  if (Math.abs(gib - Math.round(gib)) < 1e-9) return String(Math.round(gib));
  return gib.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
};

const formatTick = (gib: number): string => {
  if (Math.abs(gib - Math.round(gib)) < 1e-6) return String(Math.round(gib));
  return gib.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
};

/** Nice GiB steps so the axis reads 0, 5, 10, 20 rather than fractions of the tallest bar. */
export const roundAxis = (maxBytes: number): { topBytes: number; ticks: number[] } => {
  const maxGib = Math.max(maxBytes, 1) / GIB;
  const steps: number[] = [];
  for (const base of [1, 2, 2.5, 5]) {
    for (let exp = -2; exp <= 4; exp++) steps.push(base * 10 ** exp);
  }
  steps.sort((a, b) => a - b);
  let step = steps[steps.length - 1];
  for (const candidate of steps) {
    const intervals = Math.ceil(maxGib / candidate - 1e-9);
    if (intervals >= 3 && intervals <= 6) {
      step = candidate;
      break;
    }
  }
  const intervals = Math.max(1, Math.ceil(maxGib / step - 1e-9));
  const top = intervals * step;
  const ticks = Array.from({ length: intervals + 1 }, (_, index) => index * step);
  return { topBytes: top * GIB, ticks };
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
  const measured = chooseMeasured(sorted);
  const maxBytes = Math.max(
    1,
    ...sorted.flatMap((row, index) => [row.predicted_kv_bytes, Math.max(0, measured.growth[index] ?? 0)]),
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

  const plot = { left: 148, right: 1840, top: 236, bottom: 740 };
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
        <div style={{ position: "absolute", left: 72, top: 36, opacity: titleOpacity }}>
          <div style={{ fontFamily: theme.serif, fontStyle: "italic", fontSize: 64, lineHeight: 1 }}>
            {measured.label ? "Predicted vs measured" : "Predicted KV cache"}
          </div>
          <div style={{ marginTop: 14, fontSize: 22, color: theme.muted }}>{model}</div>
          {shapeLine ? <div style={{ marginTop: 6, fontSize: 20, color: theme.muted }}>{shapeLine}</div> : null}
          {gqaLine ? <div style={{ marginTop: 4, fontSize: 20, color: theme.muted }}>{gqaLine}</div> : null}
        </div>

        <div style={{ position: "absolute", right: 72, top: 48, textAlign: "right", opacity: titleOpacity }}>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 22, fontSize: 20 }}>
            <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 18, height: 18, background: theme.predicted, display: "inline-block" }} />
              predicted KV cache
            </span>
            {measured.label ? (
              <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 18, height: 18, background: theme.measured, display: "inline-block" }} />
                {measured.label}
              </span>
            ) : null}
          </div>
        </div>

        <svg width={WIDTH} height={SAFE_HEIGHT} style={{ position: "absolute", inset: 0, opacity: axisOpacity }}>
          {axis.ticks.map((tick, index) => {
            const fraction = tick / (axis.topBytes / GIB);
            const y = plot.bottom - plotHeight * fraction;
            const label = formatTick(tick);
            return (
              <g key={index}>
                <line x1={plot.left} x2={plot.right} y1={y} y2={y} stroke={theme.grid} strokeWidth={1} />
                <text x={plot.left - 16} y={y + 6} fill={theme.muted} fontSize={18} textAnchor="end" fontFamily={theme.mono}>
                  {label}
                </text>
              </g>
            );
          })}
          <text
            x={28}
            y={(plot.top + plot.bottom) / 2}
            fill={theme.muted}
            fontSize={16}
            textAnchor="middle"
            fontFamily={theme.mono}
            transform={`rotate(-90 28 ${(plot.top + plot.bottom) / 2})`}
          >
            GiB
          </text>
          <line x1={plot.left} x2={plot.right} y1={plot.bottom} y2={plot.bottom} stroke={theme.ink} strokeWidth={1.5} />
          <text x={(plot.left + plot.right) / 2} y={860} fill={theme.muted} fontSize={20} textAnchor="middle" fontFamily={theme.mono}>
            context length (tokens)
          </text>
          <text x={72} y={900} fill={theme.muted} fontSize={20} fontFamily={theme.mono}>
            2 x layers x kv_heads x head_dim x bytes x tokens
          </text>
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
          const growth = measured.growth[index];
          const predictedHeight = (row.predicted_kv_bytes / axis.topBytes) * plotHeight * grow;
          const measuredHeight = growth == null ? 0 : (Math.max(0, growth) / axis.topBytes) * plotHeight * grow;
          const predictedX = measured.label ? cx - barWidth - 6 : cx - barWidth / 2;
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
              {growth != null ? (
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
                  fontSize: 20,
                  color: theme.ink,
                  fontFamily: theme.mono,
                }}
              >
                {formatContext(row.num_ctx)}
              </div>
              <div
                style={{
                  position: "absolute",
                  left: cx - groupWidth / 2,
                  top: plot.bottom + 40,
                  width: groupWidth,
                  textAlign: "center",
                  fontSize: 16,
                  opacity: labelOpacity,
                  fontFamily: theme.mono,
                }}
              >
                <span style={{ color: theme.predicted }}>{formatGib(row.predicted_kv_bytes)}</span>
                {growth != null ? (
                  <>
                    <span style={{ color: theme.muted }}> / </span>
                    <span style={{ color: theme.measured }}>{formatGib(growth)}</span>
                  </>
                ) : null}
              </div>
            </React.Fragment>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
