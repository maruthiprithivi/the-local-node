#!/usr/bin/env python3
"""Regenerate only some scenes of an already-voiced video (e.g. after editing an end card).
    python scripts/tts_patch.py --video kv-cache --scenes last
    python scripts/tts_patch.py --video kv-cache --scenes 0,9
Keeps every other scene's audio and timing untouched."""
import argparse, json, pathlib, sys
import numpy as np, soundfile as sf
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from tts_onnx import ROOT, SR, speakable  # same substitutions and pacing rules
from kokoro_onnx import Kokoro

ap = argparse.ArgumentParser()
ap.add_argument('--video', required=True)
ap.add_argument('--scenes', required=True, help="comma list of 0-based indices, or 'last'")
ap.add_argument('--voice', default='af_heart'); ap.add_argument('--speed', type=float, default=0.96)
a = ap.parse_args()
data = json.loads((ROOT / 'src' / 'narration.json').read_text())[a.video]
tj = ROOT / 'public' / 'scenes' / f'{a.video}.json'
timing = json.loads(tj.read_text())
idx = [len(data['scenes']) - 1] if a.scenes == 'last' else [int(x) for x in a.scenes.split(',')]
k = Kokoro(str(ROOT.parent / 'tts' / 'kokoro-v1.0.onnx'), str(ROOT.parent / 'tts' / 'voices-v1.0.bin'))
for i in idx:
    sc = data['scenes'][i]
    wav, _ = k.create(speakable(sc['text']), voice=a.voice, speed=a.speed, lang='en-us')
    lead, tail = 0.35, (1.1 if sc['visual'] in ('Title', 'Recap', 'EndCard') else 0.7)
    wav = np.concatenate([np.zeros(int(lead * SR), np.float32), np.asarray(wav, np.float32), np.zeros(int(tail * SR), np.float32)])
    name = f'{i + 1:02d}.wav'
    sf.write(ROOT / 'public' / 'audio' / a.video / name, wav, SR)
    timing['scenes'][i].update(durationSeconds=round(len(wav) / SR, 3), text=sc['text'], visual=sc['visual'])
    print(f'{a.video} scene {i + 1}: {len(wav) / SR:.2f}s')
timing['totalSeconds'] = round(sum(s['durationSeconds'] for s in timing['scenes']), 2)
tj.write_text(json.dumps(timing, indent=2))
