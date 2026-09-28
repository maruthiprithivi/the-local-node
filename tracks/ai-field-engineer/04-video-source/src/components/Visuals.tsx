import React from 'react';
import { interpolate } from 'remotion';
import { theme } from '../theme';

/** Every visual receives scene progress p (0 → 1), its params, and the video accent colour. */
export type VisualProps = {
  p: number;
  params: Record<string, any>;
  accent: string;
};

const ramp = (p: number, a: number, b: number) =>
  interpolate(p, [a, b], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

const stage: React.CSSProperties = {
  flex: 1,
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'center',
  gap: 28,
};

const card = (extra?: React.CSSProperties): React.CSSProperties => ({
  background: theme.panel,
  border: `2px solid ${theme.rule}`,
  borderRadius: 18,
  padding: '22px 26px',
  ...extra,
});

const label: React.CSSProperties = {
  fontFamily: theme.mono,
  fontSize: 20,
  letterSpacing: 2,
  textTransform: 'uppercase',
  color: theme.muted,
};

const big: React.CSSProperties = {
  fontFamily: theme.display,
  fontWeight: 700,
  fontSize: 54,
  color: theme.ink,
  lineHeight: 1.05,
};

const Bar: React.FC<{ w: number; color: string; h?: number; text?: string }> = ({ w, color, h = 44, text }) => (
  <div style={{ height: h, width: `${Math.max(0, Math.min(100, w))}%`, background: color, borderRadius: 8, display: 'flex', alignItems: 'center', paddingLeft: 14, color: theme.bg, fontFamily: theme.mono, fontSize: 22, fontWeight: 600, overflow: 'hidden', whiteSpace: 'nowrap' }}>
    {text}
  </div>
);

const Chip: React.FC<{ children: React.ReactNode; color?: string; dim?: boolean }> = ({ children, color = theme.teal, dim }) => (
  <span style={{ fontFamily: theme.mono, fontSize: 24, padding: '8px 16px', borderRadius: 999, border: `2px solid ${color}`, color: dim ? theme.muted : color, opacity: dim ? 0.45 : 1 }}>{children}</span>
);

/* ─────────────────────────── generic scenes ─────────────────────────── */

export const Title: React.FC<VisualProps> = ({ p, params, accent }) => (
  <div style={{ ...stage, justifyContent: 'center', gap: 16 }}>
    <div style={{ ...label, color: accent, opacity: ramp(p, 0, 0.12) }}>{params.kicker}</div>
    <div style={{ fontFamily: theme.display, fontWeight: 800, fontSize: 108, lineHeight: 1, color: theme.ink, letterSpacing: -3, opacity: ramp(p, 0.05, 0.25), transform: `translateY(${(1 - ramp(p, 0.05, 0.3)) * 18}px)` }}>
      {params.headline}
    </div>
    <div style={{ fontFamily: theme.body, fontSize: 38, color: theme.muted, opacity: ramp(p, 0.2, 0.4) }}>{params.sub}</div>
    {params.learn ? (
      <div style={{ ...card({ borderColor: accent, opacity: ramp(p, 0.35, 0.6), maxWidth: 1250 }) }}>
        <div style={{ ...label, color: accent, fontSize: 18 }}>In this video</div>
        <div style={{ fontFamily: theme.body, fontSize: 34, color: theme.ink, marginTop: 6 }}>{params.learn}</div>
      </div>
    ) : null}
    <div style={{ height: 6, width: `${ramp(p, 0.25, 0.95) * 60}%`, background: accent, borderRadius: 3, marginTop: 8 }} />
  </div>
);

export const Outro: React.FC<VisualProps> = ({ p, params, accent }) => (
  <div style={{ ...stage, justifyContent: 'center', alignItems: 'flex-start', gap: 22 }}>
    <div style={{ ...label, color: accent }}>Up next</div>
    <div style={{ ...big, fontSize: 64, opacity: ramp(p, 0, 0.3) }}>{params.line}</div>
    <div style={{ height: 6, width: `${ramp(p, 0.1, 1) * 100}%`, background: accent, borderRadius: 3 }} />
  </div>
);

export const Bullets: React.FC<VisualProps> = ({ p, params, accent }) => {
  const items: string[] = params.items ?? [];
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <div style={{ ...label, color: accent }}>{params.heading}</div>
      {items.map((it, i) => {
        const a = ramp(p, 0.08 + i * 0.22, 0.28 + i * 0.22);
        return (
          <div key={i} style={{ ...card({ opacity: 0.25 + 0.75 * a, transform: `translateX(${(1 - a) * 24}px)`, borderColor: a > 0.8 ? accent : theme.rule }) , display: 'flex', gap: 20, alignItems: 'center' }}>
            <div style={{ fontFamily: theme.mono, fontSize: 26, color: accent, minWidth: 34 }}>{String(i + 1).padStart(2, '0')}</div>
            <div style={{ fontFamily: theme.body, fontSize: 36, color: theme.ink, lineHeight: 1.25 }}>{it}</div>
          </div>
        );
      })}
    </div>
  );
};

/* ─────────────────────────── inference 101 ─────────────────────────── */

export const PrefillDecode: React.FC<VisualProps> = ({ p, params, accent }) => {
  const decode = params.phase === 'decode';
  const promptLit = decode ? 1 : ramp(p, 0.15, 0.45);
  const outCount = decode ? Math.floor(ramp(p, 0.15, 0.95) * 18) : 0;
  return (
    <div style={{ ...stage }}>
      <div style={label}>Prompt tokens · read all at once</div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {Array.from({ length: 28 }).map((_, i) => (
          <div key={i} style={{ width: 44, height: 44, borderRadius: 8, background: promptLit > i / 28 ? theme.copper : theme.panel2, border: `2px solid ${promptLit > i / 28 ? theme.copper : theme.rule}` }} />
        ))}
      </div>
      <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
        <Chip color={decode ? theme.muted : theme.copper} dim={decode}>PREFILL · parallel · compute-bound</Chip>
        <div style={{ fontFamily: theme.mono, fontSize: 24, color: theme.muted }}>→ first token = TTFT</div>
      </div>
      <div style={{ ...label, marginTop: 10 }}>Output tokens · one at a time</div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', minHeight: 52 }}>
        {Array.from({ length: 18 }).map((_, i) => (
          <div key={i} style={{ width: 44, height: 44, borderRadius: 8, background: i < outCount ? accent : 'transparent', border: `2px solid ${i < outCount ? accent : theme.rule}` }} />
        ))}
      </div>
      <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
        <Chip color={decode ? theme.teal : theme.muted} dim={!decode}>DECODE · sequential · memory-bound</Chip>
        <div style={{ fontFamily: theme.mono, fontSize: 24, color: theme.muted }}>gap between tokens = ITL</div>
      </div>
    </div>
  );
};

export const Metrics: React.FC<VisualProps> = ({ p, accent }) => {
  const rows = [
    ['TTFT', 'time to first token', 'prefill + queue'],
    ['ITL / TPOT', 'time between tokens', 'decode speed'],
    ['Throughput', 'tokens/sec, all users', 'batching'],
    ['Goodput', 'throughput within the SLA', 'what you actually sell'],
  ];
  return (
    <div style={{ ...stage }}>
      {rows.map((r, i) => {
        const a = ramp(p, i * 0.18, 0.2 + i * 0.18);
        return (
          <div key={i} style={{ ...card({ opacity: 0.3 + 0.7 * a, borderColor: a > 0.9 ? accent : theme.rule }), display: 'grid', gridTemplateColumns: '300px 1fr 360px', alignItems: 'center', gap: 20 }}>
            <div style={{ fontFamily: theme.mono, fontSize: 34, color: accent }}>{r[0]}</div>
            <div style={{ fontFamily: theme.body, fontSize: 34, color: theme.ink }}>{r[1]}</div>
            <div style={{ fontFamily: theme.body, fontSize: 28, color: theme.muted }}>{r[2]}</div>
          </div>
        );
      })}
    </div>
  );
};

/* ─────────────────────────── KV cache ─────────────────────────── */

export const KvGrow: React.FC<VisualProps> = ({ p, accent }) => {
  const n = Math.floor(ramp(p, 0.1, 0.9) * 14) + 1;
  return (
    <div style={{ ...stage }}>
      <div style={label}>Each new token reads every earlier token's keys and values</div>
      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end', height: 320 }}>
        {Array.from({ length: 15 }).map((_, i) => {
          const on = i < n;
          return (
            <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6, justifyContent: 'flex-end' }}>
              <div style={{ height: on ? 120 : 0, background: theme.copper, borderRadius: 6, transition: 'none' }} />
              <div style={{ height: on ? 120 : 0, background: theme.copperDim, border: on ? `2px solid ${theme.copper}` : 'none', borderRadius: 6 }} />
              <div style={{ fontFamily: theme.mono, fontSize: 18, color: i === n - 1 ? accent : theme.muted, textAlign: 'center' }}>{i + 1}</div>
            </div>
          );
        })}
      </div>
      <div style={{ display: 'flex', gap: 24 }}>
        <Chip color={theme.copper}>K — keys, cached</Chip>
        <Chip color={theme.copper}>V — values, cached</Chip>
        <Chip color={accent}>current token asks the question</Chip>
      </div>
    </div>
  );
};

