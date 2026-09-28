export const FPS = 24;
export const WIDTH = 1920;
export const HEIGHT = 1080;

export const theme = {
  bg: '#0C1014',
  panel: '#151A20',
  panel2: '#1D242C',
  rule: '#2A333D',
  ink: '#ECEFEA',
  muted: '#9BA5B0',
  teal: '#3CC4AE',
  tealDim: '#123630',
  copper: '#EC935B',
  copperDim: '#3A2517',
  violet: '#9D90FF',
  good: '#59CE86',
  bad: '#F0705E',
  warn: '#E6AD3E',
  display: '"Bricolage Grotesque", "Inter", system-ui, sans-serif',
  body: '"IBM Plex Sans", system-ui, sans-serif',
  mono: '"IBM Plex Mono", ui-monospace, monospace',
};

export const accentOf = (name: string) => (name === 'copper' ? theme.copper : theme.teal);

/** Words per second used to estimate scene length before narration exists. */
export const WORDS_PER_SECOND = 2.6;
export const TAIL_PAD_SECONDS = 0.45;

export const estimateSeconds = (text: string) => {
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  return Math.max(2.5, words / WORDS_PER_SECOND + TAIL_PAD_SECONDS);
};
