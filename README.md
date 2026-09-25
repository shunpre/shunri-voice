# shunri-voice

瞬LP AI広報「瞬理（しゅり）」の固定ナレーション音声を作るための Irodori-TTS 検証リポジトリです。

## 目的

最初から1つの声に固定せず、同じReel台本を5種類の声で生成して比較します。採用した声は、そのWAVを参照音声として以後の生成に使い、瞬理の声を固定していきます。

## 対応環境

- Apple Silicon Mac: Irodori-TTS をローカル実行（MPS / CPU）
- Intel Mac: 公式 Irodori-TTS-Server を Docker CPU で実行

Intel Mac では PyTorch 2.10 の macOS x86_64 wheel がないため、Mac本体には入れず Linux Docker 内で実行します。

## 1. セットアップ

    cd ~/shunri-voice
    git pull origin main
    make setup

### Apple Silicon Mac

uv がない場合:

    brew install uv
    make setup

### Intel Mac

Docker が必要です。未導入なら:

    brew install --cask docker

Docker Desktop を起動してから:

    make setup

セットアップはCPU用 Docker イメージを構築し、Irodori-TTS API を localhost:8088 で起動します。

## 2. 5種類の瞬理候補を一括生成

    make voices

生成先:

    outputs/voice-a.wav
    outputs/voice-b.wav
    outputs/voice-c.wav
    outputs/voice-d.wav
    outputs/voice-e.wav

初回生成時は Irodori-TTS モデルをダウンロードします。

台本は samples/reel_script.txt を編集すれば差し替えられます。

## 3. 採用した声を固定する

例: voice-b を採用した場合

    mkdir -p references
    cp outputs/voice-b.wav references/shunri.wav
    python3 scripts/generate.py --text-file samples/reel_script.txt --preset default --reference references/shunri.wav

参照音声を使うことで、話者IDを保ちながら台本ごとに話し方を調整できます。

Intel Mac では参照音声を Docker 側の voices/ に自動コピーして使用します。

## 4. Apple Silicon の MPS / CPU

通常は自動判定します。

    python3 scripts/generate.py --preset all --device mps

MPSで失敗した場合:

    python3 scripts/generate.py --preset all --device cpu

Intel Mac では --device 指定に関係なく Docker CPU API を利用します。

## 声候補

- A: 知的・落ち着き
- B: 軽いウィスパー
- C: 明るく親しみやすい
- D: クールなAI広報
- E: 自然なSNSクリエイター

## ライセンス / 注意

Irodori-TTS のコード・モデルの利用条件と Ethical Restrictions に従ってください。実在人物・声優・著名人などの声を本人の明示的同意なくクローンしないでください。本リポジトリはオリジナルAIキャラクター「瞬理」用の新規音声設計を前提にしています。

生成時の SilentCipher 電子透かしは Irodori-TTS 側の標準挙動をそのまま利用します。

## 構成

- config/voices.json: 声候補と固定後のデフォルト設定
- samples/reel_script.txt: 比較用Reel台本
- scripts/bootstrap.sh: 環境判定とセットアップ
- scripts/generate.py: 一括 / 単体音声生成
- outputs/: 生成音声（Git管理外）
- references/: 採用した参照音声（Git管理外）
- .vendor/Irodori-TTS/: Apple Silicon用本体（Git管理外）
- .vendor/Irodori-TTS-Server/: Intel Mac用公式APIサーバー（Git管理外）