export const KvMath: React.FC<VisualProps> = ({ p, accent }) => {
  const lines = [
    'KV per token = 2 × layers × KV heads × head dim × bytes',
    'Llama 3 70B   = 2 × 80 × 8 × 128 × 2  =  0.33 MB / token',
    '8K context    = 2.6 GB per request',
    '128K context  = 43 GB per request',
  ];
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      {lines.map((l, i) => (
        <div key={i} style={{ fontFamily: theme.mono, fontSize: i === 0 ? 40 : 44, color: i === 0 ? theme.muted : i === 3 ? theme.bad : theme.ink, opacity: ramp(p, i * 0.2, 0.15 + i * 0.2), whiteSpace: 'pre' }}>
          {l}
        </div>
      ))}
      <div style={{ ...card({ borderColor: accent, marginTop: 16, opacity: ramp(p, 0.75, 0.95) }) }}>
        <div style={{ fontFamily: theme.body, fontSize: 34, color: theme.ink }}>One long-context agent can need more memory than the model itself.</div>
      </div>
    </div>
  );
};

export const KvBlocks: React.FC<VisualProps> = ({ p, params, accent }) => {
  const paged = params.mode === 'paged';
  const cols = 16;
  const rows = 6;
  const total = cols * rows;
  const fill = ramp(p, 0.1, 0.9);
  const cells = Array.from({ length: total }).map((_, i) => {
    if (paged) {
      const used = i < Math.floor(fill * total * 0.92);
      const req = Math.floor(i / 7) % 5;
      return used ? ['used', req] : ['free', 0];
    }
    const block = Math.floor(i / 16);
    const withinBlock = i % 16;
    const reserved = block < Math.ceil(fill * rows);
    const usedLen = [6, 3, 9, 4, 7, 5][block % 6];
    if (!reserved) return ['free', 0];
    return withinBlock < usedLen ? ['used', block] : ['waste', block];
  });
  const wasted = cells.filter((c) => c[0] === 'waste').length;
  const used = cells.filter((c) => c[0] === 'used').length;
  const colors = [theme.teal, theme.copper, theme.violet, theme.good, theme.warn];
  return (
    <div style={{ ...stage }}>
      <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
        <Chip color={paged ? theme.good : theme.bad}>{paged ? 'PagedAttention · blocks on demand' : 'Naive · reserve max length'}</Chip>
        <div style={{ fontFamily: theme.mono, fontSize: 26, color: theme.muted }}>
          used {used} · wasted {wasted} of {total} blocks
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 6 }}>
        {cells.map((c, i) => (
          <div key={i} style={{
            aspectRatio: '1',
            borderRadius: 6,
            background: c[0] === 'used' ? colors[(c[1] as number) % colors.length] : c[0] === 'waste' ? 'repeating-linear-gradient(45deg,#2A333D 0 4px,#F0705E44 4px 8px)' : theme.panel2,
            border: `1px solid ${theme.rule}`,
          }} />
        ))}
      </div>
      <div style={{ fontFamily: theme.body, fontSize: 32, color: theme.muted }}>
        {paged ? 'Non-contiguous blocks + a block table → 2–4× more concurrent requests.' : 'Every request holds room it will probably never use.'}
      </div>
    </div>
  );
};

export const KvQuant: React.FC<VisualProps> = ({ p, accent }) => {
  const a = ramp(p, 0.2, 0.8);
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <div style={label}>KV cache in FP16 vs FP8 · same GPU</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <div style={{ fontFamily: theme.mono, fontSize: 28, color: theme.muted, width: 150 }}>FP16 KV</div>
          <Bar w={80} color={theme.copper} text="16 concurrent requests" />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <div style={{ fontFamily: theme.mono, fontSize: 28, color: theme.muted, width: 150 }}>FP8 KV</div>
          <Bar w={80} color={theme.teal} text={`${Math.round(16 + a * 16)} concurrent requests`} />
        </div>
      </div>
      <div style={{ ...card({ borderColor: theme.teal, opacity: ramp(p, 0.55, 0.85) }) }}>
        <div style={{ fontFamily: theme.body, fontSize: 34, color: theme.ink }}>Halving the cache doubles concurrency — often cheaper than halving the weights.</div>
      </div>
    </div>
  );
};

/* ─────────────────────────── hardware ─────────────────────────── */

export const BandwidthPipe: React.FC<VisualProps> = ({ p, accent }) => {
  const dots = 26;
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
        <div style={{ ...card({ width: 320, borderColor: theme.copper }) }}>
          <div style={{ ...label, color: theme.copper }}>HBM memory</div>
          <div style={{ ...big, fontSize: 44, marginTop: 8 }}>70 GB</div>
          <div style={{ fontFamily: theme.body, fontSize: 26, color: theme.muted }}>every weight, every token</div>
        </div>
        <div style={{ flex: 1, position: 'relative', height: 90 }}>
          <div style={{ position: 'absolute', top: 34, left: 0, right: 0, height: 22, background: theme.panel2, borderRadius: 11, border: `2px solid ${theme.rule}` }} />
          {Array.from({ length: dots }).map((_, i) => {
            const t = (p * 2.2 + i / dots) % 1;
            return <div key={i} style={{ position: 'absolute', top: 40, left: `${t * 100}%`, width: 12, height: 12, borderRadius: 6, background: theme.copper }} />;
          })}
          <div style={{ position: 'absolute', top: 0, width: '100%', textAlign: 'center', fontFamily: theme.mono, fontSize: 24, color: theme.muted }}>3.35 TB/s — the bottleneck</div>
        </div>
        <div style={{ ...card({ width: 320, borderColor: accent }) }}>
          <div style={{ ...label, color: accent }}>Compute</div>
          <div style={{ ...big, fontSize: 44, marginTop: 8 }}>989 TF</div>
          <div style={{ fontFamily: theme.body, fontSize: 26, color: theme.muted }}>mostly idle at batch 1</div>
        </div>
      </div>
      <div style={{ ...card({ marginTop: 26, borderColor: theme.rule }) }}>
        <div style={{ fontFamily: theme.mono, fontSize: 34, color: theme.ink }}>~2 FLOPs per byte moved · the GPU can do ~300</div>
      </div>
    </div>
  );
};

export const Ceiling: React.FC<VisualProps> = ({ p, accent }) => {
  const lines = [
    ['tokens/sec  ≤  memory bandwidth ÷ bytes read per token', theme.ink],
    ['H100 · 70B FP8   =  3350 ÷ 70   ≈  48 tok/s', theme.teal],
    ['H200 · 70B FP8   =  4800 ÷ 70   ≈  69 tok/s', theme.teal],
    ['DGX Spark · 70B FP8 = 273 ÷ 70  ≈  3.9 tok/s', theme.bad],
  ];
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      {lines.map((l, i) => (
        <div key={i} style={{ fontFamily: theme.mono, fontSize: i === 0 ? 46 : 40, color: l[1] as string, opacity: ramp(p, i * 0.2, 0.15 + i * 0.2), whiteSpace: 'pre' }}>{l[0]}</div>
      ))}
      <div style={{ ...card({ borderColor: accent, opacity: ramp(p, 0.8, 0.95), marginTop: 12 }) }}>
        <div style={{ fontFamily: theme.body, fontSize: 32, color: theme.ink }}>Same model. The only thing that changed is the memory pipe.</div>
      </div>
    </div>
  );
};

export const DeviceTable: React.FC<VisualProps> = ({ p, accent }) => {
  const rows = [
    ['RTX 4090', '24 GB', '1.0 TB/s'],
    ['A100 80GB', '80 GB', '2.0 TB/s'],
    ['H100 SXM', '80 GB', '3.35 TB/s'],
    ['H200', '141 GB', '4.8 TB/s'],
    ['B200', '192 GB', '8.0 TB/s'],
    ['DGX Spark (GB10)', '128 GB unified', '273 GB/s'],
  ];
  return (
    <div style={{ ...stage, justifyContent: 'center', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px 320px', ...label, paddingLeft: 26 }}>
        <div>Device</div><div>Memory</div><div>Bandwidth</div>
      </div>
      {rows.map((r, i) => {
        const a = ramp(p, 0.05 + i * 0.12, 0.2 + i * 0.12);
        const spark = i === rows.length - 1;
        return (
          <div key={i} style={{ ...card({ padding: '14px 26px', opacity: 0.25 + 0.75 * a, borderColor: spark && a > 0.8 ? theme.copper : theme.rule }), display: 'grid', gridTemplateColumns: '1fr 300px 320px', alignItems: 'center' }}>
            <div style={{ fontFamily: theme.body, fontSize: 34, color: theme.ink }}>{r[0]}</div>
            <div style={{ fontFamily: theme.mono, fontSize: 30, color: theme.muted }}>{r[1]}</div>
            <div style={{ fontFamily: theme.mono, fontSize: 30, color: spark ? theme.copper : accent }}>{r[2]}</div>
          </div>
        );
      })}
    </div>
  );
};

export const Roofline: React.FC<VisualProps> = ({ p, accent }) => {
  const W = 1300, H = 420, L = 90, B = 70;
  const ridgeX = L + (W - L - 40) * 0.62;
  const x = L + (W - L - 40) * Math.min(0.95, 0.06 + ramp(p, 0.1, 0.9) * 0.85);
  const roofY = 60;
  const y = x < ridgeX ? H - B - ((x - L) / (ridgeX - L)) * (H - B - roofY) : roofY;
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ maxHeight: 460 }}>
        <rect x={L} y={roofY} width={ridgeX - L} height={H - B - roofY} fill={theme.copperDim} opacity={0.5} />
        <rect x={ridgeX} y={roofY} width={W - 40 - ridgeX} height={H - B - roofY} fill={theme.tealDim} opacity={0.5} />
        <path d={`M${L},${H - B} L${ridgeX},${roofY} L${W - 40},${roofY}`} fill="none" stroke={theme.ink} strokeWidth={4} />
        <line x1={L} y1={H - B} x2={W - 40} y2={H - B} stroke={theme.rule} strokeWidth={2} />
        <line x1={L} y1={roofY} x2={L} y2={H - B} stroke={theme.rule} strokeWidth={2} />
        <circle cx={x} cy={y} r={14} fill={x < ridgeX ? theme.copper : theme.teal} stroke={theme.bg} strokeWidth={4} />
        <text x={L + 16} y={roofY + 40} fill={theme.copper} fontSize={26} fontFamily={theme.mono}>MEMORY-BOUND</text>
        <text x={W - 56} y={roofY + 40} fill={theme.teal} fontSize={26} fontFamily={theme.mono} textAnchor="end">COMPUTE-BOUND</text>
        <text x={W / 2} y={H - 18} fill={theme.muted} fontSize={26} fontFamily={theme.mono} textAnchor="middle">batch size / arithmetic intensity →</text>
      </svg>
      <div style={{ fontFamily: theme.body, fontSize: 34, color: theme.ink, textAlign: 'center' }}>
        Batch 1 sits far left. Batching walks the dot right, into the compute you already paid for.
      </div>
    </div>
  );
};

