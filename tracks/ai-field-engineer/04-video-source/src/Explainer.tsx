import React from 'react';
import { AbsoluteFill, Sequence, Series, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
// <Audio> comes from @remotion/media (the 'remotion' export is the legacy HTML5 tag).
import { Audio } from '@remotion/media';
import { VISUALS, VisualProps } from './components/Visuals';
import { framesFor, SceneSpec, SceneTiming, VideoSpec, VIDEOS } from './scenes';
import { cuesFor } from './lib/subtitles';
import { accentOf, theme } from './theme';

export type ExplainerProps = {
  videoId: string;
  timings: SceneTiming[] | null;
};

/** Fixed-height band at the bottom. The visual stage never draws into it. */
const SUBTITLE_BAND = 200;

const Subtitles: React.FC<{ text: string; durationInFrames: number; accent: string }> = ({ text, durationInFrames, accent }) => {
  const { fps } = useVideoConfig();
  const cues = React.useMemo(() => cuesFor(text, durationInFrames, fps), [text, durationInFrames, fps]);
  return (
    <div style={{
      height: SUBTITLE_BAND, flexShrink: 0, borderTop: `2px solid ${theme.rule}`,
      background: theme.bg, display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '0 90px', position: 'relative',
    }}>
      {cues.map((c, i) => (
        <Sequence key={i} from={c.from} durationInFrames={c.dur} layout="none">
          <div style={{
            position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: '0 90px', textAlign: 'center',
          }}>
            <span style={{
              fontFamily: theme.body, fontSize: 44, lineHeight: 1.3, color: theme.ink,
              textWrap: 'balance', maxWidth: 1600,
            }}>{c.text}</span>
          </div>
        </Sequence>
      ))}
      <div style={{ position: 'absolute', left: 90, bottom: 14, width: 34, height: 4, background: accent, borderRadius: 2, opacity: 0.6 }} />
    </div>
  );
};

const SceneView: React.FC<{
  scene: SceneSpec; index: number; total: number; durationInFrames: number;
  video: VideoSpec; audio: string | null;
}> = ({ scene, index, total, durationInFrames, video, audio }) => {
  const frame = useCurrentFrame();
  const p = Math.min(1, Math.max(0, frame / Math.max(1, durationInFrames - 1)));
  const accent = accentOf(video.accent);
  const Visual = VISUALS[scene.visual] ?? VISUALS.Bullets;
  const props: VisualProps = { p, params: scene.params ?? {}, accent };

  return (
    <AbsoluteFill style={{ backgroundColor: theme.bg, display: 'flex', flexDirection: 'column' }}>
      {audio ? <Audio src={staticFile(audio)} /> : null}

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 24, padding: '48px 72px 24px', minHeight: 0, overflow: 'hidden' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <div style={{ fontFamily: theme.mono, fontSize: 24, letterSpacing: 2, textTransform: 'uppercase', color: accent }}>{video.title}</div>
          <div style={{ fontFamily: theme.mono, fontSize: 24, color: theme.muted }}>
            {String(index + 1).padStart(2, '0')} / {String(total).padStart(2, '0')}
          </div>
        </div>
        <Visual {...props} />
      </div>

      <Subtitles text={scene.text} durationInFrames={durationInFrames} accent={accent} />

      <div style={{ height: 6, background: theme.panel2 }}>
        <div style={{ height: 6, width: `${((index + p) / total) * 100}%`, background: accent }} />
      </div>
    </AbsoluteFill>
  );
};

export const Explainer: React.FC<ExplainerProps> = ({ videoId, timings }) => {
  const video = VIDEOS[videoId];
  const frames = framesFor(video, timings);

  return (
    <AbsoluteFill style={{ backgroundColor: theme.bg }}>
      <Series>
        {video.scenes.map((scene, i) => (
          <Series.Sequence key={i} durationInFrames={frames[i]} name={`${i + 1}. ${scene.visual}`}>
            <SceneView
              scene={scene} index={i} total={video.scenes.length}
              durationInFrames={frames[i]} video={video}
              audio={timings?.[i]?.audio ?? null}
            />
          </Series.Sequence>
        ))}
      </Series>
    </AbsoluteFill>
  );
};
