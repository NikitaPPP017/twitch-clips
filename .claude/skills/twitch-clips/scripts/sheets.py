"""Листы кадров для проверки глазами (их читает Claude через Read).

Usage: python sheets.py faces 1:50:20 0:53:14 ...  -> work/sheets/faces_N.jpg
         верхняя часть кадра (там вебка во всех раскладках), 5 кадров -6..+6 с вокруг каждого времени:
         смеётся ли сам стример или смех из видео/игры
       python sheets.py layout                    -> work/sheets/layout_<id>.png
         для каждого момента из work/moments.json: кадры начала/середины/конца каждого куска
         в полном размере 960x540 с сеткой каждые 100 px исходника - чтобы задать
         прямоугольники cam/content в work/layouts.json
       python sheets.py check output/<клип>.mp4 ... -> work/sheets/check.jpg  (кадры готовых клипов)
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from common import MOMENTS, VOD, WORK, fmt, load, sec

OUT = WORK / "sheets"


def grab(src, t, vf):
    tmp = OUT / "_tmp.png"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{max(t, 0):.2f}", "-i", str(src),
                    "-frames:v", "1", "-vf", vf, str(tmp)], check=True)
    return Image.open(tmp).copy()


def faces(times):
    rows = []
    for t in times:
        row = Image.new("RGB", (70 + 5 * 240, 135), "white")
        ImageDraw.Draw(row).text((3, 60), fmt(t), fill="black")
        for i, d in enumerate((-6, -3, 0, 3, 6)):
            row.paste(grab(VOD, t + d, "crop=1080:608:0:0,scale=240:135"), (70 + i * 240, 0))
        rows.append(row)
    for k in range(0, len(rows), 10):
        part = rows[k : k + 10]
        sheet = Image.new("RGB", (part[0].width, 135 * len(part)), "white")
        for i, r in enumerate(part):
            sheet.paste(r, (0, 135 * i))
        sheet.save(OUT / f"faces_{k // 10}.jpg")
        print(OUT / f"faces_{k // 10}.jpg")


def layout():
    for m in load(MOMENTS):
        frames = []
        for a, b in m["segments"]:
            a, b = sec(a), sec(b)
            for t in (a + 0.5, (a + b) / 2, b - 0.5):
                im = grab(VOD, t, "scale=960:540")
                d = ImageDraw.Draw(im)
                for x in range(0, 960, 50):
                    d.line([(x, 0), (x, 540)], fill="red" if x % 100 == 0 else "#ff000055")
                for y in range(0, 540, 50):
                    d.line([(0, y), (960, y)], fill="red" if y % 100 == 0 else "#ff000055")
                d.text((4, 524), f"{fmt(t)}  (grid of 1920x1080 source: thin line = 100 px, bold = 200 px)", fill="yellow")
                frames.append(im)
        cols = 3
        sheet = Image.new("RGB", (cols * 960, 540 * ((len(frames) + cols - 1) // cols)), "white")
        for i, im in enumerate(frames):
            sheet.paste(im, ((i % cols) * 960, (i // cols) * 540))
        sheet.save(OUT / f"layout_{m['id']:02}.png")
        print(OUT / f"layout_{m['id']:02}.png")


def check(files):
    tiles = []
    for f in files:
        dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]))
        for p in (0.15, 0.5, 0.85):
            im = grab(f, dur * p, "scale=225:400")
            ImageDraw.Draw(im).text((3, 3), f"{Path(f).name[:20]} {dur * p:.0f}s", fill="yellow")
            tiles.append(im)
    cols = 9
    sheet = Image.new("RGB", (cols * 228, 403 * ((len(tiles) + cols - 1) // cols)), "white")
    for i, im in enumerate(tiles):
        sheet.paste(im, ((i % cols) * 228, (i // cols) * 403))
    sheet.save(OUT / "check.jpg")
    print(OUT / "check.jpg")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    mode, args = sys.argv[1], sys.argv[2:]
    if mode == "faces":
        faces([sec(a) for a in args])
    elif mode == "layout":
        layout()
    else:
        check(args)