export const Precision: React.FC<VisualProps> = ({ p, params, accent }) => {
  const mode = params.mode as string;
  const spec: Record<string, { bits: [string, number, string][]; gb: number; note: string }> = {
    fp16: { bits: [['sign', 1, theme.muted], ['exponent', 5, theme.copper], ['mantissa', 10, theme.teal]], gb: 140, note: 'baseline quality · 2 bytes per weight' },
    fp8: { bits: [['sign', 1, theme.muted], ['exponent', 4, theme.copper], ['mantissa', 3, theme.teal]], gb: 70, note: 'hardware tensor cores on H100+ · ~2× math' },
    int4: { bits: [['4-bit integer + shared scale', 4, theme.violet]], gb: 35, note: 'AWQ · GPTQ · GGUF · NVFP4 · 16 levels per group' },
  };
  const s = spec[mode];
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <div style={{ ...label, color: accent }}>{mode.toUpperCase()} · one weight</div>
      <div style={{ display: 'flex', gap: 22, alignItems: 'flex-end' }}>
        {s.bits.map((b, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6 }}>
              {Array.from({ length: b[1] }).map((_, j) => (
                <div key={j} style={{ width: 54, height: 72, borderRadius: 8, background: b[2], opacity: ramp(p, 0.05 + j * 0.02, 0.2 + j * 0.02) }} />
              ))}
            </div>
            <div style={{ fontFamily: theme.mono, fontSize: 22, color: theme.muted }}>{b[0]} · {b[1]}</div>
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginTop: 20 }}>
        <div style={{ fontFamily: theme.mono, fontSize: 28, color: theme.muted, width: 250 }}>70B weights</div>
        <Bar w={(s.gb / 160) * 100} color={accent} text={`${s.gb} GB`} />
      </div>
      <div style={{ fontFamily: theme.body, fontSize: 32, color: theme.ink }}>{s.note}</div>
    </div>
  );
};

/* ─────────────────────────── batching ─────────────────────────── */

export const BatchGantt: React.FC<VisualProps> = ({ p, params, accent }) => {
  const cont = params.mode === 'continuous';
  const lens = [6, 2, 9, 3, 4, 8, 2, 5, 7, 3, 6, 4];
  const slots = 4;
  const bars: { slot: number; s: number; e: number; id: number }[] = [];
  if (cont) {
    const free = [0, 0, 0, 0];
    lens.forEach((l, id) => {
      let k = 0;
      for (let i = 1; i < slots; i++) if (free[i] < free[k]) k = i;
      bars.push({ slot: k, s: free[k], e: free[k] + l, id });
      free[k] += l;
    });
  } else {
    let start = 0;
    for (let b = 0; b < lens.length; b += slots) {
      const grp = lens.slice(b, b + slots);
      grp.forEach((l, i) => bars.push({ slot: i, s: start, e: start + l, id: b + i }));
      start += Math.max(...grp);
    }
  }
  const T = 24;
  const head = ramp(p, 0.08, 0.95) * T;
  const busy = lens.reduce((a, b) => a + b, 0);
  const end = Math.max(...bars.map((b) => b.e));
  const colors = [theme.teal, theme.copper, theme.violet, theme.good, theme.warn, theme.bad];
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <div style={{ display: 'flex', gap: 18, alignItems: 'center' }}>
        <Chip color={cont ? theme.good : theme.bad}>{cont ? 'Continuous batching' : 'Static batching'}</Chip>
        <div style={{ fontFamily: theme.mono, fontSize: 26, color: theme.muted }}>done at step {end} · GPU busy {Math.round((busy / (end * slots)) * 100)}%</div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {Array.from({ length: slots }).map((_, s) => (
          <div key={s} style={{ position: 'relative', height: 56, background: theme.panel2, borderRadius: 8 }}>
            {bars.filter((b) => b.slot === s && b.s < head).map((b) => (
              <div key={b.id} style={{
                position: 'absolute', left: `${(b.s / T) * 100}%`,
                width: `${((Math.min(b.e, head) - b.s) / T) * 100}%`,
                top: 4, bottom: 4, borderRadius: 6, background: colors[b.id % colors.length],
                display: 'flex', alignItems: 'center', paddingLeft: 10, color: theme.bg, fontFamily: theme.mono, fontSize: 22, overflow: 'hidden',
              }}>R{b.id + 1}</div>
            ))}
          </div>
        ))}
      </div>
      <div style={{ fontFamily: theme.body, fontSize: 32, color: theme.muted }}>
        {cont ? 'A finished request frees its slot immediately — the queue keeps moving.' : 'Everyone waits for the longest request in the group.'}
      </div>
    </div>
  );
};

export const ChunkedPrefill: React.FC<VisualProps> = ({ p, accent }) => {
  const n = 14;
  const lit = Math.floor(ramp(p, 0.1, 0.9) * n);
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <div style={label}>One 100K-token prompt, interleaved with everyone else's decode</div>
      <div style={{ display: 'flex', gap: 8 }}>
        {Array.from({ length: n }).map((_, i) => (
          <div key={i} style={{ flex: 1, height: 90, borderRadius: 8, background: i <= lit ? (i % 3 === 2 ? theme.teal : theme.copper) : theme.panel2, border: `2px solid ${theme.rule}` }} />
        ))}
      </div>
      <div style={{ display: 'flex', gap: 24 }}>
        <Chip color={theme.copper}>chunk of the long prefill</Chip>
        <Chip color={theme.teal}>decode step for other users</Chip>
      </div>
      <div style={{ fontFamily: theme.body, fontSize: 32, color: theme.ink }}>Slightly slower TTFT for the big prompt, far smoother streaming for everyone else.</div>
    </div>
  );
};

export const SpecDecode: React.FC<VisualProps> = ({ p, accent }) => {
  const draft = ['the', 'KV', 'cache', 'stores'];
  const accepted = Math.min(4, Math.floor(ramp(p, 0.2, 0.75) * 5));
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <div style={label}>Draft model proposes 4 · big model verifies in ONE pass</div>
      <div style={{ display: 'flex', gap: 14 }}>
        {draft.map((w, i) => {
          const state = i < accepted ? (i === 3 ? 'rej' : 'acc') : 'pending';
          const c = state === 'acc' ? theme.good : state === 'rej' ? theme.bad : theme.muted;
          return (
            <div key={i} style={{ padding: '18px 26px', borderRadius: 12, border: `3px ${state === 'pending' ? 'dashed' : 'solid'} ${c}`, color: c, fontFamily: theme.mono, fontSize: 38, textDecoration: state === 'rej' ? 'line-through' : 'none' }}>{w}</div>
          );
        })}
        {accepted >= 4 && (
          <div style={{ padding: '18px 26px', borderRadius: 12, border: `3px solid ${theme.copper}`, color: theme.copper, fontFamily: theme.mono, fontSize: 38 }}>keys</div>
        )}
      </div>
      <div style={{ ...card({ borderColor: accent, marginTop: 20 }) }}>
        <div style={{ fontFamily: theme.mono, fontSize: 34, color: theme.ink }}>tokens per big-model pass = (1 − α^(k+1)) / (1 − α)</div>
        <div style={{ fontFamily: theme.body, fontSize: 30, color: theme.muted, marginTop: 8 }}>α = 0.75, k = 4 → about 3 tokens per pass, same quality</div>
      </div>
    </div>
  );
};

/* ─────────────────────────── training ─────────────────────────── */

