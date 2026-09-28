import React from 'react';
import { Composition, staticFile } from 'remotion';
import { Explainer, ExplainerProps } from './Explainer';
import { framesFor, SceneTiming, VIDEOS, VIDEO_IDS } from './scenes';
import { FPS, HEIGHT, WIDTH } from './theme';

/**
 * Narration timings are written by scripts/tts.py (or scripts/tts.mjs) into
 * public/scenes/<videoId>.json. If they are missing, every composition still
 * works in the Studio using an estimate from the word count.
 */
const loadTimings = async (videoId: string): Promise<SceneTiming[] | null> => {
  try {
    const res = await fetch(staticFile(`scenes/${videoId}.json`));
    if (!res.ok) return null;
    const json = await res.json();
    if (!json || !Array.isArray(json.scenes)) return null;
    return json.scenes.map((s: any) => ({
      durationSeconds: Number(s.durationSeconds),
      audio: typeof s.audio === 'string' ? s.audio : null,
    }));
  } catch {
    return null;
  }
};

export const RemotionRoot: React.FC = () => (
  <>
    {VIDEO_IDS.map((id) => (
      <Composition
        key={id}
        id={id}
        component={Explainer}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        durationInFrames={FPS * 60}
        defaultProps={{ videoId: id, timings: null } as ExplainerProps}
        calculateMetadata={async ({ props }) => {
          const timings = await loadTimings(id);
          const frames = framesFor(VIDEOS[id], timings);
          return {
            durationInFrames: frames.reduce((a, b) => a + b, 0),
            props: { ...props, timings },
          };
        }}
      />
    ))}
  </>
);
