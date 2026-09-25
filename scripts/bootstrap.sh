#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OS="$(uname -s)"
ARCH="$(uname -m)"

IRODORI_REPO="https://github.com/Aratako/Irodori-TTS.git"
IRODORI_COMMIT="89f9d8fbd4d51ea019867ee1197725ede1df13c5"
IRODORI_DIR="$ROOT_DIR/.vendor/Irodori-TTS"

SERVER_REPO="https://github.com/Aratako/Irodori-TTS-Server.git"
SERVER_COMMIT="61012c760f22f7b4a6c21c5c5f8f9e148120b6f9"
SERVER_DIR="$ROOT_DIR/.vendor/Irodori-TTS-Server"

mkdir -p "$ROOT_DIR/.vendor" "$ROOT_DIR/outputs" "$ROOT_DIR/references"

if [ "$OS" = "Darwin" ] && [ "$ARCH" = "x86_64" ]; then
  echo "Intel Mac を検出しました。Docker CPU ランタイムでセットアップします。"

  if ! command -v docker >/dev/null 2>&1; then
    echo
    echo "Docker が見つかりません。"
    echo "Homebrew を使う場合:"
    echo "  brew install --cask docker"
    echo
    echo "インストール後に Docker Desktop を起動してから、もう一度 make setup を実行してください。"
    exit 1
  fi

  if ! docker info >/dev/null 2>&1; then
    echo
    echo "Docker はありますが、Docker Engine が起動していません。"
    echo "Docker Desktop を起動してから、もう一度 make setup を実行してください。"
    exit 1
  fi

  if [ ! -d "$SERVER_DIR/.git" ]; then
    echo "[1/4] Irodori-TTS-Server を取得します..."
    git clone "$SERVER_REPO" "$SERVER_DIR"
  fi

  echo "[2/4] 検証済みサーバーコミットへ合わせます..."
  git -C "$SERVER_DIR" fetch --all --tags
  git -C "$SERVER_DIR" checkout "$SERVER_COMMIT"

  cat > "$SERVER_DIR/.env" <<'EOF'
IRODORI_HOST=0.0.0.0
IRODORI_PORT=8088
IRODORI_TTS_BACKEND=cpu
IRODORI_HF_CHECKPOINT=Aratako/Irodori-TTS-v4.1-Small-MF
IRODORI_CODEC_REPO=Aratako/Semantic-DACVAE-Japanese-32dim
IRODORI_MODEL_NAME=irodori-tts
IRODORI_MODEL_DEVICE=cpu
IRODORI_CODEC_DEVICE=cpu
IRODORI_MODEL_PRECISION=fp32
IRODORI_CODEC_PRECISION=fp32
IRODORI_COMPILE_MODEL=false
IRODORI_COMPILE_DYNAMIC=false
IRODORI_PRELOAD=false
IRODORI_MODEL_LOAD_TIMEOUT=3600
IRODORI_MAX_CONCURRENT_SYNTHESIS=1
IRODORI_SYNTHESIS_WAIT_TIMEOUT=3600
IRODORI_EMPTY_CACHE_INTERVAL=10
IRODORI_VOICES_DIR=voices
IRODORI_ALLOW_NO_REF_VOICE=true
IRODORI_DEFAULT_RESPONSE_FORMAT=wav
IRODORI_DEFAULT_T_SCHEDULE_MODE=linear
IRODORI_DEFAULT_SWAY_COEFF=-1.0
IRODORI_DEFAULT_DURATION_SCALE=1.0
IRODORI_DEFAULT_CFG_SCALE_TEXT=3.0
IRODORI_DEFAULT_CFG_SCALE_SPEAKER=5.0
IRODORI_DEFAULT_CFG_GUIDANCE_MODE=independent
IRODORI_DEFAULT_CHUNKING_ENABLED=true
IRODORI_DEFAULT_CHUNK_MIN_CHARS=80
EOF

  mkdir -p "$SERVER_DIR/voices"

  echo "[3/4] CPU Docker イメージを構築します..."
  (
    cd "$SERVER_DIR"
    docker compose build
  )

  echo "[4/4] Irodori-TTS API を起動します..."
  (
    cd "$SERVER_DIR"
    docker compose up -d
  )

  echo
  echo "Intel Mac 用セットアップ完了。"
  echo "次: cd "$ROOT_DIR" && make voices"
  echo "※ 初回の音声生成時にモデルがダウンロードされるため時間がかかります。"
  exit 0
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git が見つかりません。Xcode Command Line Tools などで git を導入してください。" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv が見つかりません。" >&2
  echo "Homebrew がある場合: brew install uv" >&2
  exit 1
fi

if [ ! -d "$IRODORI_DIR/.git" ]; then
  echo "[1/3] Irodori-TTS を取得します..."
  git clone "$IRODORI_REPO" "$IRODORI_DIR"
fi

echo "[2/3] 検証済みコミットへ合わせます..."
git -C "$IRODORI_DIR" fetch --all --tags
git -C "$IRODORI_DIR" checkout "$IRODORI_COMMIT"

echo "[3/3] 依存関係をセットアップします..."
cd "$IRODORI_DIR"
uv sync --extra cpu

echo
echo "セットアップ完了。"
echo "次: cd "$ROOT_DIR" && make voices"