export const TrainingPipeline: React.FC<VisualProps> = ({ p, params, accent }) => {
  const stageIdx = params.stage as number;
  const stages = [
    ['Pretrain', 'trillions of tokens', 'the model creator'],
    ['SFT', 'prompt → ideal answer', 'teach format & domain'],
    ['DPO', 'preferred vs rejected', 'teach taste'],
    ['RFT / RL', 'prompt + grader', 'teach correctness'],
  ];
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <div style={{ display: 'flex', gap: 18, alignItems: 'stretch' }}>
        {stages.map((s, i) => {
          const on = i === stageIdx;
          const a = on ? ramp(p, 0, 0.3) : 1;
          return (
            <div key={i} style={{ ...card({ flex: 1, borderColor: on ? accent : theme.rule, opacity: on ? 1 : 0.42, transform: `translateY(${on ? -8 * a : 0}px)` }) }}>
              <div style={{ fontFamily: theme.mono, fontSize: 22, color: on ? accent : theme.muted }}>STEP {i + 1}</div>
              <div style={{ ...big, fontSize: 44, marginTop: 6 }}>{s[0]}</div>
              <div style={{ fontFamily: theme.mono, fontSize: 24, color: theme.muted, marginTop: 10 }}>{s[1]}</div>
              <div style={{ fontFamily: theme.body, fontSize: 28, color: theme.ink, marginTop: 8 }}>{s[2]}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export const LoRA: React.FC<VisualProps> = ({ p, accent }) => {
  const a = ramp(p, 0.15, 0.7);
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <div style={{ display: 'flex', gap: 30, alignItems: 'center' }}>
        <div style={{ ...card({ flex: 1, borderColor: theme.rule }) }}>
          <div style={label}>Frozen base weights</div>
          <div style={{ ...big, fontSize: 60, marginTop: 10 }}>70,000,000,000</div>
          <div style={{ fontFamily: theme.body, fontSize: 28, color: theme.muted }}>untouched, shared by everyone</div>
        </div>
        <div style={{ fontFamily: theme.mono, fontSize: 60, color: accent }}>+</div>
        <div style={{ ...card({ width: 460, borderColor: accent, opacity: 0.3 + 0.7 * a }) }}>
          <div style={{ ...label, color: accent }}>LoRA adapter</div>
          <div style={{ ...big, fontSize: 60, marginTop: 10 }}>~30 MB</div>
          <div style={{ fontFamily: theme.body, fontSize: 28, color: theme.muted }}>two small matrices, trained</div>
        </div>
      </div>
      <div style={{ ...card({ marginTop: 24, borderColor: theme.rule }) }}>
        <div style={{ fontFamily: theme.body, fontSize: 34, color: theme.ink }}>One deployment can serve hundreds of adapters — a fine-tune per customer, at base-model cost.</div>
      </div>
    </div>
  );
};

export const TrainDecide: React.FC<VisualProps> = ({ p, accent }) => {
  const rows = [
    ['Can you write the ideal answer?', 'SFT (usually LoRA)', theme.teal],
    ['Can you only say which of two is better?', 'DPO / preference tuning', theme.violet],
    ['Can a program score the answer 0–1?', 'RFT / reinforcement fine-tuning', theme.copper],
    ['Not sure yet?', 'Better prompt + retrieval first — it is free', theme.muted],
  ];
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      {rows.map((r, i) => {
        const a = ramp(p, i * 0.2, 0.15 + i * 0.2);
        return (
          <div key={i} style={{ ...card({ opacity: 0.25 + 0.75 * a, borderColor: a > 0.85 ? (r[2] as string) : theme.rule }), display: 'grid', gridTemplateColumns: '1fr 40px 1fr', alignItems: 'center', gap: 16 }}>
            <div style={{ fontFamily: theme.body, fontSize: 34, color: theme.ink }}>{r[0]}</div>
            <div style={{ fontFamily: theme.mono, fontSize: 30, color: r[2] as string }}>→</div>
            <div style={{ fontFamily: theme.mono, fontSize: 30, color: r[2] as string }}>{r[1]}</div>
          </div>
        );
      })}
    </div>
  );
};

/* ─────────────────────────── fitting big models ─────────────────────────── */

export const MemoryStack: React.FC<VisualProps> = ({ p, accent }) => {
  const a = ramp(p, 0.12, 0.85);
  const w = 55 * a, kv = 28 * a, ov = 9 * a;
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <div style={label}>GPU memory budget</div>
      <div style={{ display: 'flex', height: 90, borderRadius: 12, overflow: 'hidden', background: theme.panel2, border: `2px solid ${theme.rule}` }}>
        <div style={{ width: `${w}%`, background: theme.teal, display: 'flex', alignItems: 'center', paddingLeft: 18, fontFamily: theme.mono, fontSize: 26, color: theme.bg }}>weights</div>
        <div style={{ width: `${kv}%`, background: theme.copper, display: 'flex', alignItems: 'center', paddingLeft: 18, fontFamily: theme.mono, fontSize: 26, color: theme.bg }}>KV cache</div>
        <div style={{ width: `${ov}%`, background: theme.muted }} />
      </div>
      <div style={{ fontFamily: theme.mono, fontSize: 38, color: theme.ink, marginTop: 16 }}>total = weights + KV + ~10%</div>
      <div style={{ fontFamily: theme.mono, fontSize: 30, color: theme.muted }}>weights = params × bytes · KV = per-token × context × concurrency</div>
    </div>
  );
};

export const Offload: React.FC<VisualProps> = ({ p, accent }) => {
  const rows = [
    ['1. Quantize further', 'FP8 → 4-bit. Free speed, measurable quality cost.', theme.teal],
    ['2. Add GPUs', 'Tensor or pipeline parallel. Needs fast links.', theme.teal],
    ['3. Cut context / concurrency', 'The KV cache is usually the real problem.', theme.warn],
    ['4. Offload to CPU or disk', 'Last resort: 10–50× narrower pipe, decode crawls.', theme.bad],
  ];
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      {rows.map((r, i) => {
        const a = ramp(p, i * 0.18, 0.15 + i * 0.18);
        return (
          <div key={i} style={{ ...card({ opacity: 0.25 + 0.75 * a, borderColor: a > 0.85 ? (r[2] as string) : theme.rule }) }}>
            <div style={{ fontFamily: theme.display, fontWeight: 700, fontSize: 38, color: r[2] as string }}>{r[0]}</div>
            <div style={{ fontFamily: theme.body, fontSize: 30, color: theme.ink, marginTop: 4 }}>{r[1]}</div>
          </div>
        );
      })}
    </div>
  );
};

export const MoEActive: React.FC<VisualProps> = ({ p, accent }) => {
  const cycle = Math.floor(p * 4);
  const picks = [[1, 5], [0, 6], [3, 4], [2, 7]][cycle % 4];
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <div style={label}>120B total parameters · ~5B active per token</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: 14 }}>
        {Array.from({ length: 8 }).map((_, i) => {
          const on = picks.includes(i);
          return (
            <div key={i} style={{ height: 150, borderRadius: 12, border: `3px solid ${on ? accent : theme.rule}`, background: on ? theme.tealDim : theme.panel, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: theme.mono, fontSize: 30, color: on ? accent : theme.muted }}>
              E{i + 1}
            </div>
          );
        })}
      </div>
      <div style={{ display: 'flex', gap: 26, marginTop: 16 }}>
        <div style={{ fontFamily: theme.mono, fontSize: 30, color: theme.copper }}>memory: pay for all of it</div>
        <div style={{ fontFamily: theme.mono, fontSize: 30, color: accent }}>speed: pay only for the active part</div>
      </div>
    </div>
  );
};

export const Parallelism: React.FC<VisualProps> = ({ p, accent }) => {
  const tensor = p < 0.5;
  const t = tensor ? ramp(p, 0.05, 0.45) : ramp(p, 0.55, 0.95);
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <Chip color={tensor ? theme.teal : theme.copper}>{tensor ? 'Tensor parallel · slice every layer' : 'Pipeline parallel · a block of layers each'}</Chip>
      <div style={{ display: 'flex', gap: 24 }}>
        {Array.from({ length: 4 }).map((_, g) => (
          <div key={g} style={{ flex: 1, height: 300, border: `3px solid ${theme.rule}`, borderRadius: 14, padding: 12, display: 'flex', flexDirection: 'column-reverse', gap: 6, background: theme.panel }}>
            {Array.from({ length: 6 }).map((_, l) => {
              const show = tensor ? true : Math.floor(l / 1.5) === g;
              const hue = [theme.teal, theme.copper, theme.violet, theme.good][l % 4];
              return (
                <div key={l} style={{
                  height: 38,
                  width: tensor ? '26%' : '100%',
                  alignSelf: tensor ? 'center' : 'stretch',
                  borderRadius: 6,
                  background: show ? hue : 'transparent',
                  opacity: show ? 0.85 : 0,
                }} />
              );
            })}
          </div>
        ))}
      </div>
      <div style={{ fontFamily: theme.body, fontSize: 32, color: theme.ink }}>
        {tensor ? 'All GPUs work on the same token, then sync after every layer — NVLink territory.' : 'Each GPU owns a stage; requests flow through like an assembly line.'}
      </div>
      <div style={{ height: 5, background: theme.rule, borderRadius: 3 }}><div style={{ height: 5, width: `${t * 100}%`, background: accent, borderRadius: 3 }} /></div>
    </div>
  );
};

/* ─────────────────────────── platform ─────────────────────────── */

