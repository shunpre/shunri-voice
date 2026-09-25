# shunri-voice

瞬LP AI広報「瞬理（しゅり）」の固定ナレーション音声を作るための Irodori-TTS 検証リポジトリです。

## 目的

最初から1つの声に固定せず、同じReel台本を5種類の声で生成して比較します。採用した声は、そのWAVを参照音声として以後の生成に使い、瞬理の声を固定していきます。

## 1. セットアップ

    cd ~/shunri-voice
    git pull origin main
    make setup

uv がない場合:

    brew install uv
    make setup

setup は .vendor/Irodori-TTS に公式 Irodori-TTS を取得し、macOS向け依存関係をセットアップします。

## 2. 5種類の瞬理候補を一括生成

    make voices

生成先は outputs/voice-a.wav 〜 outputs/voice-e.wav です。

台本は samples/reel_script.txt を編集すれば差し替えられます。

## 3. 採用した声を固定する

例: voice-b を採用した場合

    mkdir -p references
    cp outputs/voice-b.wav references/shunri.wav
    python3 scripts/generate.py --text-file samples/reel_script.txt --preset default --reference references/shunri.wav

参照音声を使うことで、話者IDを保ちながら台本ごとに話し方を調整できます。

## 4. MPS / CPU

通常は自動判定します。

    python3 scripts/generate.py --preset all --device mps

MPSで失敗した場合:

    python3 scripts/generate.py --preset all --device cpu

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
- scripts/bootstrap.sh: Irodori-TTSセットアップ
- scripts/generate.py: 一括 / 単体音声生成
- outputs/: 生成音声（Git管理外）
- references/: 採用した参照音声（Git管理外）
- .vendor/: Irodori-TTS本体（Git管理外）
