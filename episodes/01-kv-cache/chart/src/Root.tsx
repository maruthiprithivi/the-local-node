import React from "react";
import { Composition } from "remotion";
import { Chart, ChartProps, chartDuration } from "./Chart";
import sample from "./sample-measurements.json";
import { FPS, HEIGHT, WIDTH } from "./theme";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="KVCacheChart"
    component={Chart}
    fps={FPS}
    width={WIDTH}
    height={HEIGHT}
    durationInFrames={chartDuration(sample.rows.length, FPS)}
    defaultProps={sample as ChartProps}
    calculateMetadata={({ props }) => {
      const rows = Array.isArray(props.rows) ? props.rows.length : 1;
      return { durationInFrames: chartDuration(rows, FPS) };
    }}
  />
);