export const PlatformMap: React.FC<VisualProps> = ({ p, params, accent }) => {
  const hl = params.highlight as number;
  const layers = [
    ['Your application', 'prompts, RAG, agents'],
    ['Model + fine-tunes', 'which model, LoRA, evals'],
    ['Serving engine', 'kernels, batching, KV cache'],
    ['Autoscaling & routing', 'workers, regions, failover'],
    ['GPUs & data centre', 'hardware, network, power'],
  ];
  return (
    <div style={{ ...stage, justifyContent: 'center', gap: 12 }}>
      {layers.map((l, i) => {
        const managed = hl === 1 && i >= 1;
        const a = ramp(p, 0.05 + i * 0.1, 0.25 + i * 0.1);
        return (
          <div key={i} style={{ ...card({ padding: '16px 26px', opacity: 0.3 + 0.7 * a, borderColor: managed ? accent : theme.rule, background: managed ? theme.tealDim : theme.panel }), display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontFamily: theme.display, fontWeight: 700, fontSize: 38, color: theme.ink }}>{l[0]}</div>
              <div style={{ fontFamily: theme.body, fontSize: 26, color: theme.muted }}>{l[1]}</div>
            </div>
            <div style={{ fontFamily: theme.mono, fontSize: 24, color: managed ? accent : theme.muted }}>{hl === 1 ? (i === 0 ? 'you' : 'managed platform') : 'someone runs this'}</div>
          </div>
        );
      })}
    </div>
  );
};

export const Modes: React.FC<VisualProps> = ({ p, accent }) => {
  const modes = [
    ['Serverless', 'per token', 'bursty, unpredictable traffic'],
    ['Dedicated', 'per GPU-hour', 'steady volume, strict latency'],
    ['Batch', 'discounted', 'offline jobs and evaluations'],
    ['Reserved', 'committed', 'known scale, best unit price'],
  ];
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
        {modes.map((m, i) => {
          const a = ramp(p, i * 0.18, 0.18 + i * 0.18);
          return (
            <div key={i} style={{ ...card({ opacity: 0.3 + 0.7 * a, borderColor: a > 0.85 ? accent : theme.rule }) }}>
              <div style={{ ...big, fontSize: 46 }}>{m[0]}</div>
              <div style={{ fontFamily: theme.mono, fontSize: 26, color: accent, marginTop: 6 }}>{m[1]}</div>
              <div style={{ fontFamily: theme.body, fontSize: 28, color: theme.muted, marginTop: 6 }}>{m[2]}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export const Maturity: React.FC<VisualProps> = ({ p, accent }) => {
  const steps = ['Rent a closed model', 'Engineer prompt & context', 'Migrate to open models', 'Train on your own data'];
  const upto = Math.floor(ramp(p, 0.08, 0.92) * steps.length);
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <div style={{ display: 'flex', gap: 14, alignItems: 'stretch' }}>
        {steps.map((s, i) => (
          <React.Fragment key={i}>
            <div style={{ ...card({ flex: 1, borderColor: i <= upto ? accent : theme.rule, opacity: i <= upto ? 1 : 0.35 }) }}>
              <div style={{ fontFamily: theme.mono, fontSize: 24, color: accent }}>STAGE {i + 1}</div>
              <div style={{ fontFamily: theme.display, fontWeight: 700, fontSize: 38, color: theme.ink, marginTop: 8, lineHeight: 1.1 }}>{s}</div>
            </div>
            {i < steps.length - 1 && <div style={{ alignSelf: 'center', fontFamily: theme.mono, fontSize: 40, color: theme.muted }}>→</div>}
          </React.Fragment>
        ))}
      </div>
      <div style={{ fontFamily: theme.body, fontSize: 34, color: theme.ink, marginTop: 20 }}>
        Cost falls and control rises as you move right — but only if quality is proven at every step.
      </div>
    </div>
  );
};

/* ─────────────────────────── lab-topic visuals ─────────────────────────── */

export const Recap: React.FC<VisualProps> = ({ p, params, accent }) => {
  const items: string[] = params.items ?? [];
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <div style={{ ...label, color: accent }}>{params.heading ?? 'Recap'}</div>
      {items.map((it, i) => {
        const a = ramp(p, 0.05 + i * 0.2, 0.25 + i * 0.2);
        return (
          <div key={i} style={{ ...card({ opacity: 0.25 + 0.75 * a, borderColor: a > 0.8 ? accent : theme.rule, transform: `translateY(${(1 - a) * 12}px)` }), display: 'flex', gap: 22, alignItems: 'center' }}>
            <div style={{ width: 46, height: 46, borderRadius: 23, border: `3px solid ${accent}`, color: accent, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: theme.mono, fontSize: 24, flexShrink: 0 }}>{i + 1}</div>
            <div style={{ fontFamily: theme.body, fontSize: 38, color: theme.ink, lineHeight: 1.22 }}>{it}</div>
          </div>
        );
      })}
    </div>
  );
};

export const EndCard: React.FC<VisualProps> = ({ p, params, accent }) => (
  <div style={{ ...stage, justifyContent: 'center', alignItems: 'center', gap: 26, textAlign: 'center' }}>
    <div style={{ ...label, color: accent }}>Run it next</div>
    <div style={{ fontFamily: theme.display, fontWeight: 750, fontSize: 68, color: theme.ink, lineHeight: 1.1, maxWidth: 1400, opacity: ramp(p, 0, 0.3) }}>{params.line}</div>
    <div style={{ height: 6, width: `${ramp(p, 0.1, 1) * 50}%`, background: accent, borderRadius: 3 }} />
    <div style={{ fontFamily: theme.mono, fontSize: 24, color: theme.muted, marginTop: 10 }}>Field Engineer Lab Book</div>
  </div>
);

export const CommandCard: React.FC<VisualProps> = ({ p, params, accent }) => {
  const lines: string[] = params.lines ?? [];
  const shown = Math.ceil(ramp(p, 0.05, 0.75) * lines.length);
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <div style={{ ...label, color: accent }}>{params.heading}</div>
      <div style={{ background: '#0A0E12', border: `2px solid ${theme.rule}`, borderRadius: 16, padding: '26px 30px', minHeight: 330 }}>
        {lines.map((l, i) => (
          <div key={i} style={{
            fontFamily: theme.mono, fontSize: 30, lineHeight: 1.5, whiteSpace: 'pre',
            color: l.trim().startsWith('#') ? theme.muted : theme.ink,
            opacity: i < shown ? 1 : 0.12,
          }}>{l || ' '}</div>
        ))}
      </div>
    </div>
  );
};

export const ServingStack: React.FC<VisualProps> = ({ p, params, accent }) => {
  const hl = params.highlight ?? -1;
  const boxes = [
    ['API layer', 'OpenAI-compatible HTTP, streaming'],
    ['Scheduler', 'continuous batching, admission, preemption'],
    ['KV cache manager', 'PagedAttention blocks, prefix reuse'],
    ['Model executor', 'kernels, tensor parallel, CUDA graphs'],
  ];
  return (
    <div style={{ ...stage, justifyContent: 'center', gap: 14 }}>
      {boxes.map((b, i) => {
        const on = hl === i || hl === -1;
        const a = ramp(p, 0.05 + i * 0.14, 0.25 + i * 0.14);
        return (
          <div key={i} style={{ ...card({ opacity: (on ? 1 : 0.32) * (0.3 + 0.7 * a), borderColor: hl === i ? accent : theme.rule, background: hl === i ? theme.tealDim : theme.panel }), display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontFamily: theme.display, fontWeight: 700, fontSize: 42, color: theme.ink }}>{b[0]}</div>
            <div style={{ fontFamily: theme.mono, fontSize: 26, color: theme.muted }}>{b[1]}</div>
          </div>
        );
      })}
      <div style={{ fontFamily: theme.body, fontSize: 30, color: theme.muted, marginTop: 8 }}>Request enters at the top, tokens come back out of it.</div>
    </div>
  );
};

export const SweepCurve: React.FC<VisualProps> = ({ p, params, accent }) => {
  const latency = params.phase === 'latency';
  const W = 1300, H = 430, L = 110, B = 70, T = 30;
  const xs = [1, 2, 4, 8, 16, 32];
  const thr = [20, 39, 74, 135, 228, 320];
  const ttft = [180, 195, 230, 310, 520, 980];
  const X = (i: number) => L + (i / (xs.length - 1)) * (W - L - 50);
  const Ythr = (v: number) => H - B - (v / 360) * (H - B - T);
  const Ylat = (v: number) => H - B - (Math.min(v, 1100) / 1100) * (H - B - T);
  const upto = ramp(p, 0.08, 0.85) * (xs.length - 1);
  const pts = (vals: number[], Y: (v: number) => number) =>
    vals.map((v, i) => (i <= upto ? `${i ? 'L' : 'M'}${X(i)},${Y(v)}` : '')).join(' ');
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ maxHeight: 460 }}>
        <line x1={L} y1={H - B} x2={W - 50} y2={H - B} stroke={theme.rule} strokeWidth={2} />
        <line x1={L} y1={T} x2={L} y2={H - B} stroke={theme.rule} strokeWidth={2} />
        {xs.map((x, i) => (
          <text key={i} x={X(i)} y={H - B + 32} fill={theme.muted} fontSize={24} fontFamily={theme.mono} textAnchor="middle">{x}</text>
        ))}
        <text x={(W + L) / 2} y={H - 14} fill={theme.muted} fontSize={24} fontFamily={theme.mono} textAnchor="middle">concurrent requests</text>
        {latency ? (
          <>
            <line x1={L} y1={Ylat(600)} x2={W - 50} y2={Ylat(600)} stroke={theme.bad} strokeWidth={3} strokeDasharray="8 6" />
            <text x={W - 56} y={Ylat(600) - 12} fill={theme.bad} fontSize={24} fontFamily={theme.mono} textAnchor="end">p95 TTFT target</text>
            <path d={pts(ttft, Ylat)} fill="none" stroke={theme.copper} strokeWidth={5} />
            <text x={L + 16} y={T + 26} fill={theme.copper} fontSize={26} fontFamily={theme.mono}>p95 time to first token</text>
          </>
        ) : (
          <>
            <path d={pts(thr, Ythr)} fill="none" stroke={theme.teal} strokeWidth={5} />
            <text x={L + 16} y={T + 26} fill={theme.teal} fontSize={26} fontFamily={theme.mono}>aggregate tokens/sec</text>
          </>
        )}
      </svg>
      <div style={{ fontFamily: theme.body, fontSize: 32, color: theme.ink, textAlign: 'center' }}>
        {latency ? 'Capacity is everything left of where the curve crosses the target.' : 'Throughput climbs with concurrency, then flattens as the GPU saturates.'}
      </div>
    </div>
  );
};

