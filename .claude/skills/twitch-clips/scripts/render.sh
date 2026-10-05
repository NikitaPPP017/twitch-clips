#!/bin/zsh
# Рендер клипов из work/remotion/public/edits в output/. Запуск из корня проекта.
# Usage: render.sh [имя_клипа ...]   (без аргументов - все)
# Упавший рендер повторяется до 3 раз (бывает ERR_NETWORK_CHANGED при смене сети на Mac).
ROOT="$PWD"
cd work/remotion || { echo "нет work/remotion - запусти setup.sh" >&2; exit 1; }
mkdir -p "$ROOT/output"
names=("$@")
[[ ${#names} -eq 0 ]] && names=(${(f)"$(ls public/edits | sed 's/\.json$//')"})
failed=()
for name in $names; do
  ok=0
  for attempt in 1 2 3; do
    if npx remotion render src/index.ts Clip "$ROOT/output/$name.mp4" --props="{\"name\":\"$name\"}" --log=error >/dev/null 2>"$ROOT/work/render_$name.err"; then
      ok=1; break
    fi
    echo "  повтор $name ($attempt)"
  done
  if [[ $ok -eq 1 ]]; then echo "OK $name"; else echo "FAILED $name (см. work/render_$name.err)"; failed+=$name; fi
done
[[ ${#failed} -eq 0 ]]
