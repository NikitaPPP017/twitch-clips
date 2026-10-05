"""Шаги 1-3: VOD, чат, аудио, транскрипт, детектор смеха. Пропускает уже готовое.

Usage: python prepare.py <ссылка на VOD Twitch | путь к видеофайлу>
"""
import os
import re
import shutil
import subprocess
import sys

from common import AUDIO, CHAT, INPUT, LAUGH, OUTPUT, TRANSCRIPT, VOD, WORK

PY = sys.executable
HERE = __file__.rsplit("/", 1)[0]


def run(*cmd):
    subprocess.run(cmd, check=True)


def main(source):
    for d in (INPUT, WORK, OUTPUT):
        d.mkdir(exist_ok=True)
    m = re.search(r"twitch\.tv/videos/(\d+)", source)

    # 1. видео
    if VOD.exists():
        print("vod: уже есть, пропускаю")
    elif m:
        run("yt-dlp", "-f", "best[height<=1080]", "-N", "8", "--no-part",
            "--write-info-json", "-o", str(INPUT / "vod.%(ext)s"), source)
    else:
        src = os.path.expanduser(source)
        print(f"vod: копирую файл {src}")
        shutil.copy(src, VOD)

    # 2. чат (только для ссылки Twitch)
    if CHAT.exists():
        print("chat: уже есть, пропускаю")
    elif m:
        if subprocess.run([PY, f"{HERE}/download_chat.py", m.group(1), str(CHAT)]).returncode != 0:
            print("chat: ВНИМАНИЕ - чат не скачан (нет ключа или Twitch не отдал), сигнал чата будет пустым")
    else:
        print("chat: ВНИМАНИЕ - дан файл, а не ссылка Twitch, чат не скачан, сигнал чата будет пустым")

    # 3. аудио 16 кГц моно, транскрипт, смех
    if not AUDIO.exists():
        run("ffmpeg", "-loglevel", "error", "-y", "-i", str(VOD), "-vn", "-ac", "1", "-ar", "16000", str(AUDIO))
    if not TRANSCRIPT.with_suffix(".json").exists():
        run(PY, f"{HERE}/transcribe.py")
    else:
        print("transcript: уже есть, пропускаю")
    if not LAUGH.exists():
        run(PY, f"{HERE}/laugh_detect.py")
    else:
        print("laugh: уже есть, пропускаю")
    run(PY, f"{HERE}/signals.py")


if __name__ == "__main__":
    main(sys.argv[1])