export const PrefixTree: React.FC<VisualProps> = ({ p, params, accent }) => {
  const cached = (params.step ?? 0) === 1;
  const leaf = ['user A', 'user B', 'user C'];
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <div style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
        <div style={{ ...card({ width: 330, borderColor: cached ? theme.good : theme.copper, background: cached ? theme.tealDim : theme.panel }) }}>
          <div style={{ ...label, color: cached ? theme.good : theme.copper }}>{cached ? 'cached · reused' : 'recomputed every call'}</div>
          <div style={{ ...big, fontSize: 40, marginTop: 8 }}>System prompt</div>
          <div style={{ fontFamily: theme.mono, fontSize: 26, color: theme.muted }}>2,000 tokens</div>
        </div>
        <div style={{ fontFamily: theme.mono, fontSize: 40, color: theme.muted }}>→</div>
        <div style={{ ...card({ width: 330, borderColor: cached ? theme.good : theme.copper, background: cached ? theme.tealDim : theme.panel }) }}>
          <div style={{ ...label, color: cached ? theme.good : theme.copper }}>{cached ? 'cached · reused' : 'recomputed every call'}</div>
          <div style={{ ...big, fontSize: 40, marginTop: 8 }}>Tool definitions</div>
          <div style={{ fontFamily: theme.mono, fontSize: 26, color: theme.muted }}>1,500 tokens</div>
        </div>
        <div style={{ fontFamily: theme.mono, fontSize: 40, color: theme.muted }}>→</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {leaf.map((l, i) => (
            <div key={i} style={{ ...card({ padding: '12px 20px', borderColor: accent, opacity: ramp(p, 0.2 + i * 0.12, 0.4 + i * 0.12) }) }}>
              <div style={{ fontFamily: theme.mono, fontSize: 26, color: theme.ink }}>{l} · 60 tokens</div>
            </div>
          ))}
        </div>
      </div>
      <div style={{ ...card({ marginTop: 26, borderColor: cached ? theme.good : theme.rule }) }}>
        <div style={{ fontFamily: theme.mono, fontSize: 34, color: theme.ink }}>
          {cached ? '3 requests · 3,680 tokens sent · 180 computed  (95% reused)' : '3 requests · 3,680 tokens sent · 3,680 computed'}
        </div>
      </div>
    </div>
  );
};

export const QloraMem: React.FC<VisualProps> = ({ p, params, accent }) => {
  const fits = params.mode === 'fits';
  const rows = fits
    ? [['QLoRA 8B on a laptop-class box', 6, theme.teal], ['QLoRA 70B on 128 GB unified', 46, theme.teal], ['Available memory', 100, theme.rule]]
    : [['Full fine-tune · weights', 30, theme.copper], ['+ gradients', 60, theme.copper], ['+ optimizer state', 100, theme.bad], ['QLoRA · 4-bit base + adapter', 22, theme.teal]];
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <div style={{ ...label, color: accent }}>{fits ? 'What fits on one box' : 'Where the memory goes'}</div>
      {rows.map((r, i) => {
        const a = ramp(p, 0.05 + i * 0.16, 0.3 + i * 0.16);
        return (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
            <div style={{ fontFamily: theme.body, fontSize: 30, color: theme.muted, width: 480 }}>{r[0]}</div>
            <div style={{ flex: 1, height: 52, background: theme.panel2, borderRadius: 10, overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${(r[1] as number) * a}%`, background: r[2] as string, borderRadius: 10 }} />
            </div>
          </div>
        );
      })}
      <div style={{ fontFamily: theme.body, fontSize: 32, color: theme.ink, marginTop: 18 }}>
        {fits ? 'The base model stays frozen and quantized; only the adapter trains.' : 'Full fine-tuning holds three heavy things at once. QLoRA holds one, in four bits.'}
      </div>
    </div>
  );
};

export const TwoBox: React.FC<VisualProps> = ({ p, accent }) => {
  const t = ramp(p, 0.15, 0.85);
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 30 }}>
        {[0, 1].map((i) => (
          <React.Fragment key={i}>
            <div style={{ ...card({ flex: 1, borderColor: accent, textAlign: 'center' }) }}>
              <div style={{ ...label, color: accent }}>Box {i + 1}</div>
              <div style={{ ...big, fontSize: 56, marginTop: 10 }}>128 GB</div>
              <div style={{ fontFamily: theme.mono, fontSize: 26, color: theme.muted, marginTop: 6 }}>273 GB/s</div>
            </div>
            {i === 0 && (
              <div style={{ width: 260, textAlign: 'center' }}>
                <div style={{ height: 14, background: theme.panel2, borderRadius: 7, position: 'relative', overflow: 'hidden' }}>
                  <div style={{ position: 'absolute', left: `${(t * 130) % 130 - 30}%`, top: 0, bottom: 0, width: '30%', background: theme.copper, borderRadius: 7 }} />
                </div>
                <div style={{ fontFamily: theme.mono, fontSize: 24, color: theme.muted, marginTop: 10 }}>200 Gb QSFP</div>
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 20, marginTop: 30 }}>
        <div style={{ ...card({ flex: 1, borderColor: theme.good }) }}>
          <div style={{ ...label, color: theme.good }}>You get</div>
          <div style={{ fontFamily: theme.body, fontSize: 34, color: theme.ink, marginTop: 8 }}>256 GB of capacity — a 235B model in four-bit now fits</div>
        </div>
        <div style={{ ...card({ flex: 1, borderColor: theme.bad }) }}>
          <div style={{ ...label, color: theme.bad }}>You do not get</div>
          <div style={{ fontFamily: theme.body, fontSize: 34, color: theme.ink, marginTop: 8 }}>More bandwidth per token — decode stays around 12 tok/s</div>
        </div>
      </div>
    </div>
  );
};

/* ─────────────────────────── worked examples ─────────────────────────── */

export const Worked: React.FC<VisualProps> = ({ p, params, accent }) => {
  const rows: [string, string][] = params.rows ?? [];
  return (
    <div style={{ ...stage, justifyContent: 'center', gap: 16 }}>
      <div style={{ ...label, color: accent }}>{params.heading}</div>
      {params.scenario ? (
        <div style={{ fontFamily: theme.body, fontSize: 34, color: theme.muted, marginBottom: 4 }}>{params.scenario}</div>
      ) : null}
      <div style={{ ...card({ padding: '20px 26px' }) }}>
        {rows.map((r, i) => {
          const a = ramp(p, 0.05 + i * 0.13, 0.22 + i * 0.13);
          return (
            <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 24, alignItems: 'baseline', padding: '9px 0', borderBottom: i < rows.length - 1 ? `1px solid ${theme.rule}` : 'none', opacity: 0.2 + 0.8 * a }}>
              <div style={{ fontFamily: theme.mono, fontSize: 30, color: theme.muted }}>{r[0]}</div>
              <div style={{ fontFamily: theme.mono, fontSize: 32, color: theme.ink, fontWeight: 600 }}>{r[1]}</div>
            </div>
          );
        })}
      </div>
      {params.answer ? (
        <div style={{ ...card({ borderColor: accent, background: theme.tealDim, opacity: ramp(p, 0.62, 0.85) }) }}>
          <div style={{ ...label, color: accent, fontSize: 18 }}>{params.answerLabel ?? 'Answer'}</div>
          <div style={{ fontFamily: theme.display, fontWeight: 700, fontSize: 44, color: theme.ink, marginTop: 6, lineHeight: 1.15 }}>{params.answer}</div>
        </div>
      ) : null}
    </div>
  );
};

export const BeforeAfter: React.FC<VisualProps> = ({ p, params, accent }) => {
  const rows: [string, string, string][] = params.rows ?? [];
  const a = ramp(p, 0.12, 0.6);
  return (
    <div style={{ ...stage, justifyContent: 'center' }}>
      <div style={{ ...label, color: accent }}>{params.heading}</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr', gap: 14 }}>
        <div />
        <div style={{ ...label, textAlign: 'center', color: theme.bad }}>{params.beforeLabel ?? 'before'}</div>
        <div style={{ ...label, textAlign: 'center', color: theme.good }}>{params.afterLabel ?? 'after'}</div>
        {rows.map((r, i) => (
          <React.Fragment key={i}>
            <div style={{ fontFamily: theme.body, fontSize: 32, color: theme.ink, display: 'flex', alignItems: 'center' }}>{r[0]}</div>
            <div style={{ ...card({ padding: '14px 18px', textAlign: 'center', borderColor: theme.rule }) }}>
              <span style={{ fontFamily: theme.mono, fontSize: 34, color: theme.muted }}>{r[1]}</span>
            </div>
            <div style={{ ...card({ padding: '14px 18px', textAlign: 'center', borderColor: accent, opacity: 0.3 + 0.7 * a }) }}>
              <span style={{ fontFamily: theme.mono, fontSize: 34, color: theme.ink }}>{r[2]}</span>
            </div>
          </React.Fragment>
        ))}
      </div>
      {params.note ? <div style={{ fontFamily: theme.body, fontSize: 30, color: theme.muted, marginTop: 14 }}>{params.note}</div> : null}
    </div>
  );
};

/* ─────────────────────────── training deep dives (videos 14–18) ─────────────────────────── */

/** A grid of weights. mode 'full': every cell gets updated. 'lora': grid frozen, two thin matrices train. */
export const WeightUpdate: React.FC<VisualProps> = ({ p, params, accent }) => {
  const mode: string = params.mode ?? 'full';
  const R = 10, C = 16;
  const lit = ramp(p, 0.1, 0.75);
  const cell = (r: number, c: number) => {
    const order = ((r * 7 + c * 13) % 37) / 37;             // pseudo-random update order
    const on = mode === 'full' && order < lit;
    return (
      <div key={`${r}-${c}`} style={{ width: 34, height: 34, borderRadius: 6,
        background: on ? accent : theme.panel2, opacity: on ? 0.55 + 0.45 * ((r + c) % 3) / 2 : 1,
        border: `1px solid ${theme.rule}` }} />
    );
  };
  const grid = (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${C}, 34px)`, gap: 5, opacity: mode === 'lora' ? 0.55 : 1 }}>
      {Array.from({ length: R * C }, (_, i) => cell(Math.floor(i / C), i % C))}
    </div>
  );
  const la = ramp(p, 0.25, 0.6);
  return (
    <div style={{ ...stage, justifyContent: 'center', gap: 22 }}>
      <div style={{ ...label, color: accent }}>{params.heading ?? (mode === 'full' ? 'Full fine-tuning: every weight moves' : 'LoRA: freeze W, train two thin matrices')}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 34 }}>
        <div style={{ position: 'relative' }}>
          {grid}
          <div style={{ fontFamily: theme.mono, fontSize: 26, color: theme.muted, marginTop: 10 }}>
            W · {params.wLabel ?? '4096 × 4096 = 16.8 M weights'} {mode === 'lora' ? '· frozen ❄' : ''}
          </div>
        </div>
        {mode === 'lora' ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 18, opacity: 0.2 + 0.8 * la }}>
            <div style={{ fontFamily: theme.mono, fontSize: 60, color: accent }}>+</div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ width: 40, height: 380, background: accent, borderRadius: 8 }} />
              <div style={{ fontFamily: theme.mono, fontSize: 24, color: theme.muted, marginTop: 8 }}>B</div>
            </div>
            <div style={{ fontFamily: theme.mono, fontSize: 44, color: theme.ink }}>×</div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ width: 380, height: 40, background: accent, borderRadius: 8 }} />
              <div style={{ fontFamily: theme.mono, fontSize: 24, color: theme.muted, marginTop: 8 }}>A</div>
            </div>
          </div>
        ) : (
          <div style={{ ...card({ borderColor: accent, width: 520, opacity: ramp(p, 0.4, 0.7) }) }}>
            <div style={{ ...label, color: accent, fontSize: 18 }}>trainable</div>
            <div style={{ ...big, fontSize: 64, marginTop: 6 }}>100%</div>
            <div style={{ fontFamily: theme.body, fontSize: 28, color: theme.muted, marginTop: 6 }}>each one needs a gradient and optimizer state</div>
          </div>
        )}
      </div>
      {params.note ? <div style={{ fontFamily: theme.body, fontSize: 32, color: theme.ink, opacity: ramp(p, 0.55, 0.8) }}>{params.note}</div> : null}
    </div>
  );
};

