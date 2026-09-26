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

Docker が必要です。

macOS 13以降なら Homebrew で導入できます。

    brew install --cask docker

macOS 12 Monterey では Homebrew の最新 Docker Desktop は入らないため、Docker公式リリースノートから **Docker Desktop 4.41.2 / Mac with Intel chip** を手動インストールしてください。

https://desktop.docker.com/mac/main/amd64/191736/Docker.dmg

Docker Desktop を起動してから:

    make setup

セットアップはCPU用 Docker イメージを構築し、Irodori-TTS API を localhost:8088 で起動します。Intel MacではCPU負荷を抑えるため、4ステップの MeanFlow 版 `Irodori-TTS-v4.1-Small-MF` を使用します。

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


## MP4 / MP3 から瞬理の固定声を登録

気に入っている声サンプルがある場合は、Voice Design でゼロから声を作るより、参照音声として登録する方が有効です。

MP4 / MP3 / WAV などをそのまま指定できます。

    make reference FILE="/path/to/voice-sample.mp4"

内部で音声だけを抽出し、Irodori-TTS向けの 48kHz / mono / PCM WAV に変換して、

    references/shunri.wav

へ保存します。

その後、固定声でテスト生成します。

    make shunri

生成先:

    outputs/clone.wav

Intel Mac では、ホストに ffmpeg がなくてもセットアップ済みの Docker イメージ内の ffmpeg を使って変換します。

参照音声はGit管理外なので、公開GitHubへアップロードされません。


## いつでも使える `shunri` コマンド

一度だけインストールします。

    cd ~/shunri-voice
    git pull origin main
    make install-cli
    source ~/.zshrc

以後は、どのフォルダにいても瞬理の固定声を呼び出せます。

文章を直接指定:

    shunri "こんにちは。瞬理です。今日はLPについて話します。"

生成後そのまま再生:

    shunri --play "こんにちは。瞬理です。"

台本ファイルから生成:

    shunri --file ~/Desktop/script.txt

保存先を指定:

    shunri --output ~/Desktop/shunri-reel.wav "読み上げたい文章"

標準の出力先:

    ~/shunri-voice/outputs/shunri.wav

Intel Mac では Irodori-TTS API が停止していれば `shunri` コマンドが Docker Compose サービスを自動起動します。

固定声の正本は `references/shunri.wav` です。このファイルを明示的に差し替えない限り、同じ瞬理の声を使い続けます。


## 瞬理 Reel 自動キュー

最終目標は、ChatGPT側から `@瞬理` 相当の1回の依頼で台本→瞬理音声→動画まで流すことです。

現段階では、private repository `shunpre/shun-x-scheduler` の

    runtime/shunri-reel-jobs.json

をローカルMacが監視し、`action=narrate` の確定台本を瞬理の固定声で自動ナレーション化できます。

1回だけ処理:

    make worker-once

60秒ごとの自動処理をインストール:

    make install-reel-worker

停止・削除:

    make uninstall-reel-worker

生成物:
- WAV master: `~/shunri-voice/outputs/jobs/<job-id>/narration.wav`
- downstream用MP3: private scheduler repo の `runtime/shunri-reel-assets/<job-id>/narration.mp3`

参照声 `references/shunri.wav` はローカルだけに残し、GitHubには保存しません。


## Phase 1 — Reel PoC

瞬理の確定台本から、以下を1コマンドで生成する最初の実働パイプラインです。

    確定台本
    → 瞬理の正式声
    → シーン分割
    → 日本語字幕
    → 1080x1920 MP4

最初のPoCでは人物は正準の瞬理静止画を使います。次工程でMotion Bankを接続して、参考動画のようなジェスチャー / リップシンクへ進めます。

前提:

    ~/shun-x-scheduler/assets/instagram/character/reference/canonical_front.jpeg

が存在すること。

実行:

    cd ~/shunri-voice
    git pull origin main
    make reel-poc FILE="$HOME/Desktop/script.txt"

初回のみReel renderer用Dockerイメージを自動構築します。

標準出力:

    ~/shunri-voice/outputs/reel-poc/shunri-reel-poc.mp4

途中生成物:

    ~/shunri-voice/outputs/reel-poc/.poc-work/narration.wav
    ~/shunri-voice/outputs/reel-poc/.poc-work/scene-plan.json
    ~/shunri-voice/outputs/reel-poc/.poc-work/captions.ass

設計上の重要点:
- approved scriptは書き換えない
- 音声は必ず `references/shunri.wav`
- 字幕文字はAI画像へ焼き込まずrendererが描画
- 日本語フォントはrenderer DockerにNoto CJKを入れて固定
- 1080x1920 / 30fps / H.264 + AAC


## Phase 2 — Motion Bank

Phase 1 の静止画Presenterを、瞬理専用のMotion Bankへ置き換えます。

初回:

    cd ~/shunri-voice
    git pull origin main
    make motion-bank

生成先:

    ~/shunri-voice/assets/motion-bank/

固定variant:

    neutral-talk
    open-hand
    point-up
    point-side
    think
    small-nod
    explain-both-hands
    cta-forward

現在のv1 bankは正準キャラクター画像から作る軽量モーションです。
目的はMotion Bankの選択・カット・レンダリング配線を先に完成させることです。

その後:

    make reel-poc FILE="$HOME/shunri-voice/samples/reel_script.txt"

を実行すると、scene-planごとにMotion Bank variantを自動選択し、
1枚固定ではなくPresenterカットが切り替わる縦動画を生成します。

重要:
- Motion Bankのファイル名/variant契約は今後も固定
- 後工程で同名mp4を「本物のジェスチャー動画＋lip-sync動画」に差し替える
- rendererやscene planner側は変更しない
- 旧静止画モードは --static-presenter で残す

つまり、Motion Bankの品質だけを上げればReel全体のPresenter品質も上がる構造です。
