#!/bin/zsh


Resources=$(dirname "$0")

SUPPORT="$HOME/Library/Application Support/ScreenSaver"
VENV="$SUPPORT/.venv"

cd "$Resources" || exit 1

exec "$VENV/bin/python3" gui.py update