/** The training loop: forward → loss → backward → update, with a highlight travelling around. */
export const TrainLoop: React.FC<VisualProps> = ({ p, params, accent }) => {
  const steps: [string, string][] = params.steps ?? [
    ['Forward', 'model reads the example, predicts each next token'],
    ['Loss', 'how surprised was it by the right answer?'],
    ['Backward', 'gradient: which way should each weight move?'],
    ['Update', 'optimizer nudges weights by learning rate × gradient'],
  ];
  const cur = Math.min(steps.length - 1, Math.floor(ramp(p, 0.05, 0.9) * steps.length));
  return (
    <div style={{ ...stage, justifyContent: 'center', gap: 20 }}>
      <div style={{ ...label, color: accent }}>{params.heading ?? 'One training step'}</div>
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${steps.length}, 1fr)`, gap: 16 }}>
        {steps.map((st, i) => (
          <div key={i} style={{ ...card({ borderColor: i === cur ? accent : theme.rule, opacity: i <= cur ? 1 : 0.35, background: i === cur ? theme.tealDim : theme.panel }) }}>
            <div style={{ fontFamily: theme.mono, fontSize: 22, color: i === cur ? accent : theme.muted }}>{i + 1} {i < steps.length - 1 ? '→' : '↺'}</div>
            <div style={{ ...big, fontSize: 44, marginTop: 6 }}>{st[0]}</div>
            <div style={{ fontFamily: theme.body, fontSize: 27, color: theme.muted, marginTop: 8, lineHeight: 1.25 }}>{st[1]}</div>
          </div>
        ))}
      </div>
      {params.note ? <div style={{ fontFamily: theme.body, fontSize: 32, color: theme.ink, marginTop: 8, opacity: ramp(p, 0.6, 0.85) }}>{params.note}</div> : null}
    </div>
  );
};

/** Stacked bytes-per-parameter bar, with the total for a model size. */
export const MemoryLedger: React.FC<VisualProps> = ({ p, params, accent }) => {
  const rows: [string, number, string][] = params.rows ?? [
    ['weights bf16', 2, 'teal'], ['gradients bf16', 2, 'copper'], ['Adam m fp32', 4, 'violet'], ['Adam v fp32', 4, 'violet'], ['master weights fp32', 4, 'warn'],
  ];
  const col = (c: string) => (theme as any)[c] ?? c;
  const total = rows.reduce((a, r) => a + r[1], 0);
  const maxB = params.scaleBytes ?? total;
  const shown = Math.ceil(ramp(p, 0.05, 0.6) * rows.length);
  const params_b: number = params.paramsB ?? 7;
  return (
    <div style={{ ...stage, justifyContent: 'center', gap: 20 }}>
      <div style={{ ...label, color: accent }}>{params.heading ?? 'Bytes per parameter while training'}</div>
      <div style={{ display: 'flex', height: 96, borderRadius: 12, overflow: 'hidden', background: theme.panel2, border: `2px solid ${theme.rule}` }}>
        {rows.map((r, i) => (
          <div key={i} style={{ width: `${(i < shown ? r[1] : 0) / maxB * 100}%`, background: col(r[2]), borderRight: `2px solid ${theme.bg}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: theme.mono, fontSize: 26, color: theme.bg, fontWeight: 700, overflow: 'hidden', whiteSpace: 'nowrap' }}>
            {r[1] >= 1 ? `${r[1]} B` : ''}
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px 26px' }}>
        {rows.map((r, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, opacity: i < shown ? 1 : 0.25 }}>
            <div style={{ width: 22, height: 22, borderRadius: 5, background: col(r[2]) }} />
            <span style={{ fontFamily: theme.mono, fontSize: 26, color: theme.ink }}>{r[0]}</span>
          </div>
        ))}
      </div>
      <div style={{ ...card({ borderColor: accent, opacity: ramp(p, 0.6, 0.85) }), display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <span style={{ fontFamily: theme.mono, fontSize: 34, color: theme.muted }}>{total} bytes × {params_b}B params</span>
        <span style={{ ...big, fontSize: 60 }}>≈ {params.totalText ?? `${Math.round(total * params_b)} GB`}</span>
      </div>
      {params.note ? <div style={{ fontFamily: theme.body, fontSize: 30, color: theme.muted, opacity: ramp(p, 0.7, 0.9) }}>{params.note}</div> : null}
    </div>
  );
};

/** SFT loss masking: prompt tokens are context (no loss), answer tokens are graded. */
export const LossMask: React.FC<VisualProps> = ({ p, params, accent }) => {
  const segs: [string, string][] = params.segments ?? [
    ['system', 'You triage support tickets. Reply with JSON.'],
    ['user', 'Card declined twice, launch is tomorrow.'],
    ['assistant', '{"category": "billing", "severity": 4}'],
  ];
  const masked = ramp(p, 0.35, 0.55);
  return (
    <div style={{ ...stage, justifyContent: 'center', gap: 18 }}>
      <div style={{ ...label, color: accent }}>{params.heading ?? 'One SFT example · where the loss is counted'}</div>
      {segs.map(([role, text], i) => {
        const graded = role === 'assistant';
        const words = text.split(' ');
        return (
          <div key={i} style={{ display: 'grid', gridTemplateColumns: '190px 1fr', gap: 18, alignItems: 'center' }}>
            <div style={{ fontFamily: theme.mono, fontSize: 26, color: graded ? accent : theme.muted, textTransform: 'uppercase', letterSpacing: 2 }}>{role}</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {words.map((w, j) => (
                <span key={j} style={{ fontFamily: theme.mono, fontSize: 30, padding: '6px 12px', borderRadius: 8,
                  background: graded ? (masked > 0.5 ? accent : theme.panel2) : theme.panel2,
                  color: graded && masked > 0.5 ? theme.bg : theme.ink,
                  opacity: graded ? 1 : 1 - 0.55 * masked, border: `1px solid ${theme.rule}` }}>{w}</span>
              ))}
            </div>
          </div>
        );
      })}
      <div style={{ display: 'flex', gap: 28, marginTop: 10, opacity: ramp(p, 0.5, 0.75) }}>
        <Chip color={theme.muted}>context · loss ignored</Chip>
        <Chip color={accent}>answer · loss counted</Chip>
      </div>
      {params.note ? <div style={{ fontFamily: theme.body, fontSize: 30, color: theme.ink, opacity: ramp(p, 0.65, 0.85) }}>{params.note}</div> : null}
    </div>
  );
};

