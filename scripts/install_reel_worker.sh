#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.shunlp.shunri-reel-worker"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs"
RUNNER="$ROOT_DIR/scripts/run_reel_worker.sh"
UID_NOW="$(id -u)"

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"
chmod +x "$RUNNER"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$RUNNER</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>StartInterval</key>
  <integer>60</integer>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/shunri-reel-worker.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/shunri-reel-worker-error.log</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$UID_NOW" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$UID_NOW" "$PLIST"
launchctl kickstart -k "gui/$UID_NOW/$LABEL"

echo "瞬理 Reel worker をインストールしました。"
echo "60秒ごとに private GitHub queue を確認します。"
echo "log: $LOG_DIR/shunri-reel-worker.log"
