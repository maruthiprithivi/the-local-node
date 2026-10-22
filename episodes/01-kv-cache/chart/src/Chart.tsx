import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { CAPTION_BAND, HEIGHT, theme, WIDTH } from "./theme";

export type MeasurementRow = {
  num_ctx: number;
  predicted_kv_bytes: number;
  measured_runtime_bytes: number | null;
  ttft_ms?: number | null;
  notes?: string;
};

export type ChartProps = {
  model: string;
  source: string;
  rows: MeasurementRow[];
  shape?: {
    layers: number;
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

const formatGib = (bytes: number): string => {
  const gib = bytes / GIB;
  if (Math.abs(gib - Math.round(gib)) < 1e-9) return String(Math.round(gib));
  return gib.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
};

const formatContext = (tokens: number): string => tokens.toLocaleString("en-US");

export const Chart: React.FC<ChartProps> = ({ model, source, rows, shape }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  if (!Array.isArray(rows) || rows.length === 0) {
    throw new Error("The measurements file needs a non-empty rows array.");
  }
  const sorted = [...rows].sort((a, b) => a.num_ctx - b.num_ctx);
  const maxBytes = Math.max(
    1,
    ...sorted.flatMap((row) => [row.predicted_kv_bytes, row.measured_runtime_bytes ?? 0]),
  );
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
  const span = Math.max(16, Math.floor((durationInFrames - 48) / sorted.length));
  const ticks = 4;
  const showGap = sorted.some(
    (row) => row.measured_runtime_bytes != null && row.measured_runtime_bytes > row.predicted_kv_bytes,
  );
  const shapeLine = shape
    ? `${shape.layers} layers, ${shape.kv_heads} KV heads, head dim ${shape.head_dim}, ${shape.bytes_per_value} bytes`
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
            Predicted vs measured
          </div>
          <div style={{ marginTop: 14, fontSize: 22, color: theme.muted }}>{model}</div>
          {shapeLine ? <div style={{ marginTop: 6, fontSize: 20, color: theme.muted }}>{shapeLine}</div> : null}
          {gqaLine ? <div style={{ marginTop: 4, fontSize: 20, color: theme.muted }}>{gqaLine}</div> : null}
        </div>

        <div style={{ position: "absolute", right: 72, top: 44, width: 620, textAlign: "right", opacity: titleOpacity }}>
          {source === "sample" ? (
            <div style={{ fontSize: 20, color: theme.muted }}>sample data, not a measurement</div>
          ) : (
            <div style={{ fontSize: 20, color: theme.muted }}>{source}</div>
          )}
          <div style={{ marginTop: 18, display: "flex", justifyContent: "flex-end", gap: 22, fontSize: 20 }}>
            <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 18, height: 18, background: theme.predicted, display: "inline-block" }} />
              predicted KV cache
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 18, height: 18, background: theme.measured, display: "inline-block" }} />
              measured runtime
            </span>
          </div>
          {showGap ? (
            <div style={{ marginTop: 10, fontSize: 18, color: theme.muted }}>
              measured includes the weights and other overhead
            </div>
          ) : null}
        </div>

        <svg width={WIDTH} height={SAFE_HEIGHT} style={{ position: "absolute", inset: 0, opacity: axisOpacity }}>
          {Array.from({ length: ticks + 1 }, (_, index) => {
            const fraction = index / ticks;
            const y = plot.bottom - plotHeight * fraction;
            const label = formatGib((maxBytes * fraction));
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
          const predictedHeight = (row.predicted_kv_bytes / maxBytes) * plotHeight * grow;
          const measuredHeight =
            row.measured_runtime_bytes == null ? 0 : (row.measured_runtime_bytes / maxBytes) * plotHeight * grow;
          const predictedX = cx - barWidth - 6;
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
              {row.measured_runtime_bytes != null ? (
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
                {row.measured_runtime_bytes != null ? (
                  <>
                    <span style={{ color: theme.muted }}> / </span>
                    <span style={{ color: theme.measured }}>{formatGib(row.measured_runtime_bytes)}</span>
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