/** Grid of cards (method families). highlight = index to emphasise. */
export const CardGrid: React.FC<VisualProps> = ({ p, params, accent }) => {
  const cards: [string, string, string?][] = params.cards ?? [];
  const hl: number = params.highlight ?? -1;
  const cols = params.cols ?? 3;
  return (
    <div style={{ ...stage, justifyContent: 'center', gap: 18 }}>
      <div style={{ ...label, color: accent }}>{params.heading}</div>
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 16 }}>
        {cards.map((c, i) => {
          const a = ramp(p, 0.04 + i * 0.09, 0.2 + i * 0.09);
          const on = hl === -1 || hl === i;
          return (
            <div key={i} style={{ ...card({ borderColor: hl === i ? accent : theme.rule, opacity: (on ? 1 : 0.45) * (0.2 + 0.8 * a), background: hl === i ? theme.tealDim : theme.panel, padding: '18px 22px' }) }}>
              <div style={{ fontFamily: theme.display, fontWeight: 700, fontSize: 38, color: theme.ink }}>{c[0]}</div>
              <div style={{ fontFamily: theme.body, fontSize: 26, color: theme.muted, marginTop: 6, lineHeight: 1.25 }}>{c[1]}</div>
              {c[2] ? <div style={{ fontFamily: theme.mono, fontSize: 24, color: accent, marginTop: 10 }}>{c[2]}</div> : null}
            </div>
          );
        })}
      </div>
      {params.note ? <div style={{ fontFamily: theme.body, fontSize: 30, color: theme.ink, opacity: ramp(p, 0.7, 0.9) }}>{params.note}</div> : null}
    </div>
  );
};

/** A preference pair: one prompt, a chosen and a rejected answer. */
export const PrefPair: React.FC<VisualProps> = ({ p, params, accent }) => {
  const a = ramp(p, 0.15, 0.4), b = ramp(p, 0.35, 0.6), v = ramp(p, 0.6, 0.8);
  return (
    <div style={{ ...stage, justifyContent: 'center', gap: 20 }}>
      <div style={{ ...label, color: accent }}>{params.heading ?? 'One preference pair'}</div>
      <div style={{ ...card() }}>
        <div style={{ ...label, fontSize: 18 }}>prompt</div>
        <div style={{ fontFamily: theme.body, fontSize: 34, color: theme.ink, marginTop: 6 }}>{params.prompt}</div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
        <div style={{ ...card({ borderColor: v > 0.5 ? theme.good : theme.rule, opacity: 0.2 + 0.8 * a }) }}>
          <div style={{ ...label, fontSize: 18, color: theme.good }}>{v > 0.5 ? '✓ chosen' : 'answer A'}</div>
          <div style={{ fontFamily: theme.body, fontSize: 30, color: theme.ink, marginTop: 6, lineHeight: 1.3 }}>{params.chosen}</div>
        </div>
        <div style={{ ...card({ borderColor: v > 0.5 ? theme.bad : theme.rule, opacity: 0.2 + 0.8 * b }) }}>
          <div style={{ ...label, fontSize: 18, color: theme.bad }}>{v > 0.5 ? '✗ rejected' : 'answer B'}</div>
          <div style={{ fontFamily: theme.body, fontSize: 30, color: theme.ink, marginTop: 6, lineHeight: 1.3 }}>{params.rejected}</div>
        </div>
      </div>
      {params.note ? <div style={{ fontFamily: theme.body, fontSize: 30, color: theme.muted, opacity: v }}>{params.note}</div> : null}
    </div>
  );
};

/** RLHF: SFT model → reward model → PPO loop with a KL leash to the reference. stage 0..3 */
export const RlhfLoop: React.FC<VisualProps> = ({ p, params, accent }) => {
  const st: number = params.stage ?? 3;
  const boxes: [string, string][] = [
    ['1 · SFT model', 'start from a model that already follows instructions'],
    ['2 · Reward model', 'trained on human A-vs-B choices → outputs a score'],
    ['3 · PPO loop', 'policy writes answers, reward model scores, policy updates'],
  ];
  const kl = ramp(p, 0.45, 0.75);
  return (
    <div style={{ ...stage, justifyContent: 'center', gap: 22 }}>
      <div style={{ ...label, color: accent }}>{params.heading ?? 'RLHF in three stages'}</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 18 }}>
        {boxes.map((b, i) => {
          const on = i <= st;
          return (
            <div key={i} style={{ ...card({ borderColor: i === st ? accent : theme.rule, opacity: on ? 1 : 0.3, background: i === st ? theme.tealDim : theme.panel }) }}>
              <div style={{ fontFamily: theme.display, fontWeight: 700, fontSize: 38, color: theme.ink }}>{b[0]}</div>
              <div style={{ fontFamily: theme.body, fontSize: 27, color: theme.muted, marginTop: 8, lineHeight: 1.25 }}>{b[1]}</div>
            </div>
          );
        })}
      </div>
      {st >= 2 ? (
        <div style={{ ...card({ borderColor: theme.warn, opacity: 0.2 + 0.8 * kl }), display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 24, alignItems: 'center' }}>
          <div style={{ fontFamily: theme.mono, fontSize: 30, color: theme.warn }}>objective</div>
          <div style={{ fontFamily: theme.mono, fontSize: 34, color: theme.ink }}>maximise  reward(answer)  −  β · KL(policy ‖ reference)</div>
        </div>
      ) : null}
      {params.note ? <div style={{ fontFamily: theme.body, fontSize: 30, color: theme.ink, opacity: ramp(p, 0.6, 0.85) }}>{params.note}</div> : null}
    </div>
  );
};

/** DPO: probability of chosen goes up, rejected goes down, relative to a frozen reference. */
export const DpoShift: React.FC<VisualProps> = ({ p, params, accent }) => {
  const t = ramp(p, 0.15, 0.7);
  const ref = { chosen: 42, rejected: 38 };
  const pol = { chosen: 42 + 30 * t, rejected: 38 - 24 * t };
  const bar = (name: string, refv: number, polv: number, color: string) => (
    <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 18, alignItems: 'center' }}>
      <div style={{ fontFamily: theme.mono, fontSize: 30, color }}>{name}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ height: 30, width: `${refv}%`, background: theme.panel2, border: `2px dashed ${theme.muted}`, borderRadius: 6 }} />
          <span style={{ fontFamily: theme.mono, fontSize: 22, color: theme.muted }}>reference (frozen)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ height: 38, width: `${polv}%`, background: color, borderRadius: 6 }} />
          <span style={{ fontFamily: theme.mono, fontSize: 22, color: theme.ink }}>policy (training)</span>
        </div>
      </div>
    </div>
  );
  return (
    <div style={{ ...stage, justifyContent: 'center', gap: 24 }}>
      <div style={{ ...label, color: accent }}>{params.heading ?? 'What DPO does to probabilities'}</div>
      {bar('chosen ✓', ref.chosen, pol.chosen, theme.good)}
      {bar('rejected ✗', ref.rejected, pol.rejected, theme.bad)}
      <div style={{ ...card({ borderColor: accent, opacity: ramp(p, 0.55, 0.8) }) }}>
        <div style={{ fontFamily: theme.mono, fontSize: 30, color: theme.ink, lineHeight: 1.4 }}>
          loss = −log σ( β · [ (log π(chosen) − log π_ref(chosen)) − (log π(rejected) − log π_ref(rejected)) ] )
        </div>
      </div>
      {params.note ? <div style={{ fontFamily: theme.body, fontSize: 30, color: theme.muted, opacity: ramp(p, 0.7, 0.9) }}>{params.note}</div> : null}
    </div>
  );
};

export const VISUALS: Record<string, React.FC<VisualProps>> = {
  Title, Outro, Bullets, PrefillDecode, Metrics,
  KvGrow, KvMath, KvBlocks, KvQuant,
  BandwidthPipe, Ceiling, DeviceTable, Roofline, Precision,
  BatchGantt, ChunkedPrefill, SpecDecode,
  TrainingPipeline, LoRA, TrainDecide,
  MemoryStack, Offload, MoEActive, Parallelism,
  PlatformMap, Modes, Maturity,
  Recap, EndCard, CommandCard, ServingStack, SweepCurve, PrefixTree, QloraMem, TwoBox,
  Worked, BeforeAfter,
  WeightUpdate, TrainLoop, MemoryLedger, LossMask, CardGrid, PrefPair, RlhfLoop, DpoShift,
};
