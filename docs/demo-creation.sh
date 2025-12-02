#!/usr/bin/env bash
SRC=${1:?source.mp4}
ffmpeg -ss 00:00:08 -i "$SRC" -vframes 1 -q:v 2 docs/demo-thumbnail.png
ffmpeg -ss 00:00:05 -t 4 -i "$SRC" -vf "fps=15,scale=640:-1:flags=lanczos" -y docs/demo.gif
if command -v gifsicle >/dev/null 2>&1; then
  gifsicle -O3 docs/demo.gif -o docs/demo.gif
fi
echo "Created docs/demo-thumbnail.png and docs/demo.gif"
