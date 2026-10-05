1. Нужен Mac на M1–M4 с [Homebrew](https://brew.sh) и Claude Code; ffmpeg, Python, Node.js, Whisper и Remotion навык установит сам при первом запуске.
2. Создай пустую папку (например `~/Desktop/clips`) и положи в неё папку `.claude` из этого архива.
3. Открой эту папку в Claude Code (в терминале `cd ~/Desktop/clips && claude` или «Open folder» в приложении) и один раз нажми **Trust**: это включит разрешения навыка.
4. Напиши: «сделай нарезки https://www.twitch.tv/videos/…» (или положи видео в папку и напиши «сделай нарезки из vod.mp4»).
5. Дальше Claude всё сделает сам, без вопросов; готовые клипы 9:16 появятся в папке `output`, и только тогда он спросит, что поправить. Настройки (ник, язык, длина, субтитры) лежат в `.claude/skills/twitch-clips/config.json`.
