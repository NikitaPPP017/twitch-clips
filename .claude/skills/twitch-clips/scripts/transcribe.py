"""Транскрипт mlx-whisper с таймкодами по словам.

Usage: python transcribe.py            (work/audio.wav -> work/transcript.{json,srt,txt})
       python transcribe.py --clean    (только повторная фильтрация готового json)
"""
import json
import re
import sys
import time

from common import AUDIO, TRANSCRIPT, config, fmt

# фразы, которые Whisper "слышит" в тишине и музыке (артефакты обучения на субтитрах)
HALLUCINATIONS = re.compile(r"DimaTorzok|Продолжение следует|Редактор субтитров|Корректор|Субтитры (создавал|сделал)", re.I)


def write_outputs(segments):
    segments = [s for s in segments if not HALLUCINATIONS.search(s["text"])]
    json.dump(segments, open(f"{TRANSCRIPT}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(f"{TRANSCRIPT}.srt", "w", encoding="utf-8") as f:
        for i, s in enumerate(segments, 1):
            a, b = s["start"], s["end"]
            ts = lambda t: f"{int(t // 3600):02}:{int(t % 3600 // 60):02}:{int(t % 60):02},{int(t % 1 * 1000):03}"
            f.write(f"{i}\n{ts(a)} --> {ts(b)}\n{s['text'].strip()}\n\n")
    with open(f"{TRANSCRIPT}.txt", "w", encoding="utf-8") as f:
        for s in segments:
            f.write(f"[{fmt(s['start'])}] {s['text'].strip()}\n")
    return segments


def main():
    if "--clean" in sys.argv:
        segs = write_outputs(json.load(open(f"{TRANSCRIPT}.json", encoding="utf-8")))
        print(f"segments after cleanup: {len(segs)}")
        return
    import mlx_whisper

    cfg = config()
    started = time.time()
    result = mlx_whisper.transcribe(
        str(AUDIO),
        path_or_hf_repo=cfg["detector"]["whisper_model"],
        language=cfg["language"],
        word_timestamps=True,
        condition_on_previous_text=False,  # иначе на длинных записях зацикливается
        verbose=False,
    )
    segs = write_outputs(result["segments"])
    print(f"transcript: {len(segs)} segments, {time.time() - started:.0f}s")


if __name__ == "__main__":
    main()
