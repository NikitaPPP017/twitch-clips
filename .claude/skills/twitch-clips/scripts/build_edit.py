"""Шаг 6: монтажный лист для Remotion - вырезка пауз, субтитры, раскладка, стиль.

Usage: python build_edit.py [id ...]   (без id - все моменты из work/moments.json)

Берёт work/clips/cuts.json, work/layouts.json, транскрипт, work/audio.wav и config.json.
Пишет work/remotion/public/edits/<name>.json и копирует куски в work/remotion/public/clips/.

Паузы (если pauses.cut): тихий участок длиннее min_pause_sec ужимается до keep_pad_sec
с каждой стороны. Тишина = тихо по громкости И нет слова транскрипта, поэтому смех
(громкий) и тихая речь (стример читает чат вполголоса) не вырезаются.
Раскладка куска: {"cam": [x,y,w,h], "content": [x,y,w,h]} или {"full": [x,y,w,h]}
(вебка на весь кадр, когда на стриме только вебка) или {"switch": [[сек от начала куска, раскладка], ...]}.
"""
import re
import shutil
import sys

import numpy as np
import soundfile as sf

from common import AUDIO, CLIPS, LAYOUTS, MOMENTS, REMOTION, config, load, save, words
from cut_clips import clip_name

FRAME = 0.05  # шаг анализа громкости, с
MIN_PIECE = 0.4  # короче этого кусок звука между паузами не оставляем
SPEECH_DB = 12  # "звук" = громче шумового пола куска на столько dB
MAX_GAP = 0.6  # пауза между словами, после которой начинается новая реплика


def keep_ranges(audio, sr, start, end, W, min_pause, pad):
    a = audio[int(start * sr) : int(end * sr)]
    hop = int(FRAME * sr)
    n = len(a) // hop
    if n == 0:
        return [[0, round(end - start, 2)]]
    db = 20 * np.log10(np.sqrt((a[: n * hop].reshape(n, hop) ** 2).mean(axis=1)) + 1e-9)
    loud = db > np.percentile(db, 15) + SPEECH_DB
    for w in W:
        w0 = max(w["start"], w["end"] - 0.8)  # у растянутых слов речь только в конце
        i0, i1 = int((w0 - start) / FRAME), int((w["end"] - start) / FRAME) + 1
        if i1 > 0 and i0 < n:
            loud[max(0, i0) : min(n, i1)] = True
    ranges, i = [], 0
    while i < n:
        if not loud[i]:
            i += 1
            continue
        j = i
        while j < n:
            if loud[j]:
                j += 1
                continue
            k = j
            while k < n and not loud[k]:
                k += 1
            if k < n and (k - j) * FRAME < min_pause:
                j = k  # короткая пауза - часть речи
            else:
                break
        ranges.append([i * FRAME, j * FRAME])
        i = j
    merged = []
    for s, e in ranges:
        s, e = max(0, s - pad), min(end - start, e + pad)
        if merged and s - merged[-1][1] < min_pause - 2 * pad:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    merged = [r for r in merged if r[1] - r[0] >= MIN_PIECE] or [[0, end - start]]
    merged[0][0], merged[-1][1] = 0, end - start  # границы уже выставлены по словам на шаге 5
    return [[round(s, 2), round(e, 2)] for s, e in merged]


def clean(word, st):
    w = re.sub(r"[,…:;«»\"]+$", "", word.strip())
    if st["uppercase"]:
        w = w.upper()
    core = w.rstrip("?!.")
    return st["fixes"].get(core.upper(), core) + w[len(core):]


