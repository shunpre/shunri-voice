#!/usr/bin/env bash
set -euo pipefail
LABEL="com.shunlp.shunri-reel-worker"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
rm -f "$PLIST"
echo "瞬理 Reel worker を削除しました。"
