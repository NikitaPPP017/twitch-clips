1. Нужен Mac на M1–M4 с [Homebrew](https://brew.sh) и Claude Code; ffmpeg, Python, Node.js, Whisper и Remotion навык установит сам при первом запуске.
2. Создай пустую папку (например `~/Desktop/clips`) и положи в неё папку `.claude` из этого архива.
3. Открой эту папку в Claude Code: в терминале `cd ~/Desktop/clips && claude` или «Open folder» в приложении.
4. Напиши: «сделай нарезки https://www.twitch.tv/videos/…» (или положи видео в папку и напиши «сделай нарезки из vod.mp4»).
5. Подтверди список моментов, когда Claude его покажет; готовые клипы 9:16 появятся в папке `output`, настройки (ник, язык, длина, субтитры) — в `.claude/skills/twitch-clips/config.json`.