def subtitles(W, pieces, st):
    out, t_out, prev_src = [], 0.0, None
    for p in pieces:
        brk = p["src"] != prev_src
        prev_src = p["src"]
        for w in W:
            if p["vod_start"] <= (w["start"] + w["end"]) / 2 < p["vod_end"]:
                shift = t_out - p["vod_start"]
                t0 = max(w["start"], w["end"] - 0.8, p["vod_start"])  # растянутые слова показываем ближе к концу
                out.append({"t0": t0 + shift, "t1": w["end"] + shift, "text": clean(w["word"], st), "brk": brk})
                brk = False  # на границе кусков подборки реплика начинается заново
        t_out += p["vod_end"] - p["vod_start"]

    subs, cur = [], None
    for w in out:
        if not w["text"]:
            continue
        if cur and w["text"].startswith("-"):  # "МЫ" + "-ТО"
            cur["text"] += w["text"]
            cur["end"] = w["t1"]
            continue
        new = (cur is None or w["t0"] - cur["end"] > MAX_GAP or len(cur["text"]) + 1 + len(w["text"]) > st["max_chars"]
               or cur["text"][-1] in "?!." or w["brk"])
        if new and not w["brk"] and cur and " " in cur["text"] and len(cur["text"].rsplit(" ", 1)[1]) <= 2 \
                and w["t0"] - cur["end"] <= MAX_GAP:
            head, tail = cur["text"].rsplit(" ", 1)  # предлог в конце строки переносим на следующую
            cur["text"] = head
            cur = {"start": cur["end"], "end": w["t1"], "text": f"{tail} {w['text']}"}
            subs.append(cur)
        elif new:
            cur = {"start": w["t0"], "end": w["t1"], "text": w["text"]}
            subs.append(cur)
        else:
            cur["text"] += " " + w["text"]
            cur["end"] = w["t1"]
    for i, s in enumerate(subs):
        nxt = subs[i + 1]["start"] if i + 1 < len(subs) else s["end"] + 1.2
        s["end"] = round(min(nxt, s["end"] + 1.2), 2)
        s["start"] = round(s["start"], 2)
        s["text"] = ("- " if st["dash"] else "") + s["text"].rstrip(".")
    return subs


def main(ids):
    cfg = config()
    st, pz = cfg["subtitles"], cfg["pauses"]
    style = {"nickname": cfg["nickname"], "subtitles": st, "badge": cfg["badge"], "cam_height": cfg["layout"]["cam_height"]}
    audio, sr = sf.read(AUDIO, dtype="float32")
    W = words()
    cuts, layouts = load(CLIPS / "cuts.json"), load(LAYOUTS)
    pub = REMOTION / "public"
    (pub / "clips").mkdir(parents=True, exist_ok=True)
    (pub / "edits").mkdir(parents=True, exist_ok=True)

    for m in load(MOMENTS):
        if ids and m["id"] not in ids:
            continue
        name = clip_name(m)
        if name not in layouts:
            sys.exit(f"ОШИБКА: нет раскладки для {name} в work/layouts.json")
        pieces = []
        for k, (start, end) in enumerate(cuts[name], 1):
            src = f"{name}_s{k}.mp4"
            shutil.copy(CLIPS / src, pub / "clips" / src)
            lay = layouts[name][min(k, len(layouts[name])) - 1]
            switches = lay["switch"] if "switch" in lay else [[0, lay]]
            ranges = keep_ranges(audio, sr, start, end, W, pz["min_pause_sec"], pz["keep_pad_sec"]) if pz["cut"] \
                else [[0, round(end - start, 2)]]
            for s, e in ranges:
                for j, (t, l) in enumerate(switches):
                    t_next = switches[j + 1][0] if j + 1 < len(switches) else float("inf")
                    a, b = max(s, t), min(e, t_next)
                    if b - a >= 1 / 30:
                        pieces.append({"src": f"clips/{src}", "from": round(a, 2), "to": round(b, 2),
                                       "vod_start": start + a, "vod_end": start + b, **l})
        dur = sum(p["to"] - p["from"] for p in pieces)
        save({"name": name, "duration": round(dur, 2), "style": style, "pieces": pieces,
              "subtitles": subtitles(W, pieces, st)}, pub / "edits" / f"{name}.json")
        warn = f"  ВНИМАНИЕ: длиннее {cfg['max_clip_seconds']} с" if dur > cfg["max_clip_seconds"] else ""
        print(f"{name}: {sum(e - s for s, e in cuts[name]):.1f} с -> {dur:.1f} с, кусков {len(pieces)}{warn}")


if __name__ == "__main__":
    main([int(x) for x in sys.argv[1:]])
