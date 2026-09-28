#!/usr/bin/env python3
"""
Generate narration on Apple silicon with Kokoro-82M through MLX (mlx-audio).

  pip install mlx-audio misaki soundfile numpy
  python scripts/tts_mlx.py                       # all videos
  python scripts/tts_mlx.py --video kv-cache      # one video
  python scripts/tts_mlx.py --voice am_michael --speed 1.0

Writes public/audio/<video>/NN.wav (24 kHz) and public/scenes/<video>.json,
which is what Remotion reads to size each scene. Identical output contract to
scripts/tts_onnx.py (the Linux/CPU path used to render the delivered MP4s).
"""
from __future__ import annotations
import argparse, json, pathlib, re
import numpy as np, soundfile as sf

ROOT = pathlib.Path(__file__).resolve().parents[1]
SR = 24_000

# spoken forms for things a TTS model reads badly
SUBS = [
    (r'\bRLHF\b', 'R L H F'), (r'\bRLAIF\b', 'R L A I F'), (r'\bPPO\b', 'P P O'), (r'\bGRPO\b', 'G R P O'),
    (r'\bPEFT\b', 'peft'), (r'\bDoRA\b', 'Dora'), (r'\bKL\b', 'K L'), (r'\bORPO\b', 'or po'), (r'\bIPO\b', 'I P O'),
    (r'\bKTO\b', 'K T O'), (r'\bSimPO\b', 'sim po'), (r'\bIA3\b', 'I A three'), (r'\bMLX\b', 'M L X'), (r'\bTRL\b', 'T R L'),
    (r'\bFSDP\b', 'F S D P'), (r'\bZeRO\b', 'zero'), (r'\bbf16\b', 'B F sixteen'), (r'\bPOC\b', 'P O C'), (r'\bJSON\b', 'jason'),
    (r'\bvs\b', 'versus'), (r'\b([FLT])([1-9])\b', r'\1 \2'), (r'β', 'beta'), (r'σ', 'sigma'), (r'π', 'pi'),
    (r'\bTTFT\b', 'T T F T'), (r'\bITL\b', 'I T L'), (r'\bTPOT\b', 'T POT'),
    (r'\bKV\b', 'K V'), (r'\bp95\b', 'p ninety five'), (r'\bp50\b', 'p fifty'),
    (r'\bGB/s\b', 'gigabytes per second'), (r'\bTB/s\b', 'terabytes per second'),
    (r'\btok/s\b', 'tokens per second'), (r'\bFP(\d+)\b', r'F P \1'), (r'\bINT4\b', 'int four'),
    (r'\bNVFP4\b', 'N V F P four'), (r'\bMXFP4\b', 'M X F P four'), (r'\bLoRA\b', 'LoRah'),
    (r'\bQLoRA\b', 'Q LoRah'), (r'\bSFT\b', 'S F T'), (r'\bDPO\b', 'D P O'), (r'\bRFT\b', 'R F T'),
    (r'\bMoE\b', 'mixture of experts'), (r'\bvLLM\b', 'v L L M'), (r'\bSGLang\b', 'S G Lang'),
    (r'\bGPU\b', 'G P U'), (r'\bGPUs\b', 'G P Uz'), (r'\bAPI\b', 'A P I'), (r'\bSLA\b', 'S L A'),
    (r'\bH100\b', 'H one hundred'), (r'\bH200\b', 'H two hundred'), (r'\bB200\b', 'B two hundred'),
    (r'×', ' times '), (r'÷', ' divided by '), (r'=', ' equals '), (r'→', ' then '),
    (r'α', 'alpha'), (r'\^', ' to the power '), (r'\s*·\s*', ', '), (r'—', ', '), (r'–', ' to '),
    (r'\$', ' dollars '), (r'%', ' percent'),
]

def speakable(t: str) -> str:
    for pat, rep in SUBS:
        t = re.sub(pat, rep, t)
    return re.sub(r'\s+', ' ', t).strip()

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default='mlx-community/Kokoro-82M-bf16')
    ap.add_argument('--voice', default='af_heart')
    ap.add_argument('--speed', type=float, default=0.96)
    ap.add_argument('--lang', default='a')
    ap.add_argument('--video')
    a = ap.parse_args()

    from mlx_audio.tts.utils import load_model   # imported late so --help works without mlx

    model = load_model(a.model)
    data = json.loads((ROOT / 'src' / 'narration.json').read_text())
    ids = [a.video] if a.video else list(data)
    (ROOT / 'public' / 'scenes').mkdir(parents=True, exist_ok=True)

    for vid in ids:
        v = data[vid]
        out = ROOT / 'public' / 'audio' / vid
        out.mkdir(parents=True, exist_ok=True)
        scenes = []
        print(f'\n▶ {vid} — {v["title"]}', flush=True)

        for i, sc in enumerate(v['scenes'], start=1):
            chunks = []
            for result in model.generate(text=speakable(sc['text']), voice=a.voice,
                                         speed=a.speed, lang_code=a.lang):
                chunks.append(np.asarray(result.audio, dtype=np.float32).reshape(-1))
            wav = np.concatenate(chunks)
            lead, tail = 0.35, (1.1 if sc['visual'] in ('Title', 'Recap', 'EndCard') else 0.7)
            wav = np.concatenate([np.zeros(int(lead * SR), np.float32), wav,
                                  np.zeros(int(tail * SR), np.float32)])
            name = f'{i:02d}.wav'
            sf.write(out / name, wav, SR)
            secs = len(wav) / SR
            scenes.append({'index': i, 'visual': sc['visual'], 'audio': f'audio/{vid}/{name}',
                           'durationSeconds': round(secs, 3), 'text': sc['text'], 'leadSeconds': lead})
            print(f'   {name} {secs:6.2f}s  {sc["visual"]}', flush=True)

        payload = {'video': vid, 'voice': a.voice, 'sampleRate': SR,
                   'totalSeconds': round(sum(s['durationSeconds'] for s in scenes), 2),
                   'scenes': scenes}
        (ROOT / 'public' / 'scenes' / f'{vid}.json').write_text(json.dumps(payload, indent=2))
        print(f'   → {payload["totalSeconds"]}s total', flush=True)

    print('\nDone. npm run dev to preview, npm run render to export.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
