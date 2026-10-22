import React from "react";
import { Composition } from "remotion";
import { Chart, ChartProps } from "./Chart";
import sample from "./sample-measurements.json";
import { FPS, HEIGHT, WIDTH } from "./theme";

const DURATION_SECONDS = 12;

export const RemotionRoot: React.FC = () => (
  <Composition
    id="KVCacheChart"
    component={Chart}
    fps={FPS}
    width={WIDTH}
    height={HEIGHT}
    durationInFrames={FPS * DURATION_SECONDS}
    defaultProps={sample as ChartProps}
  />
);
