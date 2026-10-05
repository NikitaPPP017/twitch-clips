"""Сигналы для отбора моментов: смех (аудио), громкость, чат, реплики транскрипта.

Usage: python signals.py            -> work/signals.txt: топ-20 пиков смеха, всплески чата,
                                       40 кандидатов по сумме сигналов, вердикт "скучный стрим"
       python signals.py --moments  -> work/moment_signals.json + таблица: по какому сигналу
                                       выбран каждый момент из work/moments.json, какие из
                                       топ-20 пиков смеха попали в моменты

Пороги относительные (по этому стриму): p99 = "заметный смех", p99.9 = "сильный".
Абсолютный порог strong_laugh из config.json: если ни один пик его не превысил,
стрим считается скучным по смеху - моменты не выдумывать.
"""
import json
import re
import sys

import numpy as np

from common import CHAT, LAUGH, MOMENTS, WORK, config, fmt, load, save, sec, words

LAUGH_CHAT = re.compile(r"KEKW|LUL|OMEGALUL|LMAO|ICANT|pepeLaugh|xd\b|ахах|хаха|ахпх|азаз|axax|хпва|пхах|ору|ржу|лол\b|"
                        r"\){3,}|😂|🤣|💀|😹|😭", re.I)
LAUGH_TEXT = re.compile(r"ржешь|ржёте|ржете|смешно|умру от|ахах|хаха", re.I)


def laugh_episodes(lau, loud, thr):
    eps, cur = [], None
    for i, v in enumerate(lau):
        if v > thr:
            if cur and i - cur[1] <= 4:
                cur[1] = i
            else:
                cur = [i, i]
                eps.append(cur)
    out = []
    for a, b in eps:
        seg = lau[a : b + 1]
        out.append({"t": a + int(np.argmax(seg)), "start": a, "dur": b - a + 2, "peak": float(seg.max()),
                    "loud": float(max(loud[a : b + 1].max(), 0))})
    return sorted(out, key=lambda e: -e["peak"])


def chat_laughs(chat, t0, t1, lag):
    """Сообщения со смехом в окне [t0, t1 + lag + 8] (чат отстаёт от стрима)."""
    return [m["message"] for m in chat if t0 <= m["time_in_seconds"] <= t1 + lag + 8 and LAUGH_CHAT.search(m["message"] or "")]


def main():
    cfg = config()["detector"]
    L = load(LAUGH)
    lau = np.array([x["laugh"] for x in L])
    loud = np.array([x["loud"] for x in L])
    chat = load(CHAT, [])
    W = words()
    p99, p999 = float(np.percentile(lau, 99)), float(np.percentile(lau, 99.9))
    eps = laugh_episodes(lau, loud, p99)
    top = eps[:20]
    for e in top:
        e["chat_laugh"] = chat_laughs(chat, e["t"], e["t"], cfg["chat_lag_sec"])[:3]
        e["strong"] = e["peak"] >= cfg["strong_laugh"]

    if "--moments" in sys.argv:
        return per_moment(lau, loud, chat, W, top, p99, p999, cfg)

    # кандидаты: сумма сигналов, сглаженная окном 10 с, разнос 45 с
    n = len(lau)
    score = np.clip(lau / 0.05, 0, 4) + np.clip((loud - 6) / 4, 0, 2)
    for m in chat:
        if LAUGH_CHAT.search(m["message"] or ""):
            t = int(m["time_in_seconds"]) - cfg["chat_lag_sec"]
            score[max(0, t - 8) : max(0, t + 8)] += 1.0
    for w in W:
        if LAUGH_TEXT.search(w["word"]):
            score[max(0, int(w["start"]) - 10) : int(w["start"]) + 3] += 1.5
    sm = np.convolve(score, np.ones(10) / 10, "same")
    cands = []
    for i in np.argsort(-sm):
        if all(abs(i - c) > 45 for c in cands):
            cands.append(int(i))
        if len(cands) == 40:
            break

    # всплески чата (окно 30 с относительно медианы), только для чтения человеком
    rate = np.zeros(n + 60)
    for m in chat:
        rate[min(int(m["time_in_seconds"]), n + 59)] += 1
    win = np.convolve(rate, np.ones(30), "same")[:n]
    base = max(float(np.median(win[win > 0])) if (win > 0).any() else 1.0, 1.0)

    strong = [e for e in eps if e["peak"] >= cfg["strong_laugh"]]
    lines = [
        f"Детектор смеха: AST (AudioSet), окна 2 с. Порог заметного смеха p99={p99:.3f}, сильного p99.9={p999:.3f}, "
        f"strong_laugh={cfg['strong_laugh']}. Максимум стрима {lau.max():.3f}.",
        "ВНИМАНИЕ: дорожка общая (микрофон + видео + игра). Каждый пик проверь по вебке: python sheets.py faces <время>...",
        "",
        "ТОП-20 ПИКОВ СМЕХА:",
        "  # время     длит  пик    громк   смех в чате",
    ]
    for k, e in enumerate(top, 1):
        lines.append(f"{k:>3} {fmt(e['t']):>8}  {e['dur']:>3}с  {e['peak']:.3f}{'*' if e['strong'] else ' '} +{e['loud']:>3.0f}dB  {' | '.join(e['chat_laugh'])[:70]}")
    if not strong:
        lines += ["", f"ВЕРДИКТ: сильных пиков смеха нет (ни один не выше {cfg['strong_laugh']}). Стрим скучный по смеху: "
                      "предупреди пользователя и не выдумывай моменты. Можно предложить шутки по транскрипту, явно пометив, что смеха нет."]
    else:
        lines += ["", f"ВЕРДИКТ: сильных пиков {len(strong)} (помечены *). Проверь по вебке, чей это смех."]
    if not chat:
        lines += ["", "ЧАТ: нет (видео дано файлом или чат пустой) - сигнал чата не используется."]
    else:
        lines += ["", f"ЧАТ: {len(chat)} сообщений, медиана окна 30 с = {base:.0f}. Всплески (x к медиане):"]
        peaks = []
        for i in np.argsort(-win):
            if win[i] <= base:
                break
            if all(abs(i - p) > 45 for p in peaks):
                peaks.append(int(i))
            if len(peaks) == 15:
                break
        for i in sorted(peaks):
            lines.append(f"  {fmt(i)}  x{win[i] / base:.1f}  смех: {' | '.join(chat_laughs(chat, i - 15, i + 15, 0))[:80]}")
    lines += ["", "КАНДИДАТЫ ПО СУММЕ СИГНАЛОВ (смех + громкость + смех в чате + реплики), читать транскрипт вокруг:"]
    lines.append("  " + " ".join(f"{fmt(c)}({sm[c]:.1f})" for c in sorted(cands)))
    (WORK / "signals.txt").write_text("\n".join(lines), encoding="utf-8")
    save({"p99": p99, "p999": p999, "top20": top, "candidates": sorted(cands)}, WORK / "signals.json")
    print("\n".join(lines))


