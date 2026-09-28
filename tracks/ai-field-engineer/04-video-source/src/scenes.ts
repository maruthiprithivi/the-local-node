import narration from './narration.json';
import { estimateSeconds, FPS } from './theme';

export type SceneSpec = {
  visual: string;
  params: Record<string, unknown>;
  text: string;
};

export type VideoSpec = {
  title: string;
  subtitle: string;
  accent: string;
  scenes: SceneSpec[];
};

export const VIDEOS = narration as unknown as Record<string, VideoSpec>;
export const VIDEO_IDS = Object.keys(VIDEOS);

export type SceneTiming = {
  /** seconds of narration audio for this scene, including its tail padding */
  durationSeconds: number;
  /** relative path under public/, e.g. "audio/inference-101/01.wav" */
  audio: string | null;
};

/** Frame length per scene, from measured narration when available, else an estimate. */
export const framesFor = (video: VideoSpec, timings: SceneTiming[] | null): number[] =>
  video.scenes.map((scene, i) => {
    const seconds = timings?.[i]?.durationSeconds ?? estimateSeconds(scene.text);
    return Math.max(FPS, Math.round(seconds * FPS));
  });
