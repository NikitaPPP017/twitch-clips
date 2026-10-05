"""Общие пути и настройки навыка twitch-clips.

Все скрипты запускаются из корня проекта (папки стримера):
  input/   - vod.mp4, chat.json, vod.info.json
  work/    - транскрипт, детекторы, моменты, куски, раскладки
  output/  - готовые клипы 9:16 и отчёт
Настройки читаются из config.json рядом с SKILL.md.
"""
import json
import os
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ROOT = Path.cwd()
INPUT, WORK, OUTPUT = ROOT / "input", ROOT / "work", ROOT / "output"
VOD = INPUT / "vod.mp4"
CHAT = INPUT / "chat.json"
AUDIO = WORK / "audio.wav"
TRANSCRIPT = WORK / "transcript"  # .json / .srt / .txt
LAUGH = WORK / "laugh.json"
MOMENTS = WORK / "moments.json"
LAYOUTS = WORK / "layouts.json"
CLIPS = WORK / "clips"
REMOTION = WORK / "remotion"


def load_env(path=ROOT / ".env"):
    """Ключи из .env в корне проекта (KEY=value), без перезаписи уже заданных переменных."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()


def config():
    return json.load(open(SKILL_DIR / "config.json", encoding="utf-8"))


def fmt(t):
    t = int(t)
    return f"{t // 3600}:{t % 3600 // 60:02}:{t % 60:02}"


def sec(t):
    """'1:02:03.5' -> 3723.5"""
    if isinstance(t, (int, float)):
        return float(t)
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def words():
    segs = json.load(open(f"{TRANSCRIPT}.json", encoding="utf-8"))
    return [w for s in segs for w in s.get("words", [])]


def load(path, default=None):
    path = Path(path)
    return json.load(open(path, encoding="utf-8")) if path.exists() else default


def save(obj, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    json.dump(obj, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