def per_moment(lau, loud, chat, W, top, p99, p999, cfg):
    moments = load(MOMENTS)
    base_rate = len(chat) / max(len(lau), 1) * 30
    rows = []
    for m in moments:
        segs = [(sec(a), sec(b)) for a, b in m["segments"]]
        idx = [i for a, b in segs for i in range(max(0, int(a) - 1), min(len(lau), int(b) + 1))]
        msgs = [x for x in chat if any(a <= x["time_in_seconds"] <= b + cfg["chat_lag_sec"] + 8 for a, b in segs)]
        dur = sum(b - a for a, b in segs)
        cl = [x["message"] for x in msgs if LAUGH_CHAT.search(x["message"] or "")]
        cues = [w["word"].strip() for w in W if any(a <= w["start"] <= b for a, b in segs) and LAUGH_TEXT.search(w["word"])]
        pk = float(lau[idx].max()) if idx else 0.0
        sig = []
        if pk >= cfg["strong_laugh"]:
            sig.append("смех")
        elif pk >= p99:
            sig.append("слабый смех")
        if cl or (msgs and len(msgs) / (dur + 20) * 30 >= 2 * base_rate):
            sig.append("чат")
        if cues:
            sig.append("реплики")
        sig.append("транскрипт")
        rows.append({"id": m["id"], "title": m["title"], "laugh_peak": round(pk, 3),
                     "laugh_sec_p99": int((lau[idx] > p99).sum()) if idx else 0,
                     "loud_db": round(float(max(loud[idx].max(), 0)), 1) if idx else 0.0,
                     "chat_rate_x": round(len(msgs) / (dur + 20) * 30 / max(base_rate, 1e-6), 1),
                     "chat_laughs": cl[:3], "signal": " + ".join(sig)})
    hits = []
    for e in top:
        inside = [m["id"] for m in moments if any(sec(a) - 1 <= e["t"] <= sec(b) for a, b in m["segments"])]
        hits.append({"t": fmt(e["t"]), "peak": round(e["peak"], 3), "in_moment": inside})
    save({"moments": rows, "top20_hits": hits}, WORK / "moment_signals.json")
    print("| # | Момент | Пик смеха | Сек > p99 | Громкость | Чат | Сигнал выбора |\n|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['id']} | {r['title']} | {r['laugh_peak']:.3f} | {r['laugh_sec_p99']} | +{r['loud_db']:.0f} dB | "
              f"x{r['chat_rate_x']} {' '.join(r['chat_laughs'])[:30]} | {r['signal']} |")
    print("\nТоп-20 пиков смеха -> моменты: " + ", ".join(f"{h['t']}({h['peak']}): {h['in_moment'] or '-'}" for h in hits))


if __name__ == "__main__":
    main()
