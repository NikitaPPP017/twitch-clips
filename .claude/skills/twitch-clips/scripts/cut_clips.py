"""Шаг 5: нарезка кусков по work/moments.json.

Usage: python cut_clips.py [id ...]   (без id - все моменты)

Границы привязываются к словам транскрипта: рез не режет слово, тишина по краям
ужимается до LEAD/TAIL. Каждый кусок режется с перекодированием (точный до кадра):
work/clips/<NN>_<slug>_s<K>.mp4. Фактические границы -> work/clips/cuts.json.
"""
import json
import re
import subprocess
import sys

from common import CLIPS, MOMENTS, VOD, config, load, save, sec, words

LEAD, TAIL = 0.3, 1.2  # хвост длиннее, чтобы не срезать смех после последней фразы
MAX_WORD = 1.5  # "слово" длиннее = Whisper приклеил к нему паузу/музыку, таймкоду не доверяем


def slug(title):
    tr = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
                  "a b v g d e e zh z i y k l m n o p r s t u f h c ch sh sch _ y _ e yu ya".split()))
    s = "".join(tr.get(c, c) for c in title.lower())
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")[:40]


def clip_name(m):
    return f"{m['id']:02}_{slug(m['title'])}"


def snap(W, start, end):
    idx = [i for i, w in enumerate(W) if w["end"] > start and w["start"] < end and w["end"] - w["start"] <= MAX_WORD]
    if not idx:
        return start, end
    first, last = W[idx[0]], W[idx[-1]]
    prev_end = W[idx[0] - 1]["end"] if idx[0] > 0 else 0
    next_start = W[idx[-1] + 1]["start"] if idx[-1] + 1 < len(W) else last["end"] + TAIL
    new_start = max(first["start"] - LEAD, prev_end + 0.02)
    if first["start"] >= start:
        new_start = max(new_start, start)
    new_end = min(last["end"] + TAIL, next_start - 0.02)
    if last["end"] <= end:
        new_end = min(new_end, end)
    return round(new_start, 2), round(new_end, 2)


def main(ids):
    W = words()
    max_len = config()["max_clip_seconds"]
    CLIPS.mkdir(parents=True, exist_ok=True)
    cuts = load(CLIPS / "cuts.json", {})
    for m in load(MOMENTS):
        if ids and m["id"] not in ids:
            continue
        name = clip_name(m)
        cuts[name] = []
        for k, (a, b) in enumerate(m["segments"], 1):
            s, e = snap(W, sec(a), sec(b))
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(s), "-i", str(VOD), "-t", str(e - s),
                            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
                            str(CLIPS / f"{name}_s{k}.mp4")], check=True)
            cuts[name].append([s, e])
        total = sum(e - s for s, e in cuts[name])
        warn = f"  ВНИМАНИЕ: длиннее {max_len} с, убери слабые куски (не ускорять)" if total > max_len else ""
        print(f"{name}: {len(cuts[name])} кусков, {total:.1f} с (до вырезки пауз){warn}")
    save(cuts, CLIPS / "cuts.json")


if __name__ == "__main__":
    main([int(x) for x in sys.argv[1:]])
