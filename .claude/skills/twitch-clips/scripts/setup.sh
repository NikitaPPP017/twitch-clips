#!/bin/zsh
# Установка всего нужного для нарезок (macOS на Apple Silicon). Запуск из корня проекта.
# Повторный запуск безопасен: уже установленное пропускается.
set -e
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "ОШИБКА: нужен Mac на Apple Silicon (M1-M4): Whisper работает через MLX." >&2
  exit 1
fi
command -v brew >/dev/null || { echo "ОШИБКА: нужен Homebrew: https://brew.sh" >&2; exit 1; }

# ставим только то, чего нет в системе (уже установленный node из nvm и т.п. не дублируем)
command -v ffmpeg >/dev/null || brew install ffmpeg
command -v yt-dlp >/dev/null || brew install yt-dlp
command -v node >/dev/null || brew install node
command -v python3.12 >/dev/null || brew install python@3.12
PY=$(command -v python3.12)

mkdir -p input work output
[[ -x .venv/bin/python ]] || "$PY" -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q \
  mlx-whisper==0.4.3 transformers==5.18.0 torch==2.14.1 \
  soundfile==0.14.0 pillow==12.3.0 numpy==2.5.3

# шаблон Remotion копируется в work/remotion, туда же ставятся node_modules
mkdir -p work/remotion
cp -R "$SKILL_DIR/remotion/." work/remotion/
(cd work/remotion && npm install --silent --no-audit --no-fund)

echo "--- проверка"
ffmpeg -version | head -1
yt-dlp --version
.venv/bin/python -c "import mlx_whisper, transformers, torch, soundfile, PIL; print('python ok')"
(cd work/remotion && npx remotion versions >/dev/null && echo "remotion ok")
