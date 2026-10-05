"""Детектор смеха и громкости по аудио стрима.

Usage: python laugh_detect.py   (work/audio.wav -> work/laugh.json)

Модель AST (AudioSet), классы Laughter / Giggle / Snicker / Belly laugh / Chuckle.
Окна 2 с, шаг 1 с. laugh = максимум вероятностей этих классов (0..1).
loud = громкость окна в dB минус медиана окрестности +-60 с.
ВАЖНО: Twitch VOD содержит одну общую дорожку (микрофон + видео + игра + музыка),
поэтому детектор слышит и чужой смех. Пики надо проверять по вебке (sheets.py faces).
"""
import json

import numpy as np
import soundfile as sf
import torch
from transformers import ASTFeatureExtractor, ASTForAudioClassification

from common import AUDIO, LAUGH, config, fmt

SR, WIN, HOP, BATCH = 16000, 2.0, 1.0, 32
LAUGH_IDS = [16, 18, 19, 20, 21]


def main():
    model_id = config()["detector"]["laugh_model"]
    audio, sr = sf.read(AUDIO, dtype="float32")
    assert sr == SR, sr
    n = int((len(audio) / SR - WIN) // HOP) + 1
    starts = [int(i * HOP * SR) for i in range(n)]

    rms = np.array([np.sqrt(np.mean(audio[s : s + int(WIN * SR)] ** 2) + 1e-10) for s in starts])
    db = 20 * np.log10(rms)
    loud = np.array([db[i] - np.median(db[max(0, i - 60) : i + 60]) for i in range(n)])

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    fe = ASTFeatureExtractor.from_pretrained(model_id)
    model = ASTForAudioClassification.from_pretrained(model_id).to(device).eval()
    laugh = np.zeros(n)
    for b in range(0, n, BATCH):
        chunk = [audio[s : s + int(WIN * SR)] for s in starts[b : b + BATCH]]
        feats = fe(chunk, sampling_rate=SR, return_tensors="pt")["input_values"].to(device)
        with torch.no_grad():
            laugh[b : b + len(chunk)] = torch.sigmoid(model(feats).logits)[:, LAUGH_IDS].max(dim=1).values.cpu().numpy()
        if b % (BATCH * 100) == 0:
            print(f"laugh: {fmt(b * HOP)} / {fmt(n * HOP)}", flush=True)

    json.dump([{"t": i * HOP, "laugh": round(float(laugh[i]), 3), "loud": round(float(loud[i]), 1)} for i in range(n)],
              open(LAUGH, "w"), separators=(",", ":"))
    print(f"laugh: {n} windows, max {laugh.max():.3f}")


if __name__ == "__main__":
    main()
