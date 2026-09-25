#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="$HOME/.local/bin"
TARGET="$BIN_DIR/shunri"
ZSHRC="$HOME/.zshrc"
PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'

mkdir -p "$BIN_DIR"

cat > "$TARGET" <<EOF
#!/usr/bin/env bash
exec python3 "$ROOT_DIR/scripts/shunri_cli.py" "\$@"
EOF

chmod +x "$TARGET"

touch "$ZSHRC"
if ! grep -Fq "$PATH_LINE" "$ZSHRC"; then
  printf '\n%s\n' "$PATH_LINE" >> "$ZSHRC"
fi

echo "インストールしました: $TARGET"
echo
echo "このターミナルで今すぐ使うには:"
echo "  export PATH=\"$HOME/.local/bin:\$PATH\""
echo
echo "次回以降のターミナルでは自動的に使えます。"
echo
echo '例: shunri --play "こんにちは。瞬理です。"'
