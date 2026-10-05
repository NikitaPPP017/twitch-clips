"""Таблицы для остановок.

Usage: python table.py moments  -> таблица для подтверждения (файл, начало/конец в VOD, длительность, тип, сигнал, описание)
       python table.py final    -> итог после монтажа (файл, путь, длительность, тип, сигнал) + output/report.md
"""
import subprocess
import sys

from common import CLIPS, MOMENTS, OUTPUT, WORK, fmt, load, sec
from cut_clips import clip_name


def moments_table():
    sig = {r["id"]: r["signal"] for r in load(WORK / "moment_signals.json", {}).get("moments", [])}
    print("| # | Файл | Начало | Конец | Длительность | Тип | Сигнал выбора | Описание |\n|---|---|---|---|---|---|---|---|")
    for m in load(MOMENTS):
        segs = [(sec(a), sec(b)) for a, b in m["segments"]]
        dur = sum(b - a for a, b in segs)
        start = " / ".join(fmt(a) for a, _ in segs)
        end = " / ".join(fmt(b) for _, b in segs)
        print(f"| {m['id']} | {clip_name(m)}.mp4 | {start} | {end} | {dur:.0f} с | {m['type']} | "
              f"{sig.get(m['id'], m.get('signal', '?'))} | {m['why']} |")


def final_table():
    sig = {r["id"]: r for r in load(WORK / "moment_signals.json", {}).get("moments", [])}
    lines = ["| # | Файл | Длительность | Тип | Сигнал выбора | Пик смеха |", "|---|---|---|---|---|---|"]
    for m in load(MOMENTS):
        f = OUTPUT / f"{clip_name(m)}.mp4"
        if not f.exists():
            lines.append(f"| {m['id']} | {f.name} | НЕТ ФАЙЛА | {m['type']} | | |")
            continue
        dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)]))
        r = sig.get(m["id"], {})
        lines.append(f"| {m['id']} | {f} | {int(dur) // 60}:{int(dur) % 60:02} | {m['type']} | {r.get('signal', '?')} | {r.get('laugh_peak', '?')} |")
    text = "\n".join(lines)
    (OUTPUT / "report.md").write_text("# Готовые клипы\n\n" + text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    moments_table() if sys.argv[1] == "moments" else final_table()
