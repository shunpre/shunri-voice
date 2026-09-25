#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
UPSTREAM_DIR="$ROOT_DIR/.vendor/Irodori-TTS"
IRODORI_REPO="https://github.com/Aratako/Irodori-TTS.git"
IRODORI_COMMIT="89f9d8fbd4d51ea019867ee1197725ede1df13c5"

if ! command -v git >/dev/null 2>&1; then
  echo "git が見つかりません。Xcode Command Line Tools などで git を導入してください。" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv が見つかりません。" >&2
  echo "Homebrew がある場合: brew install uv" >&2
  exit 1
fi

mkdir -p "$ROOT_DIR/.vendor" "$ROOT_DIR/outputs" "$ROOT_DIR/references"

if [ ! -d "$UPSTREAM_DIR/.git" ]; then
  echo "[1/3] Irodori-TTS を取得します..."
  git clone "$IRODORI_REPO" "$UPSTREAM_DIR"
fi

echo "[2/3] 検証済みコミットへ合わせます..."
git -C "$UPSTREAM_DIR" fetch --all --tags
git -C "$UPSTREAM_DIR" checkout "$IRODORI_COMMIT"

echo "[3/3] macOS向け依存関係をセットアップします..."
cd "$UPSTREAM_DIR"
uv sync --extra cpu

echo
echo "セットアップ完了。"
echo "次: cd \"$ROOT_DIR\" && make voices"
